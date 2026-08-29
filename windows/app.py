from __future__ import annotations
import os, sys, tempfile
from pathlib import Path

import cv2
import numpy as np
import re
from cv2_enumerate_cameras import enumerate_cameras
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QMessageBox, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QStackedWidget,
    QProgressBar, QSizePolicy, QLineEdit, QComboBox, QSlider
)

from protocol import encode_file, TransferAssembler, ProtocolError, sha256_hex
from qr_codec import make_qr

MAX_FILE_SIZE = 5 * 1024 * 1024
CHUNK_SIZE = 100

def resource_path(filename):
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

AMBER = "#F7931A"
AMBER2 = "#D97900"
BG = "#0b0b0b"
PANEL = "#131313"
PANEL2 = "#181818"
BORDER = "#2b2b2b"
TEXT = "#f2f2f2"
MUTED = "#9f9f9f"
GOOD = "#5ee06d"
BAD = "#ff5d5d"

STYLE = f"""
QMainWindow, QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "Segoe UI";
}}
QFrame#panel {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 18px;
}}
QFrame#softPanel {{
    background: {PANEL2};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QPushButton {{
    background: {PANEL2};
    color: {TEXT};
    border: 1px solid #343434;
    border-radius: 14px;
    padding: 14px 18px;
    font-size: 16px;
    font-weight: 600;
}}

QPushButton#linkButton {{
    background: transparent;
    color: {MUTED};
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 14px;
    font-weight: 600;
}}

QPushButton#linkButton:hover {{
    color: {AMBER};
    border: 1px solid {AMBER};
}}
QPushButton:hover {{ border: 1px solid {AMBER2}; }}
QPushButton#primary {{
    background: #2a1602;
    border: 1px solid {AMBER};
    color: {AMBER};
}}
QPushButton#primary:hover {{ background: #361e04; }}
QPushButton#nav {{
    font-size: 28px;
    min-width: 58px;
    min-height: 58px;
    border-radius: 29px;
    color: {AMBER};
}}
QLabel#title {{ font-size: 26px; font-weight: 700; }}
QLabel#accentTitle {{ color: {AMBER}; font-size: 22px; font-weight: 700; }}
QLabel#section {{ color: {AMBER}; font-size: 18px; font-weight: 700; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#bigStatus {{ color: {AMBER}; font-size: 19px; font-weight: 700; }}
QLabel#good {{ color: {GOOD}; font-weight: 700; }}
QLabel#bad {{ color: {BAD}; font-weight: 700; }}
QProgressBar {{
    border: 1px solid #333;
    border-radius: 6px;
    background: #111;
    height: 12px;
}}
QProgressBar::chunk {{
    background: {AMBER};
    border-radius: 5px;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: #2b2b2b;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {AMBER};
    border-radius: 3px;
}}

QSlider::add-page:horizontal {{
    background: #2b2b2b;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: {AMBER};
    border: 2px solid {AMBER2};
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}}

QSlider::handle:horizontal:hover {{
    background: #ffab3d;
}}

QLineEdit#recoveryInput {{
    background: {PANEL2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 15px;
}}

QLineEdit#recoveryInput:focus {{
    border: 1px solid {AMBER};
    background: #1d1d1d;
}}

QLineEdit#hashField {{
    background: {PANEL2};
    color: {TEXT};
    border: 1px solid {AMBER};
    border-radius: 8px;
    padding: 7px 10px;
}}

QLineEdit#hashField:focus {{
    border: 1px solid #ffab3d;
}}
"""

def fmt_size(n):
    if n < 1024: return f"{n} B"
    if n < 1024*1024: return f"{n/1024:.2f} KB"
    return f"{n/(1024*1024):.2f} MB"

class Card(QFrame):
    def __init__(self, soft=False):
        super().__init__()
        self.setObjectName("softPanel" if soft else "panel")

class AirGapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AirGapQR v0.5.0")
        self.setWindowIcon(QIcon(resource_path("AirGapQR.ico")))
        self.resize(1500, 920)
        self.setMinimumSize(1200, 760)

        self.frames = []
        self.frame_index = 0
        self.selected_frame_indices = []
        self.selected_frame_pos = 0
        self.recovery_mode = False
        self.assembler = TransferAssembler()
        self.received_data = None
        self.cap = None
        self.camera_index = 0
        self.camera_zoom = 1.0
        self.frame_display_time = 2000
        self.qr_background_brightness = 255
        self.detector = cv2.QRCodeDetector()
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self._camera_tick)
        self.frame_timer = QTimer(self)
        self.frame_timer.timeout.connect(self._advance_frame)
        self.last_camera_text = ""

        self.settings_return_page = None
        self.settings_frame_timer_was_active = False
        self.settings_camera_was_active = False

        self._build()
        self._show_home()

    def lbl(self, text="", obj=None, wordwrap=False):
        x = QLabel(text)
        if obj: x.setObjectName(obj)
        x.setWordWrap(wordwrap)
        return x

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(18, 14, 18, 14)
        main.setSpacing(12)

        # topbar
        top = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(
            QPixmap(resource_path("AirGapQR_icon.png")).scaled(
                 56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation
             )
        )
        logo.setFixedSize(56, 56)

        brand = self.lbl("AirGapQR v0.5.0", "title")

        top.addWidget(logo)
        top.addWidget(brand)
        top.addStretch()
        self.top_status = self.lbl("●  READY", "bigStatus")
        top.addWidget(self.top_status)
        main.addLayout(top)

        content = QHBoxLayout()
        content.setSpacing(14)
        main.addLayout(content, 1)

        # sidebar
        side = Card()
        side.setMinimumWidth(220)
        side.setMaximumWidth(330)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(20, 22, 20, 22)
        sv.setSpacing(16)

        subtitle = self.lbl("OFFLINE FILE TRANSFER", "muted")
        sv.addWidget(subtitle)
        sv.addSpacing(18)

        self.send_btn = QPushButton("↑   FILE → QR\n     Convert file to QR")
        self.send_btn.setObjectName("primary")
        self.send_btn.setMinimumHeight(108)
        self.send_btn.clicked.connect(self.send_file)
        sv.addWidget(self.send_btn)

        self.receive_btn = QPushButton("↓   QR → FILE\n     Convert QR to file")
        self.receive_btn.setMinimumHeight(108)
        self.receive_btn.clicked.connect(self.show_receive_page)
        sv.addWidget(self.receive_btn)

        sv.addSpacing(8)
        status_card = Card(True)
        st = QVBoxLayout(status_card)
        st.addWidget(self.lbl("DEVICE STATUS", "section"))
        st.addWidget(self.lbl("NETWORK           OFFLINE"))
        st.addWidget(self.lbl("POWER             SYSTEM"))
        self.security_lbl = self.lbl("SECURITY          OK", "good")
        st.addWidget(self.security_lbl)
        sv.addWidget(status_card)
        sv.addStretch()

        clear = QPushButton("CLEAR MEMORY")
        clear.clicked.connect(self.clear_all)
        sv.addWidget(clear)
        content.addWidget(side)

        # stack
        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)

        self.home_page = self._build_home()
        self.send_page = self._build_send()
        self.receive_page = self._build_receive()
        self.settings_page = self._build_settings()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.send_page)
        self.stack.addWidget(self.receive_page)
        self.stack.addWidget(self.settings_page)

        # footer
        foot = QHBoxLayout()
        settings_btn = QPushButton("SETTINGS")
        settings_btn.setObjectName("linkButton")
        settings_btn.clicked.connect(self.open_settings)
        foot.addWidget(settings_btn)
        foot.addStretch()
        foot.addWidget(self.lbl("AIRGAP MODE", "accentTitle"))
        foot.addStretch()
        foot.addWidget(self.lbl("NO NETWORK • FILE BYTES ONLY", "muted"))
        main.addLayout(foot)

    def _build_settings(self):
        p = Card()
        lay = QVBoxLayout(p)
        lay.setContentsMargins(34, 34, 34, 34)
        lay.setSpacing(18)

        lay.addWidget(self.lbl("SETTINGS", "accentTitle"))
        lay.addWidget(self.lbl("Configure AirGapQR", "title"))

        accent = QFrame()
        accent.setFrameShape(QFrame.HLine)
        accent.setFixedHeight(2)
        accent.setStyleSheet(f"background: {AMBER};")
        lay.addWidget(accent)

        lay.addSpacing(8)

        lay.addWidget(self.lbl("CAMERA", "section"))

        self.camera_combo = QComboBox()

        available_cameras = self._detect_cameras()

        if available_cameras:
            for camera in available_cameras:
                self.camera_combo.addItem(
                    camera["name"],
                    camera["index"]
                )

            self.camera_combo.setCurrentIndex(0)
        else:
            self.camera_combo.addItem("No camera detected", -1)

        lay.addWidget(self.camera_combo)

        lay.addWidget(self.lbl("FRAME DISPLAY TIME", "section"))

        self.frame_time_combo = QComboBox()
        self.frame_time_combo.addItem("0.25 sec (experimental)", 250)
        self.frame_time_combo.addItem("0.5 sec", 500)
        self.frame_time_combo.addItem("1 sec", 1000)
        self.frame_time_combo.addItem("2 sec", 2000)
        self.frame_time_combo.addItem("3 sec", 3000)
        self.frame_time_combo.addItem("5 sec", 5000)
        time_pos = self.frame_time_combo.findData(self.frame_display_time)
        if time_pos >= 0:
            self.frame_time_combo.setCurrentIndex(time_pos)

        lay.addWidget(self.frame_time_combo)

        lay.addWidget(self.lbl("MAX FILE SIZE", "section"))

        lay.addWidget(self.lbl("5 MB", "accentTitle"))
        lay.addWidget(self.lbl("Current release limit", "muted"))

        lay.addStretch()

        buttons = QHBoxLayout()

        back_btn = QPushButton("BACK")
        back_btn.setMinimumHeight(48)
        back_btn.clicked.connect(self.return_from_settings)

        save_btn = QPushButton("SAVE & BACK")
        save_btn.setObjectName("primary")
        save_btn.setMinimumHeight(48)
        save_btn.clicked.connect(self.save_settings)

        buttons.addWidget(back_btn)
        buttons.addWidget(save_btn)

        lay.addLayout(buttons)

        return p    

    def _build_home(self):
        p = Card()
        lay = QVBoxLayout(p)
        lay.setContentsMargins(34, 34, 34, 34)
        lay.addWidget(self.lbl("AIRGAP QR BRIDGE", "accentTitle"))
        lay.addWidget(self.lbl("Optical file transfer between isolated systems.", "title"))
        lay.addSpacing(16)
        lay.addWidget(self.lbl(
            "Choose FILE → QR to convert a local file into one or more QR frames.\n"
            "Choose QR → FILE to scan QR frames and reconstruct the original file.\n\n"
            "AirGapQR transfers files offline using QR codes and verifies integrity with SHA-256.\n\n"
            "May the open source be with you.\n"
            "Open source everything.\n\n"
            "— ton_ide_zvuk",
            wordwrap=True
        ))

        tips = Card()
        tips.setObjectName("softPanel")

        tips_layout = QVBoxLayout(tips)
        tips_layout.setContentsMargins(20, 18, 20, 18)
        tips_layout.setSpacing(8)

        tips_layout.addWidget(
            self.lbl("TIPS & RECOMMENDATIONS", "section")
        )

        tips_text = self.lbl(
            "• Use Fullscreen QR for difficult cameras.\n"
            "• Adjust QR background brightness if the image appears overexposed.\n"
            "• Keep both devices stable and positioned close enough for reliable scanning.\n"
            "• Prevent the display from going to sleep during a transfer.\n"
            "• Keep devices connected to power for longer transfers.\n"
            "• Verify that SHA-256 integrity shows OK after receiving.\n"
            "• If frames are missing, use MISSING FRAMES and PLAY SELECTED instead of restarting the full transfer.",
            wordwrap=True
        )

        tips_layout.addWidget(tips_text)

        lay.addSpacing(18)
        lay.addWidget(tips)

        support_row = QHBoxLayout()

        support_btn = QPushButton("SUPPORT THE PROJECT")
        support_btn.setObjectName("linkButton")
        support_btn.setCursor(Qt.PointingHandCursor)
        support_btn.clicked.connect(self.show_support_dialog)

        support_row.setSpacing(8)
        support_row.addStretch()
        support_row.addWidget(support_btn)
        support_row.addStretch()

        lay.addSpacing(10)
        lay.addLayout(support_row)

        lay.addStretch()
        return p

    def show_support_dialog(self):
        box = QMessageBox(self)

        box.setWindowTitle("Support AirGapQR")

        logo = QPixmap(resource_path("novac.png"))
        logo = logo.scaled(
            48,
            48,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        box.setIconPixmap(logo)

        box.setText("Support AirGapQR")
        box.setInformativeText(
            "If AirGapQR is useful to you, you can support its development with Bitcoin.\n\n"
            "Bitcoin support information is available on the official GitHub repository."
        )

        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    def _build_send(self):
        outer = QWidget()
        grid = QGridLayout(outer)
        grid.setContentsMargins(0,0,0,0)
        grid.setSpacing(14)

        center = Card()
        cv = QVBoxLayout(center)
        cv.setContentsMargins(24,22,24,22)
        self.send_heading = self.lbl("SEND FILE", "accentTitle")
        cv.addWidget(self.send_heading)
        self.frame_label = self.lbl("FRAME —", "title")
        self.frame_label.setAlignment(Qt.AlignCenter)
        cv.addWidget(self.frame_label)

        qrbox = Card(True)
        qv = QVBoxLayout(qrbox)
        self.qr_display = QLabel("NO FILE LOADED")
        self.qr_display.setAlignment(Qt.AlignCenter)
        self.qr_display.setMinimumSize(0, 0)
        self.qr_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        qv.addWidget(self.qr_display)
        cv.addWidget(qrbox, 1)

        nav = QHBoxLayout()
        self.prev_btn = QPushButton("←")
        self.prev_btn.setObjectName("nav")
        self.prev_btn.clicked.connect(self.prev_frame)
        self.next_btn = QPushButton("→")
        self.next_btn.setObjectName("nav")
        self.next_btn.clicked.connect(self.next_frame)
        self.dots = self.lbl("—", "accentTitle")
        self.dots.setAlignment(Qt.AlignCenter)
        nav.addWidget(self.prev_btn)
        nav.addStretch()
        nav.addWidget(self.dots)
        nav.addStretch()
        nav.addWidget(self.next_btn)
        cv.addLayout(nav)

        self.fullscreen_btn = QPushButton("⛶  CLICK QR FOR FULL SCREEN")
        self.fullscreen_btn.setObjectName("primary")
        self.fullscreen_btn.clicked.connect(self.open_qr_fullscreen)
        cv.addWidget(self.fullscreen_btn)

        brightness_row = QHBoxLayout()

        brightness_label = self.lbl("QR BACKGROUND BRIGHTNESS", "muted")

        self.qr_brightness_slider = QSlider(Qt.Horizontal)
        self.qr_brightness_slider.setRange(80, 255)
        self.qr_brightness_slider.setValue(self.qr_background_brightness)
        self.qr_brightness_slider.valueChanged.connect(self.update_qr_brightness)

        self.qr_brightness_value = self.lbl("100%")

        brightness_row.addWidget(brightness_label)
        brightness_row.addWidget(self.qr_brightness_slider, 1)
        brightness_row.addWidget(self.qr_brightness_value)

        cv.addLayout(brightness_row)

        recovery = QHBoxLayout()

        self.recovery_input = QLineEdit()
        self.recovery_input.setObjectName("recoveryInput")
        self.recovery_input.setPlaceholderText("Frames e.g. 17,43,88")

        self.recovery_play_btn = QPushButton("PLAY SELECTED")
        self.recovery_play_btn.setObjectName("primary")
        self.recovery_play_btn.clicked.connect(self.play_selected_frames)

        self.recovery_all_btn = QPushButton("PLAY ALL")
        self.recovery_all_btn.clicked.connect(self.play_all_frames)

        recovery.addWidget(self.recovery_input, 1)
        recovery.addWidget(self.recovery_play_btn)
        recovery.addWidget(self.recovery_all_btn)

        cv.addLayout(recovery)

        hint = self.lbl("Keep steady and ensure the whole QR code is visible.", "muted")
        hint.setAlignment(Qt.AlignCenter)
        cv.addWidget(hint)

        info = Card()
        info.setMinimumWidth(280)
        info.setMaximumWidth(360)
        iv = QVBoxLayout(info)
        iv.setContentsMargins(20,20,20,20)
        iv.addWidget(self.lbl("FILE INFO", "section"))
        self.file_name = self.lbl("—")
        self.file_size = self.lbl("—")
        self.file_frames = self.lbl("—")
        self.file_hash = QLineEdit("—")
        self.file_hash.setObjectName("hashField")
        self.file_hash.setReadOnly(True)
        
        self.file_hash.setFont(QFont("Consolas", 10))
        self.copy_hash_btn = QPushButton("COPY")
        self.copy_hash_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.file_hash.text())
        )
        for title, widget in [
            ("FILENAME", self.file_name), ("FILE SIZE", self.file_size),
            ("TOTAL FRAMES", self.file_frames), ("SHA-256", self.file_hash)
        ]:
            iv.addWidget(self.lbl(title, "muted"))
            iv.addWidget(widget)
            if widget is self.file_hash:
                iv.addWidget(self.copy_hash_btn)
            iv.addSpacing(8)
        iv.addStretch()
        iv.addWidget(self.lbl("STATUS", "muted"))
        self.send_status = self.lbl("READY", "good")
        iv.addWidget(self.send_status)

        grid.addWidget(center, 0, 0)
        grid.addWidget(info, 0, 1)
        grid.setColumnStretch(0, 1)
        return outer

    def _build_receive(self):
        outer = QWidget()
        grid = QGridLayout(outer)
        grid.setContentsMargins(0,0,0,0)
        grid.setSpacing(14)

        cam = Card()
        cv = QVBoxLayout(cam)
        cv.setContentsMargins(24,22,24,22)
        cv.addWidget(self.lbl("RECEIVE FILE", "accentTitle"))
        self.camera_view = QLabel("CAMERA OFF")
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setMinimumSize(0, 0)
        self.camera_view.setStyleSheet("background:#050505;border:1px solid #303030;border-radius:14px;")
        cv.addWidget(self.camera_view, 1)

        zoom_row = QHBoxLayout()

        zoom_label = self.lbl("CAMERA ZOOM", "muted")

        self.camera_zoom_slider = QSlider(Qt.Horizontal)
        self.camera_zoom_slider.setRange(0, 4)
        self.camera_zoom_slider.setSingleStep(1)
        self.camera_zoom_slider.setValue(0)
        self.camera_zoom_slider.valueChanged.connect(self.update_camera_zoom)

        self.camera_zoom_value = self.lbl("1.0×")

        zoom_row.addWidget(zoom_label)
        zoom_row.addWidget(self.camera_zoom_slider, 1)
        zoom_row.addWidget(self.camera_zoom_value)

        cv.addLayout(zoom_row) 

        zoom_marks = QHBoxLayout()

        for text in ["1.0×", "1.25×", "1.5×", "1.75×", "2.0×"]:
            mark = self.lbl(text, "muted")
            mark.setAlignment(Qt.AlignCenter)
            zoom_marks.addWidget(mark)

        cv.addLayout(zoom_marks)

        buttons = QHBoxLayout()
        self.cam_start = QPushButton("START CAMERA")
        self.cam_start.setObjectName("primary")
        self.cam_start.clicked.connect(self.start_camera)
        self.cam_stop = QPushButton("STOP CAMERA")
        self.cam_stop.clicked.connect(self.stop_camera)
        img_btn = QPushButton("IMPORT QR FRAMES")
        img_btn.clicked.connect(self.scan_images)
        buttons.addWidget(self.cam_start)
        buttons.addWidget(self.cam_stop)
        buttons.addWidget(img_btn)
        cv.addLayout(buttons)

        info = Card()
        info.setFixedWidth(360)
        iv = QVBoxLayout(info)
        iv.setContentsMargins(20,20,20,20)
        iv.addWidget(self.lbl("TRANSFER", "section"))
        self.rx_name = self.lbl("—")
        self.rx_size = self.lbl("—")
        self.rx_hash = QLineEdit("—")
        self.rx_hash.setObjectName("hashField")
        self.rx_hash.setReadOnly(True)
        self.rx_hash.setFont(QFont("Consolas", 10))
        self.copy_rx_source_btn = QPushButton("COPY")
        self.copy_rx_source_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.rx_hash.text())
        )
        self.rx_received_hash = QLineEdit("—")
        self.rx_received_hash.setObjectName("hashField")
        self.rx_received_hash.setReadOnly(True)
        self.rx_received_hash.setFont(QFont("Consolas", 10))
        self.copy_rx_received_btn = QPushButton("COPY")
        self.copy_rx_received_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.rx_received_hash.text())
        )
        self.rx_count = self.lbl("0 / 0")
        self.rx_missing = self.lbl("—", wordwrap=True)
        for title, widget in [
            ("FILENAME", self.rx_name),
            ("FILE SIZE", self.rx_size),
            ("SOURCE SHA-256", self.rx_hash),
            ("RECEIVED SHA-256", self.rx_received_hash),
            ("FRAMES", self.rx_count),
            ("MISSING FRAMES", self.rx_missing)
        ]:
            iv.addWidget(self.lbl(title, "muted"))
            iv.addWidget(widget)
            if widget is self.rx_hash:
                iv.addWidget(self.copy_rx_source_btn)
            elif widget is self.rx_received_hash:
                iv.addWidget(self.copy_rx_received_btn)
            iv.addSpacing(8)

        self.rx_progress = QProgressBar()
        self.rx_progress.setRange(0,100)
        self.rx_progress.setValue(0)
        iv.addWidget(self.rx_progress)
        iv.addSpacing(14)

        self.rx_integrity = self.lbl("WAITING", "accentTitle")
        iv.addWidget(self.rx_integrity)
        iv.addStretch()

        save = QPushButton("SAVE RECEIVED FILE")
        save.setObjectName("primary")
        save.clicked.connect(self.save_received)
        iv.addWidget(save)

        grid.addWidget(cam,0,0)
        grid.addWidget(info,0,1)
        grid.setColumnStretch(0,1)
        return outer

    def update_camera_zoom(self, value):
        zoom_values = [1.0, 1.25, 1.5, 1.75, 2.0]
        zoom_labels = ["1.0×", "1.25×", "1.5×", "1.75×", "2.0×"]

        self.camera_zoom = zoom_values[value]
        self.camera_zoom_value.setText(zoom_labels[value])

    def _show_home(self):
        self.stack.setCurrentWidget(self.home_page)
        self.top_status.setText("●  READY")

    def open_settings(self):
        self.settings_return_page = self.stack.currentWidget()

        camera_pos = self.camera_combo.findData(self.camera_index)
        if camera_pos >= 0:
            self.camera_combo.setCurrentIndex(camera_pos)

        time_pos = self.frame_time_combo.findData(self.frame_display_time)
        if time_pos >= 0:
            self.frame_time_combo.setCurrentIndex(time_pos)

        self.settings_frame_timer_was_active = self.frame_timer.isActive()
        self.settings_camera_was_active = self.cap is not None

        if self.settings_frame_timer_was_active:
            self.frame_timer.stop()

        if self.settings_camera_was_active:
            self.stop_camera()

        self.stack.setCurrentWidget(self.settings_page)
        self.top_status.setText("●  SETTINGS")

    def send_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose file")
        if not path: return
        try:
            size = os.path.getsize(path)
            if size > MAX_FILE_SIZE:
                raise ValueError("v0.3 limit is 5 MiB.")
            data = Path(path).read_bytes()
            self.frames = encode_file(Path(path).name, data, CHUNK_SIZE)
            self.frame_index = 0
            self.selected_frame_indices = []
            self.selected_frame_pos = 0
            self.recovery_mode = False
            self.recovery_input.clear()
            self.file_name.setText(Path(path).name)
            self.file_size.setText(fmt_size(len(data)))
            self.file_frames.setText(str(len(self.frames)))
            self.file_hash.setText(sha256_hex(data))
            self.file_hash.setCursorPosition(0)
            self.send_status.setText("READY TO SEND")
            self.send_status.setObjectName("good")
            self.send_status.style().unpolish(self.send_status)
            self.send_status.style().polish(self.send_status)
            self.stack.setCurrentWidget(self.send_page)
            self.top_status.setText("●  SEND")
            self.show_current_frame()
            self.frame_timer.start(self.frame_display_time)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def show_current_frame(self):
        if not self.frames: return
        frame = self.frames[self.frame_index]
        pil = make_qr(
            frame.to_text(),
            box_size=8,
            background_brightness=self.qr_background_brightness
        )

        qimg = QImage(ImageQt(pil))
        pix = QPixmap.fromImage(qimg)
       
        # safer fallback scale
        available = self.qr_display.size()
        margin = 20
        pix = QPixmap.fromImage(qimg).scaled(
            max(100, available.width() - margin),
            max(100, available.height() - margin),
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )
        self.qr_display.setPixmap(pix)
        self.frame_label.setText(f"FRAME {self.frame_index+1} OF {len(self.frames)}")
        self.dots.setText("  ".join("●" if i==self.frame_index else "○" for i in range(min(len(self.frames),12))))

    def update_qr_brightness(self, value):
        self.qr_background_brightness = value

        percent = int(round(value * 100 / 255))

        self.qr_brightness_value.setText(f"{percent}%")

        if self.qr_brightness_slider.value() != value:
            self.qr_brightness_slider.blockSignals(True)
            self.qr_brightness_slider.setValue(value)
            self.qr_brightness_slider.blockSignals(False)

        if hasattr(self, "fullscreen_brightness_slider"):
            if self.fullscreen_brightness_slider.value() != value:
                self.fullscreen_brightness_slider.blockSignals(True)
                self.fullscreen_brightness_slider.setValue(value)
                self.fullscreen_brightness_slider.blockSignals(False)

        if hasattr(self, "fullscreen_brightness_value"):
            self.fullscreen_brightness_value.setText(f"{percent}%")

        self.show_current_frame()
        self.update_fullscreen_qr()

    def play_selected_frames(self):
        if not self.frames:
            QMessageBox.warning(self, "Recovery", "No file is loaded.")
            return

        raw = self.recovery_input.text().strip()

        if not raw:
            QMessageBox.warning(
                self,
                "Recovery",
                "Enter one or more frame numbers, for example: 17,43,88"
            )
            return

        try:
            numbers = []

            for part in raw.split(","):
                part = part.strip()

                if not part:
                    continue

                number = int(part)

                if not (1 <= number <= len(self.frames)):
                    raise ValueError

                if number not in numbers:
                    numbers.append(number)

        except ValueError:
            QMessageBox.warning(
                self,
                "Recovery",
                f"Use frame numbers from 1 to {len(self.frames)}, separated by commas."
            )
            return

        if not numbers:
            QMessageBox.warning(self, "Recovery", "No valid frame numbers entered.")
            return

        self.selected_frame_indices = [number - 1 for number in numbers]
        self.selected_frame_pos = 0
        self.recovery_mode = True

        self.frame_index = self.selected_frame_indices[0]
        self.show_current_frame()
        self.update_fullscreen_qr()

        self.frame_timer.start(self.frame_display_time)

        self.send_status.setText(
            f"RECOVERY MODE — {len(self.selected_frame_indices)} SELECTED"
        )

    def play_all_frames(self):
        if not self.frames:
            QMessageBox.warning(self, "Recovery", "No file is loaded.")
            return

        self.recovery_mode = False
        self.selected_frame_indices = []
        self.selected_frame_pos = 0

        self.show_current_frame()
        self.update_fullscreen_qr()

        self.frame_timer.start(self.frame_display_time)

        self.send_status.setText("PLAYING ALL FRAMES")

    def prev_frame(self):
        if self.frames:
            self.frame_index = (self.frame_index - 1) % len(self.frames)
            self.show_current_frame()
            self.update_fullscreen_qr()

    def open_qr_fullscreen(self):
        if not self.frames:
            return

        self.qr_fullscreen = QWidget()
        self.qr_fullscreen.keyPressEvent = self.fullscreen_key_press
        self.qr_fullscreen.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.qr_fullscreen.setStyleSheet("background: #000000;")

        layout = QVBoxLayout(self.qr_fullscreen)
        layout.setContentsMargins(20, 20, 20, 20)

        self.fullscreen_frame_label = QLabel()
        self.fullscreen_frame_label.setAlignment(Qt.AlignCenter)
        self.fullscreen_frame_label.setStyleSheet(
            "color: #F7931A; font-size: 22px; font-weight: 700;"
        )
        layout.addWidget(self.fullscreen_frame_label)

        self.fullscreen_qr = QLabel()
        self.fullscreen_qr.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.fullscreen_qr, 1)

        fullscreen_brightness_row = QHBoxLayout()

        fullscreen_brightness_label = QLabel("QR BACKGROUND BRIGHTNESS")
        fullscreen_brightness_label.setStyleSheet(
            "color: #9f9f9f; font-size: 14px;"
        )

        self.fullscreen_brightness_slider = QSlider(Qt.Horizontal)
        self.fullscreen_brightness_slider.setRange(80, 255)
        self.fullscreen_brightness_slider.setValue(
            self.qr_background_brightness
        )

        self.fullscreen_brightness_slider.valueChanged.connect(
            self.update_qr_brightness
        )

        self.fullscreen_brightness_value = QLabel(
            f"{int(round(self.qr_background_brightness * 100 / 255))}%"
        )
        self.fullscreen_brightness_value.setStyleSheet(
            "color: #9f9f9f; font-size: 14px;"
        )

        fullscreen_brightness_row.addWidget(fullscreen_brightness_label)
        fullscreen_brightness_row.addWidget(
            self.fullscreen_brightness_slider, 1
        )
        fullscreen_brightness_row.addWidget(
            self.fullscreen_brightness_value
        )

        layout.addLayout(fullscreen_brightness_row)

        self.fullscreen_hint = QLabel("ESC — EXIT FULL SCREEN")
        self.fullscreen_hint.setAlignment(Qt.AlignCenter)
        self.fullscreen_hint.setStyleSheet(
            "color: #9f9f9f; font-size: 14px;"
        )
        layout.addWidget(self.fullscreen_hint)

        self.qr_fullscreen.showFullScreen()
        QTimer.singleShot(100, self.update_fullscreen_qr)

    def update_fullscreen_qr(self):
        if not self.frames or not hasattr(self, "fullscreen_qr"):
            return

        frame = self.frames[self.frame_index]

        pil = make_qr(
            frame.to_text(),
            box_size=8,
            background_brightness=self.qr_background_brightness
        )

        qimg = QImage(ImageQt(pil))
        pix = QPixmap.fromImage(qimg)

        available = self.fullscreen_qr.size()
        margin = 40

        pix = pix.scaled(
            max(200, available.width() - margin),
            max(200, available.height() - margin),
            Qt.KeepAspectRatio,
            Qt.FastTransformation
        )

        self.fullscreen_qr.setPixmap(pix)
        self.fullscreen_frame_label.setText(
            f"FRAME {self.frame_index+1} OF {len(self.frames)}"
        )

    def fullscreen_key_press(self, event):
        if event.key() == Qt.Key_Escape:
            self.qr_fullscreen.close()

    def next_frame(self):
        if self.frames:
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.show_current_frame()
            self.update_fullscreen_qr()

    def show_receive_page(self):
        self.stack.setCurrentWidget(self.receive_page)
        self.top_status.setText("●  RECEIVE")

    def _detect_cameras(self):
        cameras = []

        for camera in enumerate_cameras():
            cameras.append({
                "name": camera.name,
                "index": camera.index,
                "backend": camera.backend,
            })

        return cameras

    def save_settings(self):
        self.camera_index = self.camera_combo.currentData()
        self.frame_display_time = self.frame_time_combo.currentData()

        QMessageBox.information(
            self,
            "Settings",
            "Settings saved."
        )

        self.return_from_settings()

    def return_from_settings(self):
        target_page = self.settings_return_page or self.home_page
        self.stack.setCurrentWidget(target_page)

        if target_page is self.send_page:
            self.top_status.setText("●  SEND")
            if self.settings_frame_timer_was_active and self.frames:
                self.frame_timer.start(self.frame_display_time)

        elif target_page is self.receive_page:
            self.top_status.setText("●  RECEIVE")
            if self.settings_camera_was_active:
                self.start_camera()

        else:
            self.top_status.setText("●  READY")

        self.settings_return_page = None
        self.settings_frame_timer_was_active = False
        self.settings_camera_was_active = False
    
    def start_camera(self):
        if self.cap is not None: return

        self.cap = cv2.VideoCapture(self.camera_index)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            QMessageBox.critical(self, "Camera", "Camera is not available.")
            return
        self.last_camera_text = ""
        self.camera_timer.start(30)
        self.top_status.setText("●  CAMERA")

    def stop_camera(self):
        self.camera_timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.camera_view.setText("CAMERA OFF")
        self.camera_view.setPixmap(QPixmap())

    def _decode_qr(self, image):
        if image is None:
            return ""

        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # 1. Normal decode
        text, _, _ = self.detector.detectAndDecode(gray)

        if text:
            return text

        # 2. Perspective-corrected fallback
        ok_detect, corners = self.detector.detect(gray)

        if not ok_detect or corners is None:
            return ""

        pts = corners.reshape(4, 2).astype("float32")

        size = 600.0
        dst = np.array([
            [0, 0],
            [size - 1, 0],
            [size - 1, size - 1],
            [0, size - 1]
        ], dtype="float32")

        matrix = cv2.getPerspectiveTransform(pts, dst)

        warped = cv2.warpPerspective(
            gray,
            matrix,
            (int(size), int(size))
        )

        text, _, _ = self.detector.detectAndDecode(warped)

        return text or ""

    def _apply_camera_zoom(self, frame):
        if frame is None or self.camera_zoom <= 1.0:
            return frame

        height, width = frame.shape[:2]

        crop_width = max(1, int(width / self.camera_zoom))
        crop_height = max(1, int(height / self.camera_zoom))

        x1 = (width - crop_width) // 2
        y1 = (height - crop_height) // 2

        return frame[
            y1:y1 + crop_height,
            x1:x1 + crop_width
        ]

    def _camera_tick(self):
        if self.cap is None: return
        ok, frame = self.cap.read()
        if not ok: return

        frame = self._apply_camera_zoom(frame)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(
            rgb.data,
            w,
            h,
            ch * w,
            QImage.Format_RGB888
        )
        pix = QPixmap.fromImage(qimg)

        available = self.camera_view.size()
        pix = pix.scaled(
            max(100, available.width() - 20),
            max(100, available.height() - 20),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.camera_view.setPixmap(pix)

        text = self._decode_qr(frame)

        if text and text != self.last_camera_text:
            if self._process_qr(text):
                self.last_camera_text = text
  
                
    def _advance_frame(self):
        if not self.frames:
            return

        if self.recovery_mode and self.selected_frame_indices:
            self.selected_frame_pos = (
                self.selected_frame_pos + 1
            ) % len(self.selected_frame_indices)

            self.frame_index = self.selected_frame_indices[
                self.selected_frame_pos
            ]
        else:
            self.frame_index = (
                self.frame_index + 1
            ) % len(self.frames)

        self.show_current_frame()
        self.update_fullscreen_qr()


    def scan_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose QR image", filter="Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path: return
        img = cv2.imread(path)
        if img is None:
            QMessageBox.warning(self, "QR", "Image could not be loaded.")
            return
        text = self._decode_qr(img)

        if text:
            self._process_qr(text)

    def scan_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose QR images",
            filter="Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if not paths:
            return
        paths.sort(key=lambda p: [
            int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", p)
        ])

        for path in paths:
            img = cv2.imread(path)

            if img is None:
                continue

            text = self._decode_qr(img)

            if text:
                self._process_qr(text)

    def _process_qr(self, text):
        try:
            frame = self.assembler.add_text(text)
            got,total = self.assembler.progress
            self.rx_name.setText(frame.filename)
            self.rx_size.setText(fmt_size(frame.file_size))
            self.rx_hash.setText(frame.sha256)
            self.rx_hash.setCursorPosition(0)
            self.rx_count.setText(f"{got} / {total}")

            missing = [i + 1 for i in self.assembler.missing_indices]

            if missing:
                self.rx_missing.setText(", ".join(map(str, missing)))
            else:
                self.rx_missing.setText("NONE")

            self.rx_progress.setValue(int(got*100/total))
            self.rx_integrity.setText("RECEIVING")
            self.top_status.setText(f"●  RECEIVE {got}/{total}")

            if self.assembler.complete:
                self.received_data = self.assembler.build()
                self.rx_received_hash.setText(sha256_hex(self.received_data))
                self.rx_received_hash.setCursorPosition(0)
                self.rx_integrity.setText("INTEGRITY OK")
                self.rx_integrity.setObjectName("good")
                self.rx_integrity.style().unpolish(self.rx_integrity)
                self.rx_integrity.style().polish(self.rx_integrity)
                self.top_status.setText("●  INTEGRITY OK")
                QMessageBox.information(self, "Transfer complete", "SHA-256 integrity check passed.")
            return True
        except ProtocolError as e:
            self.rx_integrity.setText("FRAME ERROR")
            QMessageBox.critical(self, "Invalid QR", str(e))
            return False

    def save_received(self):
        if self.received_data is None or not self.assembler.complete:
            QMessageBox.warning(self, "No file", "No complete received file.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save reconstructed file", self.assembler.filename or "received.bin")
        if not path: return
        Path(path).write_bytes(self.received_data)
        QMessageBox.information(self, "Saved", f"Saved.\nSHA-256:\n{sha256_hex(self.received_data)}")

    def clear_all(self):
        self.stop_camera()
        self.frame_timer.stop()
        self.frames = []
        self.frame_index = 0
        self.selected_frame_indices = []
        self.selected_frame_pos = 0
        self.recovery_mode = False
        self.recovery_input.clear()
        self.assembler.reset()
        self.received_data = None
        self.qr_display.setPixmap(QPixmap())
        self.qr_display.setText("NO FILE LOADED")
        self.file_name.setText("—"); 
        self.file_size.setText("—")
        self.file_frames.setText("—"); 
        self.file_hash.setText("—")
        self.rx_name.setText("—"); 
        self.rx_size.setText("—")
        self.rx_hash.setText("—")
        self.rx_received_hash.setText("—") 
        self.rx_count.setText("0 / 0")
        self.rx_missing.setText("—")
        self.rx_progress.setValue(0); 
        self.rx_integrity.setText("WAITING")
        self._show_home()

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    w = AirGapApp()
    w.show()
    sys.exit(app.exec())
