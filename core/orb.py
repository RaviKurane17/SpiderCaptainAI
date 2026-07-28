import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QBrush, QPen

class OrbWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Window configuration
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(120, 120)
        
        # Center on primary screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2
        )
        
        # Pre-allocate static colors and pens to avoid GC/memory allocation overhead in paintEvent
        self.aura_c1 = QColor(0, 255, 255, 200)
        self.aura_c2 = QColor(0, 85, 255, 120)
        self.aura_c3 = QColor(0, 0, 0, 0)
        
        self.core_c1 = QColor(255, 255, 255, 255)
        self.core_c2 = QColor(200, 255, 255, 255)
        self.core_c3 = QColor(0, 255, 255, 100)
        
        self.web_pen = QPen(QColor(255, 255, 255, 80), 1)
        
        # Animation parameters
        self.pulse_radius = 45.0
        self.pulse_direction = 0.5
        self.rotation_angle = 0.0
        
        # 30ms timer (~33 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)
        
        self.drag_pos = None

    def update_animation(self):
        self.pulse_radius += self.pulse_direction
        if self.pulse_radius >= 55.0:
            self.pulse_direction = -0.5
        elif self.pulse_radius <= 40.0:
            self.pulse_direction = 0.5
            
        self.rotation_angle = (self.rotation_angle + 2.0) % 360.0
        self.update()

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            cx, cy = self.width() // 2, self.height() // 2
            center = QPoint(cx, cy)
            
            # 1. Draw outer glowing aura
            gradient = QRadialGradient(float(cx), float(cy), self.pulse_radius)
            gradient.setColorAt(0.0, self.aura_c1)
            gradient.setColorAt(0.5, self.aura_c2)
            gradient.setColorAt(1.0, self.aura_c3)
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, int(self.pulse_radius), int(self.pulse_radius))
            
            # 2. Draw rotating tech/spider web lines using save/restore context
            painter.save()
            painter.translate(center)
            painter.rotate(self.rotation_angle)
            painter.setPen(self.web_pen)
            
            painter.drawEllipse(QPoint(0, 0), 20, 20)
            painter.drawEllipse(QPoint(0, 0), 30, 30)
            for _ in range(8):
                painter.drawLine(0, 15, 0, 40)
                painter.rotate(45.0)
            
            painter.restore()  # Cleanly resets coordinate system back to normal
            
            # 3. Draw solid glowing inner core
            core_radius = 12.0
            core_grad = QRadialGradient(float(cx), float(cy), core_radius)
            core_grad.setColorAt(0.0, self.core_c1)
            core_grad.setColorAt(0.8, self.core_c2)
            core_grad.setColorAt(1.0, self.core_c3)
            
            painter.setBrush(QBrush(core_grad))
            painter.drawEllipse(center, int(core_radius), int(core_radius))
            
        except Exception as e:
            with open("orb_crash.txt", "w") as f:
                f.write(str(e))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def mouseDoubleClickEvent(self, event):
        print("RESTORE", flush=True)
        self.close()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        orb = OrbWindow()
        orb.show()
        sys.exit(app.exec())
    except Exception as e:
        with open("orb_crash.txt", "w") as f:
            import traceback
            traceback.print_exc(file=f)
