#!/usr/bin/env python3

import math
import sys

import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMainWindow,
                             QProgressBar, QPushButton, QVBoxLayout, QWidget)
from pyqtgraph import PlotWidget


class GCS(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Gemstone Example Control Station")
        self.setGeometry(100, 100, 800, 480)  # 9-inch screen resolution

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.init_ui()

        # Timer for updating data
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)  # Update every 100ms

        # Initialize telemetry data
        self.time = 0
        self.altitude_data = []
        self.speed_data = []
        self.battery_data = []

    def init_ui(self):
        # Title Label
        self.title_label = QLabel("T3 Foundation Gemstone Project")
        self.title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #00CED1;")  # Turkuaz renk
        self.layout.addWidget(self.title_label)

        # Data Layout
        self.data_layout = QHBoxLayout()

        # Altitude Gauge
        self.altitude_gauge = self.create_gauge("Altitude (m)", 0, 1000, "#00CED1")
        self.data_layout.addWidget(self.altitude_gauge)

        # Speed Gauge
        self.speed_gauge = self.create_gauge("Speed (m/s)", 0, 100, "#FF4500")  # Kırmızımsı turuncu
        self.data_layout.addWidget(self.speed_gauge)

        # Battery Gauge
        self.battery_gauge = self.create_gauge("Battery (%)", 0, 100, "#00CED1")
        self.data_layout.addWidget(self.battery_gauge)

        self.layout.addLayout(self.data_layout)

        # Graph Widget
        self.graph_widget = PlotWidget()
        self.graph_widget.setBackground("#000000")
        self.graph_widget.setTitle("UAV Telemetry Data", color="#00CED1", size="20pt")
        self.graph_widget.setLabel("left", "Value", color="#00CED1")
        self.graph_widget.setLabel("bottom", "Time (s)", color="#00CED1")
        self.graph_widget.showGrid(x=True, y=True)
        self.graph_widget.setYRange(0, 100)
        self.layout.addWidget(self.graph_widget)

        # Control Buttons
        self.control_layout = QHBoxLayout()

        self.takeoff_button = QPushButton("Takeoff")
        self.takeoff_button.setFont(QFont("Arial", 16))
        self.takeoff_button.setStyleSheet("background-color: #00CED1; color: #000000;")
        self.control_layout.addWidget(self.takeoff_button)

        self.land_button = QPushButton("Land")
        self.land_button.setFont(QFont("Arial", 16))
        self.land_button.setStyleSheet("background-color: #FF4500; color: #000000;")
        self.control_layout.addWidget(self.land_button)

        self.layout.addLayout(self.control_layout)

    def create_gauge(self, title, min_value, max_value, color):
        gauge_widget = QWidget()
        gauge_layout = QVBoxLayout(gauge_widget)

        # Title Label
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {color};")
        gauge_layout.addWidget(title_label)

        # Progress Bar as Gauge
        gauge = QProgressBar()
        gauge.setMinimum(min_value)
        gauge.setMaximum(max_value)
        gauge.setValue(0)
        gauge.setFormat("%v")
        gauge.setStyleSheet(
            f"""
            QProgressBar {{
                border: 2px solid {color};
                border-radius: 5px;
                text-align: center;
                color: {color};
                background-color: #000000;
            }}
            QProgressBar::chunk {{
                background-color: {color};
            }}
        """
        )
        gauge_layout.addWidget(gauge)

        return gauge_widget

    def update_data(self):
        # Simulate sinusoidal telemetry data
        self.time += 0.1
        altitude = 500 + 500 * math.sin(self.time)  # Sinusoidal altitude
        speed = 50 + 50 * math.sin(self.time * 0.5)  # Sinusoidal speed
        battery = 50 + 50 * math.sin(self.time * 0.2)  # Sinusoidal battery

        # Update gauges
        self.altitude_gauge.findChild(QProgressBar).setValue(int(altitude))
        self.speed_gauge.findChild(QProgressBar).setValue(int(speed))
        self.battery_gauge.findChild(QProgressBar).setValue(int(battery))

        # Update telemetry data for the graph
        self.altitude_data.append(altitude)
        self.speed_data.append(speed)
        self.battery_data.append(battery)

        # Keep only the last 100 data points
        if len(self.altitude_data) > 100:
            self.altitude_data.pop(0)
            self.speed_data.pop(0)
            self.battery_data.pop(0)

        # Plot the data
        self.graph_widget.clear()
        self.graph_widget.plot(self.altitude_data, pen=pg.mkPen(color="#00CED1", width=2), name="Altitude")
        self.graph_widget.plot(self.speed_data, pen=pg.mkPen(color="#FF4500", width=2), name="Speed")
        self.graph_widget.plot(self.battery_data, pen=pg.mkPen(color="#00FF00", width=2), name="Battery")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set color palette
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, QColor(0, 0, 0))
    palette.setColor(palette.ColorRole.WindowText, QColor(0, 206, 209))  # Turkuaz
    palette.setColor(palette.ColorRole.Base, QColor(0, 0, 0))
    palette.setColor(palette.ColorRole.AlternateBase, QColor(0, 0, 0))
    palette.setColor(palette.ColorRole.ToolTipBase, QColor(0, 206, 209))
    palette.setColor(palette.ColorRole.ToolTipText, QColor(0, 206, 209))
    palette.setColor(palette.ColorRole.Text, QColor(0, 206, 209))
    palette.setColor(palette.ColorRole.Button, QColor(0, 0, 0))
    palette.setColor(palette.ColorRole.ButtonText, QColor(0, 206, 209))
    palette.setColor(palette.ColorRole.BrightText, QColor(255, 69, 0))  # Kırmızımsı turuncu
    palette.setColor(palette.ColorRole.Highlight, QColor(0, 206, 209))
    palette.setColor(palette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)

    window = GCS()
    window.show()
    sys.exit(app.exec())
