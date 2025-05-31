import sys
import os
import time
from PyQt5 import QtWidgets, QtGui, QtCore
from PIL import ImageGrab, Image, ImageOps

# Write to log file
def log_message(message):
    with open("ocr_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")

class SnippingWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        
        # Close screen and make it transparent
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowState(QtCore.Qt.WindowFullScreen)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Get screen size
        self.screen_geometry = QtWidgets.QDesktopWidget().screenGeometry()
        self.screen_width = self.screen_geometry.width()
        self.screen_height = self.screen_geometry.height()
        
        # Take screenshot and set as background
        self.background = self.grabScreenshot()
        
        # Mouse positions
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()
        self.is_selecting = False
        
        # Change mouse cursor
        self.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        
        # Instruction text
        self.instruction_label = QtWidgets.QLabel("Select an area for OCR", self)
        self.instruction_label.setStyleSheet("""
            color: white; 
            background-color: rgba(0, 0, 0, 180);
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 14px;
        """)
        self.instruction_label.setAlignment(QtCore.Qt.AlignCenter)
        self.instruction_label.setGeometry(
            (self.screen_width - 400) // 2,
            20,
            400,
            40
        )
        
        # Cancel button
        self.cancel_button = QtWidgets.QPushButton("Cancel (ESC)", self)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_capture)
        self.cancel_button.setGeometry(
            self.screen_width - 120,
            self.screen_height - 60,
            100,
            40
        )
        
        # Pixel grid for magnifier
        self.magnifier_size = 120
        self.magnifier_offset = 20
        self.magnifier_zoom = 2
        self.magnifier_visible = False
        
        # Screen capture variables
        self.min_size = 30  # Min 30x30 px
        
        log_message("SnippingWidget initialized")
        self.show()
    
    def grabScreenshot(self):
        # Take full screen screenshot
        try:
            screen = QtWidgets.QApplication.primaryScreen()
            screenshot = screen.grabWindow(0)
            return screenshot
        except Exception as e:
            log_message(f"Error grabbing screenshot: {e}")
            return None
    
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        
        # Draw darkened screen background
        if self.background:
            painter.setOpacity(0.4)  # 60% darkening
            painter.drawPixmap(0, 0, self.background)
            painter.setOpacity(1.0)
        else:
            # Use semi-transparent black if no background
            painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 128))
        
        # If selection area exists
        if not self.begin.isNull() and not self.end.isNull():
            # Calculate selection rectangle
            rect = QtCore.QRect(self.begin, self.end).normalized()
            
            # Apply mask to selection area - selected area transparent, rest darkened
            maskedArea = QtGui.QRegion(self.rect())
            maskedArea = maskedArea.subtracted(QtGui.QRegion(rect))
            painter.setClipRegion(maskedArea)
            painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 160))
            painter.setClipRect(self.rect())
            
            # Draw selected area borders
            pen = QtGui.QPen(QtGui.QColor(46, 125, 246), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            
            # Show size information
            width = abs(self.begin.x() - self.end.x())
            height = abs(self.begin.y() - self.end.y())
            size_text = f"{width} × {height} px"
            
            text_rect = QtCore.QRect(
                min(self.begin.x(), self.end.x()),
                max(self.begin.y(), self.end.y()) + 5,
                150,
                20
            )
            
            # Text background
            painter.fillRect(text_rect, QtGui.QColor(0, 0, 0, 180))
            painter.setPen(QtGui.QColor(255, 255, 255))
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, size_text)
        
        # Draw magnifier
        if self.magnifier_visible and not self.begin.isNull():
            self.drawMagnifier(painter)
    
    def drawMagnifier(self, painter):
        # Determine magnifier position based on mouse position
        cursor_pos = self.mapFromGlobal(QtGui.QCursor.pos())
        mag_x = cursor_pos.x() + self.magnifier_offset
        mag_y = cursor_pos.y() - self.magnifier_size - self.magnifier_offset
        
        # Prevent crossing screen boundaries
        if mag_x + self.magnifier_size > self.screen_width:
            mag_x = cursor_pos.x() - self.magnifier_size - self.magnifier_offset
        
        if mag_y < 0:
            mag_y = cursor_pos.y() + self.magnifier_offset
        
        # Draw magnifier frame
        painter.setPen(QtGui.QColor(255, 255, 255))
        painter.setBrush(QtGui.QColor(0, 0, 0, 0))  # Transparent background
        painter.drawRect(mag_x, mag_y, self.magnifier_size, self.magnifier_size)
        
        # Fill magnifier
        if self.background:
            # Cut and enlarge the area around the mouse
            grab_size = self.magnifier_size // self.magnifier_zoom
            grab_x = cursor_pos.x() - grab_size // 2
            grab_y = cursor_pos.y() - grab_size // 2
            
            source_rect = QtCore.QRect(grab_x, grab_y, grab_size, grab_size)
            target_rect = QtCore.QRect(mag_x, mag_y, self.magnifier_size, self.magnifier_size)
            
            if grab_x >= 0 and grab_y >= 0:
                painter.drawPixmap(target_rect, self.background, source_rect)
        
        # Crosshair (show plus-shaped cursor)
        painter.setPen(QtGui.QColor(255, 0, 0))
        center_x = mag_x + self.magnifier_size // 2
        center_y = mag_y + self.magnifier_size // 2
        painter.drawLine(center_x - 5, center_y, center_x + 5, center_y)
        painter.drawLine(center_x, center_y - 5, center_x, center_y + 5)
    
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.begin = event.pos()
            self.end = event.pos()
            self.is_selecting = True
            self.magnifier_visible = True
            self.update()
    
    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.is_selecting:
            self.end = event.pos()
            self.is_selecting = False
            self.magnifier_visible = False
            self.capture_selection()
    
    def capture_selection(self):
        # Get selected coordinates
        x1 = min(self.begin.x(), self.end.x())
        y1 = min(self.begin.y(), self.end.y())
        x2 = max(self.begin.x(), self.end.x())
        y2 = max(self.begin.y(), self.end.y())
        
        log_message(f"Selected area: ({x1}, {y1}) to ({x2}, {y2})")
        
        # Check for very small area
        if x2 - x1 < self.min_size or y2 - y1 < self.min_size:
            log_message(f"Warning: Selected area is too small ({x2-x1}x{y2-y1})")
            
            # Expand to minimum size
            if x2 - x1 < self.min_size:
                center_x = (x1 + x2) // 2
                half_min = self.min_size // 2
                x1 = max(0, center_x - half_min)
                x2 = min(self.screen_width, center_x + half_min)
            
            if y2 - y1 < self.min_size:
                center_y = (y1 + y2) // 2
                half_min = self.min_size // 2
                y1 = max(0, center_y - half_min)
                y2 = min(self.screen_height, center_y + half_min)
            
            log_message(f"Expanded area to: ({x1}, {y1}) to ({x2}, {y2})")
        
        # Close interface
        self.hide()
        QtWidgets.QApplication.processEvents()  # Ensure GUI is closed
        
        # Take screenshot
        try:
            time.sleep(0.1)  # Short wait for interface to fully close
            
            # Match full screen size with crop position
            bbox = (x1, y1, x2, y2)
            img = ImageGrab.grab(bbox)
            
            # Enhance image
            try:
                img = ImageOps.autocontrast(img, cutoff=0.5)
            except Exception as e:
                log_message(f"Warning: Could not enhance image: {e}")
            
            # Create captures directory (if it doesn't exist)
            captures_dir = "captures"
            if not os.path.exists(captures_dir):
                os.makedirs(captures_dir)
                log_message(f"Created captures directory: {captures_dir}")
            
            # Create timestamped filename
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.png"
            save_path = os.path.join(captures_dir, filename)
            
            # Get full path
            full_path = os.path.abspath(save_path)
            
            # Save image to the captures folder
            img.save(full_path, quality=100)
            
            # Save a copy named "capture.png" in the captures folder for OCR
            capture_path = os.path.join(captures_dir, "capture.png")
            img.save(capture_path, quality=100)
            
            log_message(f"Image saved to: {full_path}")
            log_message(f"OCR copy saved to: {capture_path}")
            log_message(f"Image size: {img.size}, Mode: {img.mode}")
            
            # Image check
            is_blank = is_blank_image(img)
            
            # Close application
            self.accept_capture()
            
        except Exception as e:
            log_message(f"Error capturing screenshot: {str(e)}")
            self.reject_capture("Could not capture screenshot")
    
    def keyPressEvent(self, event):
        # Cancel with ESC key
        if event.key() == QtCore.Qt.Key_Escape:
            self.cancel_capture()
            event.accept()  # Accept key press
            return
        super().keyPressEvent(event)  # Pass other keys to parent class
    
    def accept_capture(self):
        log_message("Capture accepted")
        QtWidgets.QApplication.quit()
    
    def reject_capture(self, reason="Operation cancelled"):
        log_message(f"Capture rejected: {reason}")
        # Create cancel flag
        with open("capture_cancelled.tmp", "w") as f:
            f.write(reason)
        QtWidgets.QApplication.quit()
    
    def cancel_capture(self):
        self.reject_capture("Cancelled by user")

