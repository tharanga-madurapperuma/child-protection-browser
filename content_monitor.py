from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QMutex, QMutexLocker, QMetaObject, Qt, QThread, Q_ARG
from PyQt5.QtGui import QImage, QPixmap
import numpy as np
import os
import time
import cv2
from datetime import datetime
import threading

from yolo_worker import YoloWorker

class ContentMonitor(QObject):
    detection_signal = pyqtSignal(dict, QPixmap)
    
    def __init__(self, browser_window):
        super().__init__()
        self.class_thresholds = {
            'violence': 0.85,
            'adult': 0.35,
            'weapons': 0.45,
            'drugs': 0.25,
            'gore': 0.25,
        }

        self.browser = browser_window
        self.processing_lock = QMutex()
        self.active = True
        self.last_detection_time = 0
        self.adaptive_interval = 100  # Start with 100ms (10fps)
        self.last_process_time = 0
        self.current_pixmap = None
        self.pending_detection = False

        # Debug directories
        self.debug_dir = "browser_captures"
        self.detection_dir = "detection_results"
        os.makedirs(self.debug_dir, exist_ok=True)
        os.makedirs(self.detection_dir, exist_ok=True)

        # Set up YOLO worker in another thread
        self.worker_thread = QThread()
        self.yolo_worker = YoloWorker(class_thresholds=self.class_thresholds)
        self.yolo_worker.moveToThread(self.worker_thread)
        self.yolo_worker.result_ready.connect(self.handle_results)
        self.worker_thread.start()

        # Set up monitoring timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.adaptive_check_content)
        self.timer.start(self.adaptive_interval)

        self.last_activity_time = time.time()
        self.activity_timeout = 2.0  # 2 second

    def start(self):
        self.active = True
        self.timer.start()
    
    def stop_monitoring(self):
        self.active = False
        self.timer.stop()
        
        if self.processing_lock.tryLock():
            self.processing_lock.unlock()
        
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.yolo_worker.cleanup()
            self.worker_thread.quit()
            self.worker_thread.wait(1000)
            if self.worker_thread.isRunning():
                self.worker_thread.terminate()

    def adaptive_check_content(self):
        if not self.active or not self.browser.isVisible():
            return

        now = time.time()
        if now - self.last_process_time < self.adaptive_interval/1000:
            return
            
        if not self.processing_lock.tryLock():
            return
            
        try:
            # Capture the visible portion
            self.current_pixmap = self.browser.grab()
            
            # Get viewport information
            viewport_size = self.browser.size()
            scroll_pos = self.browser.page().scrollPosition()
            
            # Convert to numpy array
            qimg = self.current_pixmap.toImage()
            ptr = qimg.bits()
            ptr.setsize(qimg.byteCount())
            arr = np.frombuffer(ptr, np.uint8).reshape((qimg.height(), qimg.width(), 4))[:,:,:3]
            
            # Submit for detection
            self.yolo_worker.detect_from_image(
                cv2.cvtColor(arr, cv2.COLOR_RGB2BGR),
                viewport_size.width(),
                viewport_size.height(),
                scroll_pos.x(),
                scroll_pos.y()
            )
            
            self.last_process_time = now
            
            # Dynamically adjust interval based on worker performance
            if hasattr(self.yolo_worker, 'avg_process_time'):
                target_fps = 10  # Our goal
                current_fps = 1/max(0.001, self.yolo_worker.avg_process_time)
                
                if current_fps < target_fps * 0.8:  # If we're falling behind
                    self.adaptive_interval = min(200, self.adaptive_interval + 10)
                elif current_fps > target_fps * 1.2 and self.adaptive_interval > 50:  # If we can go faster
                    self.adaptive_interval = max(50, self.adaptive_interval - 10)
                    
                self.timer.setInterval(self.adaptive_interval)
                
        except Exception as e:
            print(f"Capture error: {str(e)}")
        finally:
            self.processing_lock.unlock()

    def handle_results(self, detections):
        """Process and emit detection results"""
        if not self.active or not self.current_pixmap:
            return

        scroll_pos = self.browser.page().scrollPosition()
        viewport_size = self.browser.size()
        
        viewport_detections = []
        if detections:  # Only process if we have detections
            for det in detections:
                try:
                    x1 = det['xyxy'][0] - scroll_pos.x()
                    y1 = det['xyxy'][1] - scroll_pos.y()
                    x2 = det['xyxy'][2] - scroll_pos.x()
                    y2 = det['xyxy'][3] - scroll_pos.y()
                    
                    if not (x2 < 0 or y2 < 0 or x1 > viewport_size.width() or y1 > viewport_size.height()):
                        viewport_detections.append({
                            'xyxy': [x1, y1, x2, y2],
                            'class': det['class'],
                            'conf': det['conf']
                        })
                except Exception as e:
                    print(f"Detection processing error: {str(e)}")
                    continue
        
        # Package detection data
        detection_data = {
            'detections': viewport_detections,
            'scroll_x': scroll_pos.x(),
            'scroll_y': scroll_pos.y(),
            'viewport_width': viewport_size.width(),
            'viewport_height': viewport_size.height()
        }
        
        print(f"[Detection] Found {len(detections)} raw, {len(viewport_detections)} visible")
        self.detection_signal.emit(detection_data, self.current_pixmap)

    def update_threshold(self, class_name, threshold):
        """Thread-safe threshold update"""
        with QMutexLocker(self.processing_lock):
            self.class_thresholds[class_name] = threshold
            QMetaObject.invokeMethod(
                self.yolo_worker,
                "update_threshold",
                Qt.QueuedConnection,
                Q_ARG(str, class_name),
                Q_ARG(float, threshold)
            )