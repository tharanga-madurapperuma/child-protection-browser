from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QMutex, QMutexLocker, QMetaObject, Qt, Q_ARG, QThread
from PyQt5.QtGui import QImage, QPixmap
import numpy as np
import os
import time
import cv2
from datetime import datetime

from yolo_worker import YoloWorker

class ContentMonitor(QObject):
    detection_signal = pyqtSignal(dict, QPixmap)
    
    def __init__(self, browser_window):
        super().__init__()
        self.class_thresholds = {
            'violence': 0.90,
            'adult': 0.40,
            'weapons': 0.50,
            'drugs': 0.30,
            'gore': 0.30,
        }

        self.browser = browser_window
        self.processing_lock = QMutex()
        self.active = True
        self.skip_frame = False
        self.last_detection_time = 0
        self.detection_cooldown = 1.0  # seconds

        # Debug directories
        self.debug_dir = "browser_captures"
        self.detection_dir = "detection_results"
        os.makedirs(self.debug_dir, exist_ok=True)
        os.makedirs(self.detection_dir, exist_ok=True)

        # Set up YOLO worker in another thread
        self.thread = QThread()
        self.yolo_worker = YoloWorker(class_thresholds=self.class_thresholds)
        self.yolo_worker.moveToThread(self.thread)
        self.yolo_worker.result_ready.connect(self.handle_results)
        self.thread.start()

        # Set up monitoring timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.safe_check_content)
        self.timer.setInterval(1000)  # Check every second

    def start(self):
        self.active = True
        self.timer.start()
    
    def stop_monitoring(self):
        self.active = False
        self.timer.stop()
        
        # Ensure any ongoing processing completes
        if self.processing_lock.tryLock():
            self.processing_lock.unlock()
        
        # Clean up worker thread
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.yolo_worker.cleanup()
            self.thread.quit()
            self.thread.wait(1000)
            if self.thread.isRunning():
                self.thread.terminate()
        
    def safe_check_content(self):
        if not self.processing_lock.tryLock():
            return
            
        try:
            current_time = time.time()
            if self.skip_frame or (current_time - self.last_detection_time) < self.detection_cooldown:
                self.skip_frame = False
                return
                
            self.check_content()
            self.skip_frame = True
        finally:
            self.processing_lock.unlock()
        
    def check_content(self):
        if not self.active or not self.browser.isVisible():
            return

        # Get viewport information
        viewport_size = self.browser.size()
        scroll_pos = self.browser.page().scrollPosition()
        
        # Capture the visible portion
        visible_pixmap = self.browser.grab()
        
        # Convert to numpy array
        qimg = visible_pixmap.toImage()
        ptr = qimg.bits()
        ptr.setsize(qimg.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape((qimg.height(), qimg.width(), 4))[:,:,:3]
        
        # Submit for detection
        QMetaObject.invokeMethod(
            self.yolo_worker,
            "detect_from_image",
            Qt.QueuedConnection,
            Q_ARG(np.ndarray, cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)),
            Q_ARG(int, viewport_size.width()),
            Q_ARG(int, viewport_size.height()),
            Q_ARG(int, scroll_pos.x()),
            Q_ARG(int, scroll_pos.y())
        )

    def handle_results(self, detections):
        """Process and emit detection results"""
        scroll_pos = self.browser.page().scrollPosition()
        viewport_size = self.browser.size()
        
        viewport_detections = []
        for det in detections:
            try:
                # Convert from absolute to viewport-relative coordinates
                x1 = det['xyxy'][0] - scroll_pos.x()
                y1 = det['xyxy'][1] - scroll_pos.y()
                x2 = det['xyxy'][2] - scroll_pos.x()
                y2 = det['xyxy'][3] - scroll_pos.y()
                
                # Only include visible detections
                if not (x2 < 0 or y2 < 0 or x1 > viewport_size.width() or y1 > viewport_size.height()):
                    viewport_detections.append({
                        'xyxy': [x1, y1, x2, y2],
                        'class': det['class'],
                        'conf': det['conf']
                    })
            except Exception as e:
                print(f"Error processing detection: {str(e)}")
                continue
        
        # Package detection data
        detection_data = {
            'detections': viewport_detections,
            'scroll_x': scroll_pos.x(),
            'scroll_y': scroll_pos.y(),
            'viewport_width': viewport_size.width(),
            'viewport_height': viewport_size.height()
        }
        
        self.last_detection_time = time.time()
        self.detection_signal.emit(detection_data, self.browser.grab())

    def update_threshold(self, class_name, threshold):
        """Update threshold for both monitor and worker"""
        with QMutexLocker(self.processing_lock):
            self.class_thresholds[class_name] = threshold
            QMetaObject.invokeMethod(
                self.yolo_worker,
                "update_threshold",
                Qt.QueuedConnection,
                Q_ARG(str, class_name),
                Q_ARG(float, threshold)
            )