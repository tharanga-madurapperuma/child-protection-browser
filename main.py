# IMPORTS
import os
import sys
import numpy as np

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWebChannel import QWebChannel
from ultralytics import YOLO

# Custom modules
from text_extractor import extract_text_from_page
from browser_overlay import BrowserOverlay
from content_monitor import ContentMonitor
from nsfw_blur import TextDetectionManager


from bridge import JSBridge

import time

# MAIN WINDOW
class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.video_sites = ["youtube", "tiktok", "vimeo", "dailymotion", "twitch"]

        # Initialize warning system
        self.last_dom_change_time = {}
        self.warning_label = QLabel()
        self.warning_label.setStyleSheet("""
            background-color: #000000; 
            border-radius: 3px;
            color: #000000; 
        """)
        self.warning_label.hide()
        self.statusBar().addPermanentWidget(self.warning_label)

        # Initialize content monitoring system
        self.monitors = {}  # To store monitors for each tab
        self.overlays = {}  # To store overlays for each tab

        # For text detection
        self.text_managers = {}

        # Set up web browser tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.setCentralWidget(self.tabs)

        # Connect tab signals
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)

        # Setup navigation toolbar
        self.setup_navigation_toolbar()
        
        # Setup menus
        self.setup_menus()

        # Window styling
        self.setWindowTitle("Child Protection Browser")
        self.setWindowIcon(QIcon(os.path.join('icons', 'cil-screen-desktop.png')))
        self.apply_stylesheet()

        # Load default home page
        self.add_new_tab(QUrl('http://www.google.com'), 'Homepage')
        self.resize(1280, 720)
        self.show()


    def setup_navigation_toolbar(self):
        """Initialize the navigation toolbar with buttons"""
        navtb = QToolBar("Navigation")
        navtb.setIconSize(QSize(16, 16))
        self.addToolBar(navtb)

        # Back button
        back_btn = QAction(QIcon(os.path.join('icons', 'cil-arrow-circle-left.png')), "Back", self)
        back_btn.triggered.connect(lambda: self.tabs.currentWidget().back())
        navtb.addAction(back_btn)
 
        # Forward button
        next_btn = QAction(QIcon(os.path.join('icons', 'cil-arrow-circle-right.png')), "Forward", self)
        next_btn.triggered.connect(lambda: self.tabs.currentWidget().forward())
        navtb.addAction(next_btn)

        # Refresh button
        reload_btn = QAction(QIcon(os.path.join('icons', 'cil-reload.png')), "Reload", self)
        reload_btn.triggered.connect(lambda: self.tabs.currentWidget().reload())
        navtb.addAction(reload_btn)

        # Home button
        home_btn = QAction(QIcon(os.path.join('icons', 'cil-home.png')), "Home", self)
        home_btn.triggered.connect(self.navigate_home)
        navtb.addAction(home_btn)

        # HTTPS icon
        self.httpsicon = QLabel()  
        self.httpsicon.setPixmap(QPixmap(os.path.join('icons', 'cil-lock-unlocked.png')))
        navtb.addWidget(self.httpsicon)

        # URL bar
        self.urlbar = QLineEdit()
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        navtb.addWidget(self.urlbar)

        # Stop button
        stop_btn = QAction(QIcon(os.path.join('icons', 'cil-media-stop.png')), "Stop", self)
        stop_btn.triggered.connect(lambda: self.tabs.currentWidget().stop())
        navtb.addAction(stop_btn)

    def setup_menus(self):
        """Initialize the menu bar"""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        new_tab_action = QAction(QIcon(os.path.join('icons', 'cil-library-add.png')), "New Tab", self)
        new_tab_action.triggered.connect(lambda _: self.add_new_tab())
        file_menu.addAction(new_tab_action)

        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        navigate_home_action = QAction(QIcon(os.path.join('icons', 'cil-exit-to-app.png')), "Homepage", self)
        navigate_home_action.triggered.connect(self.navigate_home)
        help_menu.addAction(navigate_home_action)

    def apply_stylesheet(self):
        """Apply the dark mode stylesheet"""
        self.setStyleSheet("""QWidget{
           background-color: rgb(48, 48, 48);
           color: rgb(255, 255, 255);
        }
        QTabWidget::pane {
            border-top: 2px solid rgb(90, 90, 90);
            position: absolute;
            top: -0.5em;
            color: rgb(255, 255, 255);
            padding: 5px;
        }
        QTabWidget::tab-bar { alignment: left; }
        QLabel, QToolButton, QTabBar::tab {
            background: rgb(48, 48, 48);
            border-radius: 6px;
            min-width: 8ex;
            padding: 5px;
            margin-right: 2px;
            color: rgb(255, 255, 255);
        }
        QTabBar::tab{ margin: 3px 0; padding: 5px 15px; }
        QTabBar{ margin: 0px 5px; }
        QLabel:hover, QToolButton::hover, QTabBar::tab:selected, QTabBar::tab:hover {
            background: rgb(49, 49, 49);
            border: 2px solid rgb(0, 36, 36);
            background-color: rgb(0, 36, 36);
        }
        QLineEdit {
            border: 2px solid rgb(0, 36, 36);
            border-radius: 6px;
            padding: 5px;
            background-color: rgb(0, 36, 36);
            color: rgb(255, 255, 255);
        }
        QLineEdit:hover { border: 2px solid rgb(0, 66, 124); }
        QLineEdit:focus{
            border: 2px solid rgb(0, 136, 255);
            color: rgb(200, 200, 200);
        }
        QPushButton{
            background: rgb(49, 49, 49);
            border: 2px solid rgb(0, 36, 36);
            background-color: rgb(0, 36, 36);
            padding: 5px;
            border-radius: 10px;
        }""")

    def add_new_tab(self, qurl=None, label="Blank"):
        """Add a new browser tab with monitoring"""
        if qurl is None:
            qurl = QUrl('http://www.google.com')

        browser = QWebEngineView()
        browser.setUrl(qurl)

        # Clear detections on URL change
        browser.urlChanged.connect(lambda q: self.clear_tab_detections(browser))
    
        # Clear detections on page load start
        browser.loadStarted.connect(lambda: self.clear_tab_detections(browser))

        browser.urlChanged.connect(lambda q, b=browser: self.update_urlbar(q, b))


        # Connect text extraction to loadFinished signal
        browser.loadFinished.connect(lambda ok: self.handle_page_loaded(browser, ok))

        # Connect scroll handler
        browser.page().scrollPositionChanged.connect(
            lambda: self.overlays[self.tabs.indexOf(browser)].update_position()
        )


        # Enable hardware acceleration
        browser.settings().setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        browser.settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        browser.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        browser.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        browser.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        browser.settings().setAttribute(QWebEngineSettings.WebGLEnabled, True)

        # Fix for Pexels-like sites
        browser.page().profile().setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        )
        browser.page().profile().setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)



        # Bridge setup
        bridge = JSBridge()

        # Set up JS channel
        channel = QWebChannel()
        channel.registerObject("pyObj", bridge)
        browser.page().setWebChannel(channel)

        # Load the qwebchannel.js file
        qwebchannel_js = QFile(":/qtwebchannel/qwebchannel.js")
        if qwebchannel_js.open(QIODevice.ReadOnly):
            browser.page().runJavaScript(qwebchannel_js.readAll().data().decode())
            qwebchannel_js.close()
        else:
            print("Failed to load qwebchannel.js")

        # Inject JavaScript for mutation observer
        browser.page().runJavaScript("""
            (function() {
                if (window.channelInjected) return;  // prevent duplicate injection
                window.channelInjected = true;
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.pyObj = channel.objects.pyObj;

                    const observer = new MutationObserver(() => {
                        if (window.pyObj && window.pyObj.notifyDomChanged) {
                            window.pyObj.notifyDomChanged();
                        }
                    });

                    observer.observe(document.body, { childList: true, subtree: true });
                });
            })();
        """)

        # Callbacks on DOM change
        bridge.domChanged.connect(lambda: self.on_dom_change(browser))

        # Create overlay for this tab
        overlay = BrowserOverlay(browser)
        overlay.hide()
        
        # Create monitor for this tab
        monitor = ContentMonitor(browser)
        monitor.detection_signal.connect(
            lambda data, pixmap: self.handle_detections(browser, data, pixmap)  # Pass full dict
        )
        
        # Store references
        tab_index = self.tabs.addTab(browser, label)
        self.monitors[tab_index] = monitor
        self.overlays[tab_index] = overlay

        # Text blur manager for this tab
        txt_mgr = TextDetectionManager(browser)
        self.text_managers[tab_index] = txt_mgr

        # Re-scan on DOM changes
        bridge.domChanged.connect(txt_mgr.handle_dom_changed)

        
        # Start monitoring if this is the current tab
        if tab_index == self.tabs.currentIndex():
            monitor.start()
        
        self.tabs.setCurrentIndex(tab_index)
        browser.loadFinished.connect(lambda: monitor.adaptive_check_content())  # New line
        return browser

    # Modify the handle_detections method
    def handle_detections(self, browser, detection_data, pixmap):
        tab_index = self.tabs.indexOf(browser)
        if tab_index == -1:
            return
            
        overlay = self.overlays.get(tab_index)
        if not overlay:
            return
            
        # Check if this is a video site
        is_video = self.is_video_site(browser.url())
        
        # For video sites, always update detections (don't preserve old ones)
        if is_video:
            overlay.video_mode = True
            has_detections = bool(detection_data and detection_data.get('detections'))
            
            if has_detections:
                det_count = len(detection_data['detections'])
                self.warning_label.setText(f"⚠️ Blocked {det_count} inappropriate regions")
                # Force the warning label to stay visible for at least 1 second
                QTimer.singleShot(1000, lambda: self.warning_label.setVisible(has_detections and overlay.video_mode))
            else:
                self.warning_label.setVisible(False)
            
            # Always update with new detections, don't preserve old ones
            overlay.set_detections(detection_data if has_detections else None)
        else:
            # Original behavior for non-video sites
            overlay.video_mode = False
            has_detections = bool(detection_data and detection_data.get('detections'))
            
            if has_detections:
                det_count = len(detection_data['detections'])
                self.warning_label.setText(f"⚠️ Blocked {det_count} inappropriate regions")
            self.warning_label.setVisible(has_detections)
            
            overlay.set_detections(detection_data if has_detections else None)

    # ADD NEW TAB ON DOUBLE CLICK ON TABS
    def tab_open_doubleclick(self, i):
        if i == -1:  # No tab under the click
            self.add_new_tab()

    # CLOSE TABS 
    def close_current_tab(self, i):
        if self.tabs.count() < 2:
            return

        # Clean up monitor and overlay
        monitor = self.monitors.get(i)
        if monitor:
            monitor.stop_monitoring()
            if hasattr(monitor, "worker_thread") and monitor.worker_thread.isRunning():
                monitor.worker_thread.quit()
                monitor.worker_thread.wait()
            del self.monitors[i]

        if i in self.overlays:
            self.overlays[i].deleteLater()
            del self.overlays[i]

        self.tabs.removeTab(i)

        txt_mgr = self.text_managers.get(i)
        if txt_mgr:
            txt_mgr.stop()
            del self.text_managers[i]


    # UPDATE URL TEXT WHEN ACTIVE TAB IS CHANGED
    def update_urlbar(self, q, browser=None):
        #q = QURL
        if browser != self.tabs.currentWidget():
            # If this signal is not from the current tab, ignore
            return
        # URL Schema
        if q.scheme() == 'https':
            # If schema is https change icon to locked padlock to show that the webpage is secure
            self.httpsicon.setPixmap(QPixmap(os.path.join('icons', 'cil-lock-locked.png')))

        else:
            # If schema is not https change icon to locked padlock to show that the webpage is unsecure
            self.httpsicon.setPixmap(QPixmap(os.path.join('icons', 'cil-lock-unlocked.png')))

        self.urlbar.setText(q.toString())
        self.urlbar.setCursorPosition(0)



    # ACTIVE TAB CHANGE ACTIONS
    def current_tab_changed(self, i):
        # i = tab index
        # GET CURRENT TAB URL
        qurl = self.tabs.currentWidget().url()
        # UPDATE URL TEXT
        self.update_urlbar(qurl, self.tabs.currentWidget())
        # UPDATE WINDOWS TITTLE
        self.update_title(self.tabs.currentWidget())
        
        # Start monitoring for current tab, stop others
        for index, monitor in self.monitors.items():
            if index == i:
                if not monitor.active:
                    monitor.start()
            else:
                monitor.stop_monitoring()


        # Enable text manager only on active tab
        for index, mgr in self.text_managers.items():
            if index == i:
                # nothing to do; it runs on a timer
                pass
            else:
                # pause others to reduce API calls (optional)
                mgr.handle_dom_changed()  # clears queues/caches



    # UPDATE WINDOWS TITTLE
    def update_title(self, browser):
        if browser != self.tabs.currentWidget():
            # If this signal is not from the current ACTIVE tab, ignore
            return

        title = self.tabs.currentWidget().page().title()
        self.setWindowTitle(title)


    # NAVIGATE TO PASSED URL
    def navigate_to_url(self):
        q = QUrl(self.urlbar.text())
        if q.scheme() == "":
            q.setScheme("http")

        browser = self.tabs.currentWidget()
        # Clear detections before navigation
        self.clear_tab_detections(browser)
        browser.setUrl(q)

        tab_index = self.tabs.currentIndex()

        # 🧠 Safe reset of overlay geometry and monitor
        if tab_index in self.overlays:
            self.overlays[tab_index].hide()
            self.overlays[tab_index].update_position()

        if tab_index in self.monitors:
            monitor = self.monitors[tab_index]
            monitor.stop_monitoring()
            monitor.start()

    def clear_tab_detections(self, browser):
        """Clear detections for a specific tab"""
        tab_index = self.tabs.indexOf(browser)
        if tab_index in self.overlays:
            self.overlays[tab_index].clear_detections()
            self.warning_label.hide()
        
        tab_index = self.tabs.indexOf(browser)
        if tab_index in self.text_managers:
            self.text_managers[tab_index].handle_dom_changed()




    # NAVIGATE TO DEFAULT HOME PAGE
    def navigate_home(self):
        self.tabs.currentWidget().setUrl(QUrl("http://www.google.com"))

    # [Keep all your existing methods like tab_open_doubleclick, close_current_tab, 
    # update_urlbar, current_tab_changed, update_title, navigate_to_url, navigate_home]
    # ... (they remain exactly the same as in your original code)

    def resizeEvent(self, event):
        """Ensure overlays reposition properly on window resize"""
        super().resizeEvent(event)
        for overlay in self.overlays.values():
            overlay.update_position()

    def on_dom_change(self, browser):
        print("\n\n\n\n\n\nDOM changed, extracting text...")
        tab_index = self.tabs.indexOf(browser)
        now = time.time()
        last_time = self.last_dom_change_time.get(tab_index, 0)

        if now - last_time < 1.5:  # Only allow every 1.5s
            return

        self.last_dom_change_time[tab_index] = now

        monitor = self.monitors.get(tab_index)
        if monitor:
            monitor.check_content()

    def handle_page_loaded(self, browser, ok):
        if not ok:
            print(f"Page failed to load: {browser.url().toString()}")
            return

        print(f"Page loaded successfully: {browser.url().toString()}")
        extract_text_from_page(browser)
        # from nsfw_blur import TextDetectionManager
        # TextDetectionManager(browser)


        tab_index = self.tabs.indexOf(browser)

        # 🛠 Reconnect overlay update on scroll
        browser.page().scrollPositionChanged.connect(
            lambda: self.overlays[tab_index].update_position()
        )

        if tab_index in self.overlays:
            self.overlays[tab_index].update_position()
            self.overlays[tab_index].show()

        if tab_index in self.monitors:
            monitor = self.monitors[tab_index]
            if not monitor.active:
                monitor.start()

    def is_video_site(self, url):
        """Check if current URL is a video streaming site"""
        url_str = url.toString().lower()
        return any(video_site in url_str for video_site in self.video_sites)


app = QApplication(sys.argv)
app.setApplicationName("Child Protection Browser")  
app.setOrganizationName("Child Protection")
app.setOrganizationDomain("childprotection.org")

window = MainWindow()
app.exec_()