# nsfw_blur.py
import threading
import requests
import time

from PyQt5.QtCore import QObject, QTimer, pyqtSlot

API_URL = "http://54.145.47.57:8000/predict"  # ← Your AWS endpoint
CONF_THRESHOLD = 0.80                          # blur when confidence >= 0.80
MIN_LEN = 20                                   # ignore tiny paragraphs
SCAN_INTERVAL_MS = 1200                        # how often we scan DOM
MAX_PARALLEL = 3                               # cap concurrent HTTP calls per tab

def _classify_text(text: str):
    """Call your AWS API with a single paragraph."""
    try:
        resp = requests.post(API_URL, json={"text": text}, timeout=8)
        if resp.status_code == 200:
            data = resp.json() or {}
            label = int(data.get("label", 0))
            conf = float(data.get("confidence", 0.0))
            return label, conf
    except Exception as e:
        print(f"[TextBlur] API error: {e}")
    return 0, 0.0

class TextDetectionManager(QObject):
    """
    Periodically scans <p> elements, sends them to the text classifier,
    and blurs those flagged as unsafe.
    """
    def __init__(self, browser_page,
                 conf_threshold: float = CONF_THRESHOLD,
                 min_len: int = MIN_LEN,
                 scan_interval_ms: int = SCAN_INTERVAL_MS,
                 max_parallel: int = MAX_PARALLEL):
        super().__init__()
        self.page = browser_page  # QWebEngineView
        self.conf_threshold = conf_threshold
        self.min_len = min_len
        self.max_parallel = max_parallel

        # Track which indices we already processed so we don't hammer the API
        self._processed_ok = set()      # safe
        self._processed_flagged = set() # already blurred
        self._inflight = set()          # indices currently being classified

        # Periodic scanner
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.scan_once)
        self._timer.start(scan_interval_ms)

        # Re-scan on scroll to catch newly-visible content
        try:
            self.page.page().scrollPositionChanged.connect(self.scan_once)
        except Exception:
            pass

    def stop(self):
        self._timer.stop()

    @pyqtSlot()
    def handle_dom_changed(self):
        """
        Reset caches when DOM changes significantly.
        This prevents stale 'processed' states when new content arrives.
        """
        self._processed_ok.clear()
        self._processed_flagged.clear()
        self._inflight.clear()
        self.scan_once()

    @pyqtSlot()
    def scan_once(self):
        """Get paragraphs and enqueue a few for classification."""
        js = f"""
        (function() {{
            const els = Array.from(document.getElementsByTagName('p'));
            const out = [];
            for (let i = 0; i < els.length; i++) {{
                const t = (els[i].innerText || '').trim();
                if (t.length >= {self.min_len}) {{
                    out.push({{ index: i, text: t }});
                }}
            }}
            return out;
        }})();
        """
        try:
            self.page.page().runJavaScript(js, self._handle_paragraphs)
        except Exception as e:
            print(f"[TextBlur] JS run error: {e}")

    def _handle_paragraphs(self, paragraphs):
        if not paragraphs:
            return

        # Only process a limited number concurrently
        available_slots = self.max_parallel - len(self._inflight)
        if available_slots <= 0:
            return

        # Pick candidates that are not processed or inflight yet
        candidates = []
        for item in paragraphs:
            idx = item.get("index")
            if idx is None:
                continue
            if idx in self._processed_ok or idx in self._processed_flagged or idx in self._inflight:
                continue
            candidates.append(item)
            if len(candidates) >= available_slots:
                break

        for item in candidates:
            idx = item["index"]
            text = item["text"]
            self._inflight.add(idx)
            threading.Thread(target=self._classify_and_blur, args=(idx, text), daemon=True).start()

    def _classify_and_blur(self, index: int, text: str):
        label, conf = _classify_text(text)
        should_blur = (label == 1 and conf >= self.conf_threshold)

        # Hand results back to the UI thread
        def _apply():
            if should_blur:
                self._blur_paragraph(index)
                self._processed_flagged.add(index)
            else:
                self._processed_ok.add(index)
            self._inflight.discard(index)

        # Use runJavaScript to hop back to the GUI thread safely
        try:
            self.page.page().runJavaScript("1+1", lambda _: _apply())
        except Exception:
            _apply()

    def _blur_paragraph(self, index: int):
        blur_js = f"""
        (function() {{
            const p = document.getElementsByTagName('p')[{index}];
            if (!p) return;
            // Avoid re-applying styles if already blurred
            if (p.dataset._blurred === '1') return;
            p.style.filter = 'blur(5px)';
            p.style.backgroundColor = 'rgba(0, 0, 0, 0.08)';
            p.style.transition = 'filter 120ms ease';
            p.dataset._blurred = '1';
        }})();
        """
        try:
            self.page.page().runJavaScript(blur_js)
        except Exception as e:
            print(f"[TextBlur] Blur JS error: {e}")
