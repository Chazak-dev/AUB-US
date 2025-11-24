"""
Rating Dialog Component for AUBus
Allows users to rate drivers/passengers after ride completion
"""

import math
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QWidget
from PyQt5.QtCore import Qt, pyqtSignal

class StarRatingWidget(QWidget):
    """Custom star rating widget (1-5 stars)"""
    ratingChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rating = 0
        self.hovered_rating = 0
        self.star_size = 40
        self.star_spacing = 10
        self.setMouseTracking(True)
        self.setFixedHeight(self.star_size + 10)
        self.setMinimumWidth((self.star_size + self.star_spacing) * 5)
        
        # Ensure widget can receive focus and mouse events
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        
        display_rating = self.hovered_rating if self.hovered_rating > 0 else self.rating
        
        for i in range(5):
            x = i * (self.star_size + self.star_spacing) + 5
            y = 5
            
            if i < display_rating:
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#FFD700")))  # Gold
            else:
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#CCCCCC")))  # Gray
            
            painter.setPen(QtGui.QPen(QtGui.QColor("#FFA500"), 2))  # Orange border
            
            # Draw star
            self._draw_star(painter, x, y, self.star_size)
    
    def _draw_star(self, painter, x, y, size):
        """Draw a 5-pointed star"""
        points = []
        for i in range(10):
            angle = (i * 36 - 90) * math.pi / 180  # Convert to radians
            if i % 2 == 0:
                # Outer points
                radius = size / 2
            else:
                # Inner points
                radius = size / 4
            
            px = x + size / 2 + radius * math.cos(angle)
            py = y + size / 2 + radius * math.sin(angle)
            points.append(QtCore.QPointF(px, py))
        
        painter.drawPolygon(points)
    
    def mouseMoveEvent(self, event):
        x = event.pos().x()
        star_index = int(x / (self.star_size + self.star_spacing)) + 1
        self.hovered_rating = max(0, min(5, star_index))
        self.update()
        event.accept()
    
    def mousePressEvent(self, event):
        x = event.pos().x()
        star_index = int(x / (self.star_size + self.star_spacing)) + 1
        self.rating = max(1, min(5, star_index))
        self.ratingChanged.emit(self.rating)
        self.update()
        event.accept()
        print(f"⭐ Star clicked! Rating set to: {self.rating}")  # Debug output
    
    def leaveEvent(self, event):
        self.hovered_rating = 0
        self.update()
        event.accept()
    
    def get_rating(self):
        return self.rating


class RatingDialog(QDialog):
    """Dialog for rating driver or passenger after ride completion"""
    
    def __init__(self, request_id, rater_id, target_id, target_role, target_name, parent=None):
        super().__init__(parent)
        
        self.request_id = request_id
        self.rater_id = rater_id
        self.target_id = target_id
        self.target_role = target_role  # "driver" or "passenger"
        self.target_name = target_name
        
        self.rating_value = 0
        self.comment_text = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("Rate Your Ride")
        self.setModal(True)
        # Use Dialog flag instead of WindowStaysOnTopHint which can cause issues
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setMinimumWidth(450)
        self.setMinimumHeight(400)
        
        # Apply stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#skipButton {
                background-color: #9E9E9E;
            }
            QPushButton#skipButton:hover {
                background-color: #757575;
            }
            QTextEdit {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                font-size: 13px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel(f"How was your ride with {self.target_name}?")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel(f"Rate this {self.target_role}")
        subtitle.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(10)
        
        # Star rating widget
        star_container = QWidget()
        star_layout = QHBoxLayout()
        star_layout.setContentsMargins(0, 0, 0, 0)
        
        self.star_widget = StarRatingWidget()
        self.star_widget.ratingChanged.connect(self.on_rating_changed)
        
        star_layout.addStretch()
        star_layout.addWidget(self.star_widget)
        star_layout.addStretch()
        
        star_container.setLayout(star_layout)
        layout.addWidget(star_container)
        
        # Rating label
        self.rating_label = QLabel("Tap a star to rate")
        self.rating_label.setStyleSheet("font-size: 14px; color: #95a5a6;")
        self.rating_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.rating_label)
        
        layout.addSpacing(10)
        
        # Comment section
        comment_label = QLabel("Additional Comments (Optional)")
        comment_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(comment_label)
        
        self.comment_input = QTextEdit()
        self.comment_input.setPlaceholderText(
            f"Share your experience with {self.target_name}...\n"
            f"(e.g., 'Great conversation!', 'Safe driver', 'Very punctual')"
        )
        self.comment_input.setMaximumHeight(100)
        layout.addWidget(self.comment_input)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.skip_button = QPushButton("Skip")
        self.skip_button.setObjectName("skipButton")
        self.skip_button.clicked.connect(self.reject)
        self.skip_button.setFixedWidth(120)
        
        self.submit_button = QPushButton("Submit Rating")
        self.submit_button.clicked.connect(self.submit_rating)
        self.submit_button.setEnabled(False)  # Disabled until rating selected
        self.submit_button.setFixedWidth(150)
        
        button_layout.addStretch()
        button_layout.addWidget(self.skip_button)
        button_layout.addWidget(self.submit_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_rating_changed(self, rating):
        """Handle rating change"""
        self.rating_value = rating
        
        # Update label
        rating_texts = { 
            1: "⭐ Poor",
            2: "⭐⭐ Fair",
            3: "⭐⭐⭐ Good",
            4: "⭐⭐⭐⭐ Very Good",
            5: "⭐⭐⭐⭐⭐ Excellent"
        }
        self.rating_label.setText(rating_texts.get(rating, ""))
        self.rating_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
        
        # Enable submit button
        self.submit_button.setEnabled(True)
    
    def exec_(self):
        """Override exec_ to ensure dialog is shown properly"""
        # Ensure dialog is on top and focused
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        
        # Ensure star widget can receive mouse events
        if hasattr(self, 'star_widget'):
            self.star_widget.setFocus()
        
        return super().exec_()

    def submit_rating(self):
        """Validate and submit rating"""
        if self.rating_value == 0:
            QtWidgets.QMessageBox.warning(
                self,
                "No Rating",
                "Please select a star rating before submitting."
            )
            return
        
        self.comment_text = self.comment_input.toPlainText().strip()
        self.accept()
    
    def get_rating_data(self):
        """Return rating data for submission to server"""
        return {
            'request_id': self.request_id,
            'rater_id': self.rater_id,
            'target_id': self.target_id,
            'target_role': self.target_role,
            'rating': self.rating_value,
            'comment': self.comment_text if self.comment_text else ""
        }