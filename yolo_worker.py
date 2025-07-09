# Modified yolo_worker.py with dynamic tiling based on browser size
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import torch
from ultralytics import YOLO
import numpy as np

class YoloWorker(QObject):
    result_ready = pyqtSignal(list)

    def __init__(self, model_path="best.pt", class_thresholds=None):
        super().__init__()
        self.model = YOLO(model_path)
        self.model.fuse()
        self.model.eval()
        if torch.cuda.is_available():
            self.model.half()

        self.class_thresholds = class_thresholds or {
            'adult': 0.35,
            'weapons': 0.55,
            'drugs': 0.25,
            'gore': 0.25,
        }

        self.pending_request = None
        self.current_processing = False
        self.last_result = []

        # Performance monitoring
        self.avg_process_time = 0.1
        self.sample_count = 0

    @pyqtSlot(np.ndarray, int, int, int, int)
    def detect_from_image(self, img, viewport_width, viewport_height, scroll_x, scroll_y):
        if self.current_processing:
            self.pending_request = (img, viewport_width, viewport_height, scroll_x, scroll_y)
            return

        self.current_processing = True
        start_time = time.time()

        threading.Thread(target=self._process_image,
                         args=(img, viewport_width, viewport_height, scroll_x, scroll_y, start_time),
                         daemon=True).start()

    def _process_image(self, img, viewport_width, viewport_height, scroll_x, scroll_y, start_time):
        try:
            detections = []
            height, width, _ = img.shape

            # Dynamically determine tile rows and columns based on viewport size
            target_tile_size = 640
            tile_cols = max(1, round(viewport_width / target_tile_size))
            tile_rows = max(1, round(viewport_height / target_tile_size))

            tile_h = height // tile_rows
            tile_w = width // tile_cols

            for row in range(tile_rows):
                for col in range(tile_cols):
                    x1 = col * tile_w
                    y1 = row * tile_h
                    x2 = x1 + tile_w if col < tile_cols - 1 else width
                    y2 = y1 + tile_h if row < tile_rows - 1 else height

                    tile = img[y1:y2, x1:x2]

                    results = self.model.predict(
                        tile,
                        imgsz=640,
                        conf=0.4,
                        device='0' if torch.cuda.is_available() else 'cpu',
                        half=True if torch.cuda.is_available() else False,
                        max_det=8,
                        verbose=False,
                        augment=False
                    )

                    for result in results:
                        for box in result.boxes:
                            cls_name = self.model.names[int(box.cls)]
                            conf = float(box.conf)
                            if conf > self.class_thresholds.get(cls_name, 0.25):
                                bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                                detections.append({
                                    'xyxy': [
                                        bx1 + x1 + scroll_x,
                                        by1 + y1 + scroll_y,
                                        bx2 + x1 + scroll_x,
                                        by2 + y1 + scroll_y
                                    ],
                                    'class': cls_name,
                                    'conf': conf
                                })

            process_time = time.time() - start_time
            self.avg_process_time = (
                (self.avg_process_time * self.sample_count + process_time) /
                (self.sample_count + 1)
            )
            self.sample_count += 1

            self.result_ready.emit(detections)

        except Exception as e:
            print(f"Detection error: {str(e)}")
            self.result_ready.emit([])

        finally:
            self.current_processing = False
            if self.pending_request:
                img, vw, vh, sx, sy = self.pending_request
                self.pending_request = None
                self.detect_from_image(img, vw, vh, sx, sy)

    @pyqtSlot(str, float)
    def update_threshold(self, class_name, threshold):
        self.class_thresholds[class_name] = threshold

    def cleanup(self):
        if hasattr(self.model, 'close'):
            self.model.close()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
