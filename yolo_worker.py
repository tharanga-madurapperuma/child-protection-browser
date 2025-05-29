# yolo_worker.py
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import torch
from ultralytics import YOLO
import numpy as np
from PyQt5.QtCore import QDateTime

class YoloWorker(QObject):
    result_ready = pyqtSignal(list)  # emit detections

    def __init__(self, model_path="best.pt", class_thresholds=None):
        super().__init__()
        self.model = YOLO(model_path)
        self.class_thresholds = class_thresholds or {
            'violence': 0.90,
            'adult': 0.40,
            'weapons': 0.70,
            'drugs': 0.30,
            'gore': 0.30,
        }
        self.last_detection_time = 0
        self.detection_cooldown = 0.5  # seconds between detections

    @pyqtSlot(np.ndarray, int, int, int, int)
    def detect_from_image(self, img, viewport_width, viewport_height, scroll_x, scroll_y):
        current_time = QDateTime.currentMSecsSinceEpoch() / 1000
        if current_time - self.last_detection_time < self.detection_cooldown:
            self.result_ready.emit([])
            return

        try:
            if img.size < 10000:
                self.result_ready.emit([])
                return

            h, w = img.shape[:2]
            
            # Calculate optimal tile size that's multiple of 32
            base_tile_size = min(640, max(320, min(h, w) // 2))
            tile_size = ((base_tile_size + 31) // 32) * 32  # Round up to nearest multiple of 32
            
            # Ensure tile size is within reasonable bounds
            tile_size = min(640, max(32, tile_size))
            
            # Non-overlapping tiles
            tile_rows = max(1, int(h / tile_size))
            tile_cols = max(1, int(w / tile_size))
            
            all_detections = []
            seen_areas = set()  # To prevent duplicate detections
            
            for row in range(tile_rows):
                for col in range(tile_cols):
                    x1 = col * w // tile_cols
                    y1 = row * h // tile_rows
                    x2 = (col + 1) * w // tile_cols
                    y2 = (row + 1) * h // tile_rows
                    
                    tile = img[y1:y2, x1:x2]
                    if tile.size == 0:
                        continue

                    # Get actual tile dimensions (might be smaller at edges)
                    tile_h, tile_w = tile.shape[:2]
                    actual_imgsz = ((min(tile_h, tile_size) + 31) // 32) * 32
                    actual_imgsz = max(32, min(640, actual_imgsz))  # Keep within bounds

                    results = self.model.predict(
                        tile,
                        imgsz=actual_imgsz,  # Use calculated size that's multiple of 32
                        conf=0.4,
                        device='0' if torch.cuda.is_available() else 'cpu',
                        half=True if torch.cuda.is_available() else False,
                        max_det=10,
                        verbose=False
                    )

                    for result in results:
                        for box in result.boxes:
                            cls_name = self.model.names[int(box.cls)]
                            conf = float(box.conf)
                            if conf > self.class_thresholds.get(cls_name, 0.3):
                                bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                                # Create a unique identifier for this detection
                                area_id = f"{int(bx1)}_{int(by1)}_{int(bx2)}_{int(by2)}_{cls_name}"
                                if area_id not in seen_areas:
                                    seen_areas.add(area_id)
                                    all_detections.append({
                                        'xyxy': [
                                            bx1 + x1 + scroll_x,
                                            by1 + y1 + scroll_y,
                                            bx2 + x1 + scroll_x,
                                            by2 + y1 + scroll_y
                                        ],
                                        'class': cls_name,
                                        'conf': conf,
                                        'timestamp': QDateTime.currentDateTime().toString("hh:mm:ss")
                                    })

            self.last_detection_time = current_time
            self.result_ready.emit(all_detections)
        except Exception as e:
            print(f"[YOLO Worker] Error: {str(e)}")
            self.result_ready.emit([])

    @pyqtSlot(str, float)
    def update_threshold(self, class_name, threshold):
        """Thread-safe threshold update"""
        self.class_thresholds[class_name] = threshold

    def cleanup(self):
        """Clean up resources"""
        if hasattr(self.model, 'close'):
            self.model.close()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()