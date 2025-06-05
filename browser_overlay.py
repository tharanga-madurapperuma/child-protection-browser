from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QTimer, QEvent, QRectF, QPoint, QDateTime
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QRegion

class BrowserOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.detections = []
        self.stable_detections = []  # Stores confirmed detections
        self.last_update_time = 0
        self.update_cooldown = 100
        self.inactivity_timeout = 2000  # 2 seconds of no mouse events
        self.last_activity_time = QDateTime.currentMSecsSinceEpoch()
        
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Visual settings
        self.fill_color = QColor(0, 0, 0, 240)
        self.border_color = QColor(0, 0, 0, 230)
        self.border_width = 2
        
        # Setup timers
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_position)
        self.update_timer.start(100)
        
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.check_inactivity)
        self.inactivity_timer.start(500)
        
        self.update_position()

    def check_inactivity(self):
        current_time = QDateTime.currentMSecsSinceEpoch()
        if current_time - self.last_activity_time > self.inactivity_timeout:
            self.use_stable_detections()
        else:
            self.use_live_detections()

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
        if not self.parent():
            return
            
        current_time = QDateTime.currentMSecsSinceEpoch()
        if current_time - self.last_update_time < self.update_cooldown:
            return
            
        dpr = self.parent().devicePixelRatioF()
        scroll_pos = self.parent().page().scrollPosition()
        viewport = self.parent().visibleRegion().boundingRect()
        
        if not viewport.isValid():
            viewport = self.parent().rect()
        
        self.setGeometry(0, 0, int(viewport.width() * dpr), int(viewport.height() * dpr))
        self.last_update_time = current_time
        if self.detections:
            self.update()

    def set_detections(self, detection_data):
        """Convert absolute coordinates to viewport-relative coordinates"""
        self.detections = []
        if not detection_data or not detection_data.get('detections'):
            self.update()
            return
        
        # Get current viewport size (fresh reading)
        viewport_w = self.parent().width()
        viewport_h = self.parent().height()
        
        for detection in detection_data['detections']:
            try:
                # Coordinates are already viewport-relative in detection_data
                x1 = max(0, detection['xyxy'][0])
                y1 = max(0, detection['xyxy'][1])
                x2 = min(viewport_w, detection['xyxy'][2])
                y2 = min(viewport_h, detection['xyxy'][3])
                
                # Only keep visible detections
                if (x2 > 0 and y2 > 0 and x1 < viewport_w and y1 < viewport_h):
                    self.detections.append({
                        'xyxy': [x1, y1, x2, y2],
                        'class': detection['class'],
                        'conf': detection['conf']
                    })
            except Exception as e:
                print(f"Coordinate conversion error: {str(e)}")
                continue
                
        self.update()

    def paintEvent(self, event):
        if not self.detections:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Handle high DPI
        dpr = self.devicePixelRatioF()
        painter.scale(1/dpr, 1/dpr)
        
        # Draw detection areas with smoother edges
        path = QPainterPath()
        for detection in self.detections:
            try:
                x1, y1, x2, y2 = [coord * dpr for coord in detection['xyxy']]
                rect = QRectF(x1, y1, x2 - x1, y2 - y1)
                path.addRoundedRect(rect, 4, 4)
                
                # Draw class label
                painter.setPen(QPen(Qt.white, 1))
                painter.drawText(
                    QPoint(x1 + 5, y1 + 15),
                    f"{detection['class']} ({detection['conf']:.2f})"
                )
            except Exception as e:
                print(f"Paint error: {str(e)}")
                continue

        # Fill detection areas
        painter.fillPath(path, self.fill_color)
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawPath(path)

        painter.end()

    def event(self, event):
        """Pass through mouse events"""
        if event.type() in (QEvent.Wheel, QEvent.MouseMove):
            return False
        return super().event(event)

    def cleanup(self):
        """Clean up resources"""
        self.update_timer.stop()
        self.detections.clear()