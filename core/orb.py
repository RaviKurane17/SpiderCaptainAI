import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QBrush, QPen

class OrbWindow(QWidget):
    def __init__(self, signal_file=None):
        super().__init__()
        self.signal_file = signal_file

        # Window configuration — truly transparent, always on top, no taskbar entry
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
        
        # Pre-allocate static colors and pens — avoids GC/allocation overhead in paintEvent
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
        
        # 30ms timer (~33 FPS) — uses hardware-accelerated native drawing, very low CPU
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(30)
        
        # State polling timer for IPC
        self.state_file = signal_file
        self.current_state = "HIDE"
        self.state_timer = QTimer(self)
        self.state_timer.timeout.connect(self.check_state)
        self.state_timer.start(100) # Check every 100ms
        
        self.drag_pos = None

    def check_state(self):
        if not self.state_file:
            return
        import os
        if not os.path.exists(self.state_file):
            return
            
        try:
            with open(self.state_file, 'r') as f:
                state = f.read().strip()
                
            if state == "SHOW" and self.current_state != "SHOW":
                self.show()
                self.current_state = "SHOW"
            elif state == "HIDE" and self.current_state != "HIDE":
                self.hide()
                self.current_state = "HIDE"
            elif state == "EXIT":
                QApplication.quit()
        except Exception:
            pass

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
            
            # 2. Draw rotating spider-web lines using save/restore (prevents coordinate drift)
            painter.save()
            painter.translate(center)
            painter.rotate(self.rotation_angle)
            painter.setPen(self.web_pen)
            
            painter.drawEllipse(QPoint(0, 0), 20, 20)
            painter.drawEllipse(QPoint(0, 0), 30, 30)
            for _ in range(8):
                painter.drawLine(0, 15, 0, 40)
                painter.rotate(45.0)
            
            painter.restore()
            
            # 3. Draw solid glowing inner core
            core_radius = 12.0
            core_grad = QRadialGradient(float(cx), float(cy), core_radius)
            core_grad.setColorAt(0.0, self.core_c1)
            core_grad.setColorAt(0.8, self.core_c2)
            core_grad.setColorAt(1.0, self.core_c3)
            
            painter.setBrush(QBrush(core_grad))
            painter.drawEllipse(center, int(core_radius), int(core_radius))
            
        except Exception as e:
            try:
                with open("orb_crash.txt", "w") as f:
                    f.write(str(e))
            except Exception:
                pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def mouseDoubleClickEvent(self, event):
        """Double-click writes 'RESTORE_MAIN' so main window restores."""
        if self.state_file:
            try:
                with open(self.state_file, 'w') as f:
                    f.write('RESTORE_MAIN')
            except Exception:
                pass
        self.hide()
        self.current_state = "HIDE"

if __name__ == '__main__':
    try:
        signal_file = sys.argv[1] if len(sys.argv) > 1 else None
        app = QApplication(sys.argv)
        # Orb launches hidden, waits for 'SHOW' signal
        orb = OrbWindow(signal_file=signal_file)
        sys.exit(app.exec())
    except Exception as e:
        try:
            with open("orb_crash.txt", "w") as f:
                import traceback
                traceback.print_exc(file=f)
        except Exception:
            pass
