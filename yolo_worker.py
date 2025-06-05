# yolo_worker.py
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import torch
from ultralytics import YOLO
import numpy as np
from PyQt5.QtCore import QDateTime

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
            'violence': 0.85,  # Slightly lower thresholds
            'adult': 0.35,
            'weapons': 0.45,
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
        # Store the latest request if we're busy processing
        if self.current_processing:
            self.pending_request = (img, viewport_width, viewport_height, scroll_x, scroll_y)
            return
            
        self.current_processing = True
        start_time = time.time()
        
        # Process in a separate thread to keep UI responsive
        threading.Thread(target=self._process_image, 
                        args=(img, viewport_width, viewport_height, scroll_x, scroll_y, start_time),
                        daemon=True).start()

    def _process_image(self, img, viewport_width, viewport_height, scroll_x, scroll_y, start_time):
        try:
            if img.size < 8000:  # Balanced minimum size
                detections = []
            else:
                # Single tile processing for speed
                results = self.model.predict(
                    img,
                    imgsz=640,
                    conf=0.4,
                    device='0' if torch.cuda.is_available() else 'cpu',
                    half=True if torch.cuda.is_available() else False,
                    max_det=8,
                    verbose=False,
                    augment=False
                )
                
                detections = []
                for result in results:
                    for box in result.boxes:
                        cls_name = self.model.names[int(box.cls)]
                        conf = float(box.conf)
                        if conf > self.class_thresholds.get(cls_name, 0.25):
                            bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                            detections.append({
                                'xyxy': [
                                    bx1 + scroll_x,
                                    by1 + scroll_y,
                                    bx2 + scroll_x,
                                    by2 + scroll_y
                                ],
                                'class': cls_name,
                                'conf': conf
                            })
            
            # Update performance metrics
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
            # Process pending request if exists
            if self.pending_request:
                img, vw, vh, sx, sy = self.pending_request
                self.pending_request = None
                self.detect_from_image(img, vw, vh, sx, sy)

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