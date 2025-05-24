from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, QTimer, QEvent, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QRegion

class BrowserOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.detections = []
        
        # Critical settings for proper event handling
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Visual settings
        self.fill_color = QColor(0, 0, 0, 240)  # Semi-transparent black
        self.border_width = 2
        
        # Setup update timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_position)
        self.update_timer.start(100)
        
        # Debug visualization
        self.debug_mode = False  # Set to True to see coordinate debugging

    def update_position(self):
        """Force immediate repositioning on scroll"""
        if not self.parent():
            return
            
        # Get fresh scroll position
        scroll_pos = self.parent().page().scrollPosition()
        viewport = self.parent().visibleRegion().boundingRect()
        
        if not viewport.isValid():
            viewport = self.parent().rect()
        
        # Immediate repositioning with proper viewport size
        self.setGeometry(
            0,  # Fixed at 0,0 relative to browser
            0,
            viewport.width(),
            viewport.height()
        )
        
        # Force redraw with current detections
        if self.detections:
            self.update_mask()
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
                x1 = detection['xyxy'][0]
                y1 = detection['xyxy'][1]
                x2 = detection['xyxy'][2]
                y2 = detection['xyxy'][3]
                
                # Only keep visible detections
                if (x2 > 0 and y2 > 0 and x1 < viewport_w and y1 < viewport_h):
                    self.detections.append({
                        'xyxy': [
                            max(0, x1),
                            max(0, y1),
                            min(viewport_w, x2),
                            min(viewport_h, y2)
                        ],
                        'class': detection['class'],
                        'conf': detection['conf']
                    })
            except Exception as e:
                print(f"Coordinate conversion error: {e}")
                continue
                
        self.update_mask()
        self.update()

    def update_mask(self):
        """Create visible region mask"""
        if not self.detections:
            self.clearMask()
            return
            
        combined_region = QRegion()
        
        for detection in self.detections:
            try:
                x1, y1, x2, y2 = map(int, detection['xyxy'])
                rect = QRect(x1, y1, x2-x1, y2-y1)
                if rect.isValid():
                    combined_region = combined_region.united(QRegion(rect))
            except Exception as e:
                print(f"Mask creation error: {e}")
                continue
                
        self.setMask(combined_region)

    def paintEvent(self, event):
        if not self.detections:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Get scroll offset
        scroll_pos = self.parent().page().scrollPosition()
        scroll_x = scroll_pos.x()
        scroll_y = scroll_pos.y()

        # Draw detection areas
        path = QPainterPath()
        for detection in self.detections:
            try:
                x1, y1, x2, y2 = detection['xyxy']
                # Adjust for scroll position
                x1 -= scroll_x
                y1 -= scroll_y
                x2 -= scroll_x
                y2 -= scroll_y

                rect = QRectF(x1, y1, x2 - x1, y2 - y1)
                path.addRect(rect)

                # Debug info - coordinates
                painter.setPen(QPen(Qt.red, 1))
                painter.drawText(
                    QPoint(x1 + 5, y1 + 15),
                    f"{detection['class']} @{x1},{y1}"
                )
            except:
                continue

        painter.fillPath(path, self.fill_color)

        # Optional: draw viewport border
        painter.setPen(QPen(Qt.green, 2, Qt.DashLine))
        painter.drawRect(self.rect())

        # Optional: scroll offset info
        painter.setPen(QPen(Qt.white))
        painter.drawText(
            QPoint(10, 20),
            f"Scroll: {scroll_x},{scroll_y}"
        )

        painter.end()


    def event(self, event):
        """Pass through mouse events"""
        if event.type() in (QEvent.Wheel, QEvent.MouseMove):
            return False
        return super().event(event)