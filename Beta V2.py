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

os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
    '--ignore-gpu-blacklist '
    '--enable-gpu-rasterization '
    '--enable-zero-copy '
    '--use-gl=desktop'
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

# JavaScript-based ad blocker (simple common selectors)
ADBLOCK_JS = """
const selectors = [
  '[id*="ad"]', '[class*="ad"]', '[class*="ads"]', '[class*="advert"]',
  'iframe[src*="ads"]', 'iframe[src*="doubleclick"]', 'iframe[src*="adservice"]',
  'div[data-ad]', 'div[data-ad-client]', 'div[data-ad-slot]'
];
selectors.forEach(sel => {
  document.querySelectorAll(sel).forEach(el => el.remove());
});
"""

class BrowserTab(QWebEngineView):
    def __init__(self, profile, history_list, homepage_html, private=False):
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
        self.history = history_list
        self.homepage_html = homepage_html
        self.is_home = True
        self.setVisible(False)
        self.setHtml(self.homepage_html)
        self.loadFinished.connect(self.finish_load)
        self.loadFinished.connect(self.inject_adblock_js)
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
        if url and url not in self.history and not self.private:
            self.history.append(url)
            save_json(HISTORY_FILE, self.history)

    def on_render_crash(self, status, code):
        QMessageBox.critical(
            self, 'Renderer Crashed', f'Status: {status.name}\nCode: {code}'
        )
        
    def inject_adblock_js(self):
        if not self.is_home:
            self.page().runJavaScript(ADBLOCK_JS)

class SimpleBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Zeal Kimones Light Weight Private Web Browser')
        self.resize(1200, 800)
        self.history = load_json(HISTORY_FILE, [])
        self.bookmarks = load_json(BOOKMARKS_FILE, [])
        self.dark_mode = False

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

        bookmark_btn = QAction('🔖', self)
        bookmark_btn.triggered.connect(self.add_bookmark)
        toolbar.addAction(bookmark_btn)

        show_bm_btn = QAction('📂', self)
        show_bm_btn.triggered.connect(self.show_bookmarks)
        toolbar.addAction(show_bm_btn)

        private_btn = QAction('🕵️‍♂️', self)
        private_btn.setToolTip('New Private Tab')
        private_btn.triggered.connect(self.add_private_tab)
        toolbar.addAction(private_btn)

        devtools_btn = QAction('⚙️', self)
        devtools_btn.setToolTip('Toggle Dev Tools for Current Tab')
        devtools_btn.triggered.connect(self.toggle_devtools)
        toolbar.addAction(devtools_btn)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.sync_url)
        self.setCentralWidget(self.tabs)

        # Load session or add default tab
        session_tabs = load_json(SESSION_FILE, [])
        if session_tabs:
            for s in session_tabs:
                url = s.get('url')
                private = s.get('private', False)
                self.add_tab(url, private=private)
        else:
            self.add_tab()

        # On close save session
        self.app = QApplication.instance()
        self.app.aboutToQuit.connect(self.save_session)

    def add_tab(self, url=None, private=False):
        profile = QWebEngineProfile() if private else QWebEngineProfile.defaultProfile()
        if private:
            profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
            profile.setCachePath('')
            profile.setPersistentStoragePath('')

        browser = BrowserTab(profile, self.history, self.homepage_html, private=private)
        idx = self.tabs.addTab(browser, 'Home' + (' 🔒' if private else ''))
        self.tabs.setCurrentIndex(idx)
        if url:
            browser.load_url(url)
            self.tabs.setTabText(idx, 'Loading...')
        browser.titleChanged.connect(lambda t, i=idx: self.tabs.setTabText(i, t or 'New Tab'))
        browser.urlChanged.connect(lambda q, b=browser: self.update_url(q, b))
        self.sync_url(idx)

    def add_private_tab(self):
        self.add_tab(private=True)

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
        if not url.startswith(('http://', 'https://')):
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

    def add_bookmark(self):
        w = self.tabs.currentWidget()
        if isinstance(w, BrowserTab) and not w.is_home:
            url = w.url().toString()
            title = w.title()
            if any(b['url'] == url for b in self.bookmarks):
                QMessageBox.information(self, 'Bookmark', 'This page is already bookmarked.')
                return
            self.bookmarks.append({'title': title, 'url': url})
            save_json(BOOKMARKS_FILE, self.bookmarks)
            QMessageBox.information(self, 'Bookmark', f'Bookmarked: {title}')

    def show_bookmarks(self):
        if not self.bookmarks:
            QMessageBox.information(self, 'Bookmarks', 'No bookmarks saved.')
            return
        items = [f"{bm['title']} - {bm['url']}" for bm in self.bookmarks]
        item, ok = QInputDialog.getItem(self, 'Bookmarks', 'Select to open:', items, 0, False)
        if ok and item:
            url = item.split(' - ')[-1]
            self.add_tab(url)

    def toggle_devtools(self):
        w = self.tabs.currentWidget()
        if isinstance(w, BrowserTab):
            if hasattr(w, 'dev_tools') and w.dev_tools.isVisible():
                w.dev_tools.close()
            else:
                w.dev_tools = QWebEngineView()
                w.dev_tools.setWindowTitle('Developer Tools - ' + w.title())
                w.page().setDevToolsPage(w.dev_tools.page())
                w.dev_tools.resize(800, 600)
                w.dev_tools.show()

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
    window.show()
    sys.exit(app.exec_())
