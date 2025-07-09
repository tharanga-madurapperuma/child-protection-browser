# text_worker.py
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import threading
from gradio_client import Client

class TextWorker(QObject):
    result_ready = pyqtSignal(str, int)  # (text, index)

    def __init__(self):
        super().__init__()
        self.client = Client("https://rerandaka-child-protection-api.hf.space/")
        self.queue = []
        self.running = False

    @pyqtSlot(str, int)
    def classify_paragraph(self, text, index):
        if self.running:
            self.queue.append((text, index))
            return
        self.running = True
        threading.Thread(target=self._process, args=(text, index), daemon=True).start()

    def _process(self, text, index):
        try:
            result = self.client.predict(text, api_name="/classify")
            print(f"[TextWorker] Got result: {result} for paragraph #{index}")
            if result == 1:
                self.result_ready.emit(text, index)
        except Exception as e:
            print(f"[TextWorker] API error: {e}")
        finally:
            self.running = False
            if self.queue:
                next_text, next_index = self.queue.pop(0)
                self.classify_paragraph(next_text, next_index)