def is_blank_image(img):
    """Check if image is mostly blank (completely black or white)"""
    try:
        # Convert to grayscale
        if img.mode != 'L':
            img_gray = img.convert('L')
        else:
            img_gray = img
            
        # Get histogram
        hist = img_gray.histogram()
        
        # Check ratio of black or white pixels
        total_pixels = img.width * img.height
        black_pixels = hist[0]
        white_pixels = hist[255]
        
        black_ratio = black_pixels / total_pixels
        white_ratio = white_pixels / total_pixels
        
        log_message(f"Black pixel ratio: {black_ratio:.2f}, White pixel ratio: {white_ratio:.2f}")
        
        if black_ratio > 0.95 or white_ratio > 0.95:
            log_message("Warning: Captured image appears to be blank")
            return True
            
        return False
    except Exception as e:
        log_message(f"Error checking blank image: {str(e)}")
        return False

def snip_area():
    try:
        # Clear previously created cancel flag
        if os.path.exists("capture_cancelled.tmp"):
            os.remove("capture_cancelled.tmp")
        
        # Start application
        app = QtWidgets.QApplication(sys.argv)
        snip = SnippingWidget()
        app.exec_()
        
        # Check cancel flag
        if os.path.exists("capture_cancelled.tmp"):
            log_message("Capture was cancelled by user")
            with open("capture_cancelled.tmp", "r") as f:
                reason = f.read()
            os.remove("capture_cancelled.tmp")
            return False, reason
        
        # Check captured image
        capture_path = os.path.join("captures", "capture.png")
        if not os.path.exists(capture_path):
            log_message(f"Error: {capture_path} does not exist after capture")
            return False, "Image file could not be created"
        
        return True, ""
    except Exception as e:
        error_msg = str(e)
        log_message(f"Error in snip_area: {error_msg}")
        return False, f"Error: {error_msg}"

if __name__ == '__main__':
    # Initialize log file
    if not os.path.exists("ocr_log.txt"):
        open("ocr_log.txt", "w").close()
    
    log_message("\n--- New Capture Session ---")
    log_message(f"Starting snipper.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Wait for initial windows to close (1 second)
    # This ensures that the user sees the screen when pressing Ctrl+Alt+T shortcut
    time.sleep(0.5)
    
    success, message = snip_area()
    
    # Return success status
    if success:
        sys.exit(0)
    else:
        print(message)  # Print error to console
        sys.exit(1)
