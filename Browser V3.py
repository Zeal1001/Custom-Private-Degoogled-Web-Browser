import sys
import os
import json
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QTabWidget,
    QToolBar, QAction, QMessageBox, QInputDialog
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings
)
import traceback
from urllib.parse import quote_plus


os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
    '--enable-gpu-rasterization '
    '--enable-oop-rasterization '
    '--enable-zero-copy '
    '--enable-webgl '
    '--use-gl=desktop '
    '--enable-media-foundation '
    '--enable-widevine-cdm '
    '--disable-software-rasterizer '
    '--ignore-gpu-blacklist '
    '--enable-gpu-accelerated-video-decode '
    '--enable-threaded-compositing '
    '--enable-fast-deps-chrome '
    '--enable-lcd-text '
    '--disable-gl-extensions '
)

def excepthook(exc_type, exc_value, exc_tb):
    err = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    QMessageBox.critical(None, 'Error', err)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

HISTORY_FILE = 'history.json'
BOOKMARKS_FILE = 'bookmarks.json'
SESSION_FILE = 'session.json'

def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except:
        pass

def create_homepage_html():
    return '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Welcome</title>
    <style>
        body { background-color: #1e1e1e; color: #ffffff; font-family: Arial, sans-serif;
               display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        h1 { font-size: 36px; margin-bottom: 10px; }
        p { font-size: 18px; }
    </style>
</head>
<body>
    <h1>Zeal Kimones Light Weight Private Web Browser</h1>
    <p>Your secure, privacy-first browsing experience, I think if I made it right.......</p>
</body>
</html>
'''

class BrowserTab(QWebEngineView):
    def __init__(self, profile, homepage_html, private=False):
        super().__init__()
        self.private = private
        page = QWebEnginePage(profile, self)
        page.setBackgroundColor(QColor(30, 30, 30))
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        page.renderProcessTerminated.connect(self.on_render_crash)
        page.urlChanged.connect(self.on_url_changed)
        self.setPage(page)
        self.is_home = True
        self.setVisible(False)
        self.setHtml(homepage_html)
        self.loadFinished.connect(self.finish_load)
        self.profile = profile

    def finish_load(self):
        self.is_home = True
        self.setVisible(True)

    def load_url(self, url):
        self.is_home = False
        self.load(QUrl(url))

    def on_url_changed(self, qurl):
        if qurl.isEmpty() or self.is_home:
            return
        url = qurl.toString()

    def on_render_crash(self, status, code):
        QMessageBox.critical(
            self, 'Renderer Crashed', f'Status: {status.name}\nCode: {code}'
        )

class SimpleBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Zeal Kimones Light Weight Private Web Browser')
        self.resize(1200, 800)

        self.homepage_html = create_homepage_html()

        
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        for icon, func in [('←', self.go_back), ('→', self.go_forward), ('⟳', self.reload), ('🏠', self.go_home)]:
            act = QAction(icon, self)
            act.triggered.connect(func)
            toolbar.addAction(act)
        toolbar.addSeparator()

        self.url_input = QLineEdit()
        self.url_input.returnPressed.connect(self.navigate)
        self.url_input.setStyleSheet('background: #2b2b2b; color: #fff;')
        self.url_input.setMinimumWidth(400)
        toolbar.addWidget(self.url_input)

        new_tab = QAction('+', self)
        new_tab.triggered.connect(lambda: self.add_tab())
        toolbar.addAction(new_tab)

        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_url)
        self.setCentralWidget(self.tabs)

        self.add_tab()

        self.app = QApplication.instance()
        self.app.aboutToQuit.connect(self.save_session)

    def add_tab(self, url=None, private=False):
        profile = QWebEngineProfile() if private else QWebEngineProfile.defaultProfile()
        browser = BrowserTab(profile, self.homepage_html, private=private)
        idx = self.tabs.addTab(browser, 'Home' + (' 🔒' if private else ''))
        self.tabs.setCurrentIndex(idx)
        if url:
            browser.load_url(url)
            self.tabs.setTabText(idx, 'Loading...')
        browser.titleChanged.connect(lambda t, i=idx: self.tabs.setTabText(i, t or 'New Tab'))
        browser.urlChanged.connect(lambda q, b=browser: self.update_url(q, b))
        self.sync_url(idx)

    def close_tab(self, i):
        if self.tabs.count() > 1:
            self.tabs.removeTab(i)

    def sync_url(self, idx):
        w = self.tabs.widget(idx)
        if isinstance(w, BrowserTab):
            if w.is_home:
                self.url_input.clear()
            else:
                self.url_input.setText(w.url().toString())
        else:
            self.url_input.clear()

    def update_url(self, q, b):
        if b == self.tabs.currentWidget() and not b.is_home:
            self.url_input.setText(q.toString())

    def navigate(self):
        text = self.url_input.text().strip()
        if text.startswith(('http://', 'https://')):
            url = text
        elif '.' in text and ' ' not in text:
            url = 'https://' + text
        else:
            query = quote_plus(text)
            url = f'https://duckduckgo.com/?q={query}'
        w = self.tabs.currentWidget()
        if isinstance(w, BrowserTab):
            w.load_url(url)

    def go_back(self):
        w = self.tabs.currentWidget()
        if isinstance(w, BrowserTab): w.back()

    def go_forward(self):
        w = self.tabs.currentWidget()
        if isinstance(w, BrowserTab): w.forward()

    def reload(self):
        w = self.tabs.currentWidget()
        if isinstance(w, BrowserTab): w.reload()

    def go_home(self):
        w = self.tabs.currentWidget()
        if isinstance(w, BrowserTab):
            w.is_home = True
            w.setHtml(self.homepage_html)
            self.tabs.setTabText(self.tabs.currentIndex(), 'Home')
            self.url_input.clear()

    def apply_dark_mode_style(self):
        style = """
            QMainWindow {
                background: #1A1A1A;
                color: #D1D1D1;
            }

            QToolBar {
                background: #333333;
                border: none;
            }

            QToolBar QLineEdit {
                background: #2C2C2C;
                color: #D1D1D1;
                border-radius: 4px;
                padding: 4px;
            }

            QToolBar QPushButton {
                background: #4A4A4A;
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
                color: #E0E0E0;
            }

            QToolBar QPushButton:hover {
                background: #555555;
            }

            QTabBar::tab {
                background: #333333;
                color: #D1D1D1;
                padding: 8px;
                border: 1px solid #444444;
                border-radius: 5px;
            }

            QTabBar::tab:selected {
                background: #555555;
            }

            QTabBar::tab:hover {
                background: #666666;
            }

            QLineEdit {
                background: #2C2C2C;
                color: #D1D1D1;
                border: 1px solid #444444;
                padding: 6px 12px;
                border-radius: 5px;
            }

            QLineEdit:focus {
                border: 1px solid #666666;
            }

            QPushButton {
                background: #333333;
                color: #D1D1D1;
                border: none;
                border-radius: 5px;
                padding: 8px;
            }

            QPushButton:hover {
                background: #444444;
            }
        """
        self.setStyleSheet(style)

    def save_session(self):
        tabs = []
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, BrowserTab):
                tabs.append({
                    'url': w.url().toString() if not w.is_home else '',
                    'private': w.private
                })
        save_json(SESSION_FILE, tabs)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SimpleBrowser()
    window.apply_dark_mode_style()  
    window.show()
    sys.exit(app.exec_())
