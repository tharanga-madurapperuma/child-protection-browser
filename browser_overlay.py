import time
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QTimer, QEvent, QRectF, QPoint, QDateTime
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QRegion
from PyQt5.QtWebEngineWidgets import QWebEnginePage

class BrowserOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.detections = []  # Stores all active detections
        self.last_activity_time = time.time()
        self.inactivity_threshold = 2.0  # 2 seconds
        
        # Video mode settings
        self.video_mode = False
        self.video_refresh_timer = QTimer(self)
        self.video_refresh_timer.timeout.connect(self.clear_video_detections)
        self.video_refresh_timer.start(100)  # 10fps
        
        # Initialize scroll position tracking
        self.last_scroll_position = QPoint(0, 0)
        self.scroll_threshold = 10  # pixels
        
        # Detection matching thresholds
        self.position_threshold = 30  # pixels
        self.size_threshold = 0.3  # 30% size difference
        
        # Visual settings
        self.fill_color = QColor(0, 0, 0, 250)  # Semi-transparent red
        self.border_color = QColor(0, 0, 0, 250)
        
        # Setup timers
        self.activity_timer = QTimer(self)
        self.activity_timer.timeout.connect(self.check_activity)
        self.activity_timer.start(200)
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_position)
        self.update_timer.start(100)
        
        self.update_position()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.video_detection_expiry = {}  # Track when video detections should expire
        self.video_box_duration = 1.0  # Keep boxes for 1 second in video mode

    def clear_video_detections(self):
        """Clear expired detections in video mode"""
        if not self.video_mode:
            return
            
        current_time = time.time()
        expired_detections = []
        
        # Check which detections have expired
        for i, detection in enumerate(self.detections):
            if detection.get('detection_time', 0) + self.video_box_duration < current_time:
                expired_detections.append(i)
        
        # Remove expired detections in reverse order
        for i in sorted(expired_detections, reverse=True):
            if i < len(self.detections):
                self.detections.pop(i)
        
        if expired_detections:
            self.update()

    def is_same_detection(self, det1, det2):
        """Check if two detections are the same object with tolerance"""
        if det1['class'] != det2['class']:
            return False
            
        x1, y1, x2, y2 = det1['xyxy']
        x1_new, y1_new, x2_new, y2_new = det2['xyxy']
        
        # Center point comparison
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        cx_new = (x1_new + x2_new) / 2
        cy_new = (y1_new + y2_new) / 2
        
        # Position check
        distance = ((cx_new - cx)**2 + (cy_new - cy)**2)**0.5
        if distance > self.position_threshold:
            return False
            
        # Size check
        area = (x2 - x1) * (y2 - y1)
        area_new = (x2_new - x1_new) * (y2_new - y1_new)
        size_diff = abs(area_new - area) / max(area, area_new)
        if size_diff > self.size_threshold:
            return False
            
        return True

    def check_activity(self):
        """Clear detections on user activity"""
        if self.video_mode:
            return  # Don't clear on activity for video sites
            
        current_time = time.time()
        if current_time - self.last_activity_time < self.inactivity_threshold:
            if self.detections:
                self.detections = []
                self.hide()
                self.update()
                # Force content re-check
                if hasattr(self.parent(), 'page'):
                    self.parent().page().triggerAction(QWebEnginePage.Reload)

    def use_stable_detections(self):
        """Use the most consistent detections during inactivity"""
        if self.stable_detections and not self.detections:
            self.detections = self.stable_detections.copy()
            self.update()

    def use_live_detections(self):
        """Use real-time detections when active"""
        if self.detections:
            self.stable_detections = self.detections.copy()

    def update_position(self):
        """Standard position update with scroll detection"""
        if not self.parent():
            return
            
        dpr = self.parent().devicePixelRatioF()
        viewport = self.parent().visibleRegion().boundingRect()
        
        if not viewport.isValid():
            viewport = self.parent().rect()
        
        # Get current scroll position
        current_scroll = self.parent().page().scrollPosition()
        
        # Clear detections if scroll position changed significantly
        if (abs(current_scroll.x() - self.last_scroll_position.x()) > self.scroll_threshold or 
            abs(current_scroll.y() - self.last_scroll_position.y()) > self.scroll_threshold):
            self.detections = []
            self.update()
        
        self.last_scroll_position = current_scroll
        self.setGeometry(0, 0, int(viewport.width() * dpr), int(viewport.height() * dpr))
        self.update()

    def set_detections(self, detection_data):
        """Update detections while preserving previous ones (without aging)"""
        if not detection_data or not detection_data.get('detections'):
            self.update()
            return
        
        try:
            viewport_w = self.parent().width()
            viewport_h = self.parent().height()
            new_detections = []
            
            # Process new detections
            for detection in detection_data['detections']:
                try:
                    x1 = max(0, min(viewport_w, detection['xyxy'][0]))
                    y1 = max(0, min(viewport_h, detection['xyxy'][1]))
                    x2 = max(0, min(viewport_w, detection['xyxy'][2]))
                    y2 = max(0, min(viewport_h, detection['xyxy'][3]))
                    
                    if x2 > x1 and y2 > y1:
                        new_detections.append({
                            'xyxy': [x1, y1, x2, y2],
                            'class': detection['class'],
                            'conf': detection['conf']
                        })
                except Exception as e:
                    print(f"Invalid detection coordinates: {str(e)}")
            
            # For video mode, always use new detections only
            if self.video_mode:
                # For video mode, add timestamp to new detections
                current_time = time.time()
                for det in new_detections:
                    det['detection_time'] = current_time
                self.detections = new_detections
            else:
                # Combine new and existing detections
                combined = []
                matched_indices = set()
                
                # First match existing detections
                for existing in self.detections:
                    matched = False
                    for i, new_det in enumerate(new_detections):
                        if i not in matched_indices and self.is_same_detection(existing, new_det):
                            # Update position/confidence
                            combined.append({
                                'xyxy': new_det['xyxy'],
                                'class': new_det['class'],
                                'conf': max(existing['conf'], new_det['conf'])
                            })
                            matched_indices.add(i)
                            matched = True
                            break
                    
                    if not matched:
                        combined.append(existing)  # Keep existing detection
                
                # Add remaining new detections
                for i, new_det in enumerate(new_detections):
                    if i not in matched_indices:
                        combined.append(new_det)
                
                self.detections = combined
            
            self.update_position()
            self.show()
            self.update()
        except Exception as e:
            print(f"Overlay update failed: {str(e)}")
            self.hide()

    def age_detections(self):
        """Increment age of all detections and remove old ones"""
        self.all_detections = [
            d for d in self.all_detections 
            if d['age'] < self.max_age
        ]
        for d in self.all_detections:
            d['age'] += 1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        for detection in self.detections:
            self.draw_detection(painter, detection)
        
        painter.end()

    def draw_detection(self, painter, detection):
        """Draw a detection box"""
        try:
            x1, y1, x2, y2 = detection['xyxy']
            rect = QRectF(x1, y1, x2-x1, y2-y1)
            
            path = QPainterPath()
            path.addRoundedRect(rect, 4, 4)
            
            painter.fillPath(path, self.fill_color)
            painter.setPen(QPen(self.border_color, 2))
            painter.drawPath(path)
            
            painter.setPen(QPen(Qt.white, 1))
            # painter.drawText(QPoint(x1 + 5, y1 + 15), f"{detection['class']} ({detection['conf']:.2f})")
        except Exception as e:
            print(f"Drawing error: {str(e)}")

    def event(self, event):
        """Track user activity"""
        if event.type() in (QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.Wheel):
            self.last_activity_time = time.time()
            if self.detections:
                self.clear_detections()
        return super().event(event)

    def cleanup(self):
        self.update_timer.stop()
        self.video_refresh_timer.stop()
        self.detections.clear()

    def clear_detections(self):
        """Clear all current detections"""
        self.detections = []
        self.update()