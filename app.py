from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QFileSystemWatcher, QUrl, pyqtSlot, QObject
from PyQt5.QtWebChannel import QWebChannel
import sys, re, os


class Bridge(QObject):
    @pyqtSlot(str, result=str)
    def echo(self, message):
        print("Received from JS:", message)
        return message


class MyWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super(MyWebEnginePage, self).__init__(parent)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(message)

    def javaScriptAlert(self, frame, msg):
        alert = QMessageBox()
        alert.setWindowTitle("Alert")
        alert.setText(msg)
        alert.setIcon(QMessageBox.Warning)
        alert.exec_()


class MainWindow(QMainWindow):
    def __init__(self, input_file):
        super().__init__()
        self.input_file = input_file
        self.file_url = QUrl.fromLocalFile(os.path.abspath(self.input_file))
        self._dependencies = set([self.input_file])

        self.setGeometry(100, 100, 1200, 700)
        #self.showFullScreen()

        self.webview = QWebEngineView(self)
        self.setCentralWidget(self.webview)

        # Use the custom page class for logs
        self.webview.setPage(MyWebEnginePage(self))

        # Set up the WebChannel
        self.channel = QWebChannel()
        self.webview.page().setWebChannel(self.channel)

        # Expose the Python object to JavaScript
        self.bridge = Bridge()
        self.channel.registerObject("bridge", self.bridge)

        # Set up file watcher
        self.file_watcher = QFileSystemWatcher(list(self._dependencies))
        self.file_watcher.fileChanged.connect(self.update_html)

        # Initial load of HTML
        self.update_html()
    

    def update_html(self):
        # Load HTML content
        with open(self.input_file, "r") as f:
            html_content = f.read()
        
        # Extract and watch dependencies (CSS & JS files)
        self.extract_dependencies(html_content)
        self.file_watcher.addPaths(list(self._dependencies))
        
        title_match = re.search('<title>(.*?)</title>', html_content, re.IGNORECASE)
        
        if title_match:
            self.setWindowTitle(title_match.group(1))
        else:
            self.setWindowTitle("HTML Renderer")
        
        self.webview.setUrl(self.file_url)
    

    def extract_dependencies(self, html_content):
        # Regex patterns for CSS and JS files
        css_pattern = r'<link.*?href="(.*?\.css)".*?>'
        js_pattern = r'<script.*?src="(.*?\.js)".*?>'
        html_pattern = r'<div.*?data-include="(.*?\.html)".*?>'

        # Find all CSS and JS files
        css_files = re.findall(css_pattern, html_content, re.IGNORECASE)
        js_files = re.findall(js_pattern, html_content, re.IGNORECASE)
        html_files = re.findall(html_pattern, html_content, re.IGNORECASE)
        print(html_files)

        # Convert relative paths to absolute paths
        all_files = css_files + js_files + html_files
        base_dir = os.path.dirname(self.input_file)
        absolute_paths = [os.path.join(base_dir, f) for f in all_files]

        for path in absolute_paths:
            if not path in self._dependencies and os.path.exists(path):
                self._dependencies.add(path)
                with open(path, "r") as f:
                    self.extract_dependencies(f.read())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        input_file = "index.html"
    else:
        input_file = sys.argv[1]
    app = QApplication(sys.argv)
    window = MainWindow(input_file)
    window.show()
    sys.exit(app.exec_())
