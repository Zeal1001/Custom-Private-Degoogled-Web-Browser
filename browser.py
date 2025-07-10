import sys
import os
import json
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QTabWidget,
    QToolBar, QAction, QMessageBox
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineProfile, QWebEnginePage, QWebEngineSettings
)
import traceback

# Enable GPU acceleration flags for QtWebEngine
os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
    '--ignore-gpu-blacklist '
    '--enable-gpu-rasterization '
    '--enable-zero-copy '
    '--use-gl=desktop'
)

# Global exception hook

def excepthook(exc_type, exc_value, exc_tb):
    err = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    QMessageBox.critical(None, 'Error', err)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

# History persistence
def load_history(path='history.json'):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return []

def save_history(history, path='history.json'):
    try:
        with open(path, 'w') as f:
            json.dump(history, f, indent=2)
    except:
        pass

# Custom homepage HTML
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
    <p>Your secure, privacy-first browsing experience, I think if i made it right.......</p>
</body>
</html>
'''

class BrowserTab(QWebEngineView):
    def __init__(self, profile, history_list, homepage_html):
        super().__init__()
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
        self.history = history_list
        self.homepage_html = homepage_html
        self.is_home = True
        # Hide until ready
        self.setVisible(False)
        self.setHtml(self.homepage_html)
        self.loadFinished.connect(self.finish_load)

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
        if url and url not in self.history:
            self.history.append(url)
            save_history(self.history)

    def on_render_crash(self, status, code):
        QMessageBox.critical(
            self, 'Renderer Crashed', f'Status: {status.name}\nCode: {code}'
        )

class SimpleBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Zeal Kimones Light Weight Private Web Browser')
        self.resize(1200, 800)
        self.history = load_history()
        self.dark_mode = False
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setHttpUserAgent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/122 Safari/537.36'
        )
        self.homepage_html = create_homepage_html()

        # Toolbar
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

        self.theme_btn = QAction('🌙', self)
        self.theme_btn.triggered.connect(self.toggle_theme)
        toolbar.addAction(self.theme_btn)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_url)
        self.setCentralWidget(self.tabs)

        # Initial tab
        self.add_tab()

    def add_tab(self, url=None):
        browser = BrowserTab(self.profile, self.history, self.homepage_html)
        idx = self.tabs.addTab(browser, 'Home')
        self.tabs.setCurrentIndex(idx)
        if url:
            browser.load_url(url)
            self.tabs.setTabText(idx, 'New Tab')
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
        url = self.url_input.text().strip()
        if not url.startswith(('http://','https://')):
            url = 'https://' + url
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

    def toggle_theme(self):
        if not self.dark_mode:
            style = """
                QMainWindow { background: #121212; }
                QToolBar { background: #1e1e1e; }
                QLineEdit { background: #2b2b2b; color: #fff; }
                QTabBar::tab { background: #333; color: #fff; padding: 8px; }
                QTabBar::tab:selected { background: #555; }
            """
            self.setStyleSheet(style)
            self.theme_btn.setText('☀️')
        else:
            self.setStyleSheet('')
            self.theme_btn.setText('🌙')
        self.dark_mode = not self.dark_mode

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SimpleBrowser()
    window.show()
    sys.exit(app.exec_())
