import os
import sys
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QCheckBox,
    QLineEdit, QProgressBar, QTabWidget, QTextEdit, QScrollArea,
    QFileDialog, QMessageBox, QFrame, QSizePolicy, QStackedWidget,
    QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QObject, QThread, QPropertyAnimation, Property, QRectF
from PySide6.QtGui import QPalette, QColor, QFont, QGuiApplication, QClipboard, QPainter, QPainterPath

from converter_engine import MarkItDownEngine
import base64
from assets import SVG_ICONS

from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QByteArray

def get_icon(name, color_hex):
    svg_str = SVG_ICONS.get(name, "")
    if not svg_str:
        return QIcon()
    svg_str = svg_str.replace("currentColor", color_hex)
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(svg_str.encode('utf-8')), "SVG")
    return QIcon(pixmap)

class WorkerSignals(QObject):
    single_done = Signal(str, str, str, bool, bool, str)
    batch_progress = Signal(int, int, str, str)
    batch_done = Signal(list)

class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._position = 2
        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setDuration(150)
        self.stateChanged.connect(self.setup_animation)

    @Property(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    def setup_animation(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(self.width() - 20)
        else:
            self.animation.setEndValue(2)
        self.animation.start()

    def hitButton(self, pos):
        return self.contentsRect().contains(pos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        rect = QRectF(0, 0, self.width(), self.height())
        
        is_dark = True
        window = self.window()
        if hasattr(window, 'is_dark'):
            is_dark = window.is_dark

        if not self.isChecked():
            bg_color = QColor(60, 60, 60) if is_dark else QColor(200, 200, 200)
            handle_color = QColor(150, 150, 150) if is_dark else QColor(100, 100, 100)
        else:
            bg_color = QColor(230, 230, 230) if is_dark else QColor(40, 40, 40)
            handle_color = QColor(30, 30, 30) if is_dark else QColor(240, 240, 240)

        p.setBrush(bg_color)
        p.drawRoundedRect(0, 0, rect.width(), rect.height(), self.height()/2, self.height()/2)
        p.setBrush(handle_color)
        p.drawEllipse(self._position, 2, 18, 18)
        p.end()

class QueueDropZoneWidget(QFrame):
    files_dropped = Signal(list)
    remove_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("queueDropZone")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Stacked widget to switch between Empty State and List
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # Page 0: Empty Drag & Drop
        self.empty_page = QWidget()
        self.empty_layout = QVBoxLayout(self.empty_page)
        self.empty_prompt = QLabel("Drag & Drop Files Here")
        self.empty_prompt.setAlignment(Qt.AlignCenter)
        self.empty_prompt.setStyleSheet("color: #666; font-weight: bold; font-size: 13px;")
        self.empty_layout.addStretch()
        self.empty_layout.addWidget(self.empty_prompt)
        self.empty_layout.addStretch()
        self.stack.addWidget(self.empty_page)

        # Page 1: Scrollable List
        self.list_page = QWidget()
        self.list_layout = QVBoxLayout(self.list_page)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_content_layout.setSpacing(8)
        self.scroll_content_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.scroll_content)
        self.list_layout.addWidget(self.scroll)
        self.stack.addWidget(self.list_page)

        self._reset_style()

    def update_list(self, files, success_files):
        # Clear existing
        while self.scroll_content_layout.count():
            item = self.scroll_content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not files:
            self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(1)
            for f in files:
                item_w = QWidget()
                h_lay = QHBoxLayout(item_w)
                h_lay.setContentsMargins(5, 5, 5, 5)
                h_lay.setSpacing(10)
                
                is_success = f in success_files
                dot = QLabel("•")
                dot.setFont(QFont("Arial", 16, QFont.Bold))
                dot.setStyleSheet(f"color: {'#28a745' if is_success else '#666'};")
                
                fname = os.path.basename(f)
                lbl = QLabel(fname)
                lbl.setStyleSheet("color: #ccc; font-size: 13px;")
                if is_success:
                    lbl.setStyleSheet("color: #ccc; font-size: 13px;") 
                
                # Delete btn
                btn_del = QPushButton()
                btn_del.setIcon(get_icon("x", "#666"))
                btn_del.setFixedSize(20, 20)
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setStyleSheet("""
                    QPushButton { background: transparent; color: #666; border: none; font-size: 12px; }
                    QPushButton:hover { color: #f0f0f0; }
                """)
                btn_del.clicked.connect(lambda checked=False, fp=f: self.remove_requested.emit(fp))
                
                h_lay.addWidget(dot)
                h_lay.addWidget(lbl, stretch=1)
                h_lay.addWidget(btn_del)
                
                self.scroll_content_layout.addWidget(item_w)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet("QFrame#queueDropZone { border: 2px dashed #4da6ff; border-radius: 8px; background-color: #1e1e1e; }")
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._reset_style()

    def dropEvent(self, event):
        self._reset_style()
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        if paths:
            self.files_dropped.emit(paths)

    def _reset_style(self):
        self.setStyleSheet("QFrame#queueDropZone { border: 1px solid rgba(128, 128, 128, 0.3); border-radius: 8px; background-color: transparent; }")

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class MarkItDownGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkItDown")
        self.setWindowIcon(QIcon(get_resource_path("icon.ico")))
        self.resize(1100, 750)
        self.setMinimumSize(950, 650)
        
        self.is_dark = True
        self.engine = MarkItDownEngine()
        self.selected_files = []
        self.converted_success_files = set()
        self.preview_tab_widgets = []
        
        dark_svg = SVG_ICONS["chevron-down"].replace("currentColor", "#666")
        light_svg = SVG_ICONS["chevron-down"].replace("currentColor", "#888")
        self.chevron_dark_uri = "data:image/svg+xml;base64," + base64.b64encode(dark_svg.encode('utf-8')).decode('utf-8')
        self.chevron_light_uri = "data:image/svg+xml;base64," + base64.b64encode(light_svg.encode('utf-8')).decode('utf-8')

        self.signals = WorkerSignals()
        self.signals.single_done.connect(self._finish_single)
        self.signals.batch_progress.connect(self._update_progress_ui)
        self.signals.batch_done.connect(self._finish_batch)

        self._build_ui()
        self._apply_dark_theme()

    def _apply_dark_theme(self):
        self.is_dark = True
        app = QApplication.instance()
        palette = QPalette()
        dark_bg = QColor(15, 15, 15) 
        palette.setColor(QPalette.Window, dark_bg)
        palette.setColor(QPalette.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.Base, QColor(20, 20, 20))
        palette.setColor(QPalette.AlternateBase, QColor(25, 25, 25))
        palette.setColor(QPalette.ToolTipBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ToolTipText, dark_bg)
        palette.setColor(QPalette.Text, QColor(240, 240, 240))
        palette.setColor(QPalette.Button, QColor(30, 30, 30))
        palette.setColor(QPalette.ButtonText, QColor(240, 240, 240))
        app.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #0e0e0e; }
            QFrame#leftPanel { background-color: #141414; border-right: 1px solid #222; }
            QLabel { color: #f0f0f0; }
            QLabel.sectionHeader { color: #666; font-size: 10px; font-weight: bold; letter-spacing: 1px; }
            QPushButton { 
                background-color: #1a1a1a; border: 1px solid #333; 
                padding: 6px; border-radius: 6px; color: #ccc;
            }
            QPushButton:hover { background-color: #222; border-color: #444; }
            QPushButton#primaryBtn { 
                background-color: #f0f0f0; border: none; font-weight: bold; font-size: 14px; color: #111;
                border-radius: 8px;
            }
            QPushButton#primaryBtn:hover { background-color: #ffffff; }
            QPushButton#clearBtn { background-color: transparent; border: none; color: #666; font-size: 10px; font-weight: bold; }
            QPushButton#clearBtn:hover { color: #ccc; }
            QPushButton#themeBtn { background-color: transparent; border: none; font-size: 16px; }
            
            QLineEdit, QComboBox, QTextEdit { 
                background-color: #1a1a1a; border: 1px solid #2a2a2a; 
                color: #ddd; padding: 8px; border-radius: 6px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid #444; }
            QComboBox::drop-down { border: none; background: transparent; width: 30px; }
            QComboBox::down-arrow { image: url('%s'); width: 14px; height: 14px; }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a;
                color: #ddd;
                selection-background-color: #333;
                selection-color: #fff;
                border: 1px solid #2a2a2a;
            }
            
            QTabWidget::pane { border: none; border-top: 1px solid #222; background: transparent; }
            QTabBar::tab { 
                background: transparent; padding: 10px 16px; border: none; 
                border-bottom: 2px solid transparent; color: #666; font-weight: bold; font-size: 13px;
            }
            QTabBar::tab:selected { color: #f0f0f0; border-bottom: 2px solid #f0f0f0; }
            QTabBar::tab:hover { color: #aaa; }
            QProgressBar {
                border: none; border-radius: 2px; text-align: center;
                background-color: #222; color: transparent; height: 4px;
            }
            QProgressBar::chunk { background-color: #f0f0f0; border-radius: 2px; }
            
            QPushButton#iconBtn {
                background-color: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 6px; padding: 4px 8px;
                color: #ccc;
            }
            QPushButton#iconBtn:hover { background-color: #3a3a3a; }
        """ % self.chevron_dark_uri)
        
        self.theme_btn.setIcon(get_icon("sun", "#ccc"))
        self.btn_dest_browse.setIcon(get_icon("plus", "#ccc"))
        self.btn_select_files.setIcon(get_icon("file-plus", "#ccc"))
        self.btn_select_folder.setIcon(get_icon("folder-plus", "#ccc"))
        self.btn_convert.setIcon(get_icon("arrow-right", "#111"))
        self.btn_copy.setIcon(get_icon("copy", "#888"))
        
        if hasattr(self, 'icon_lbl'):
            self.icon_lbl.setPixmap(get_icon("arrow-up-down", "#444").pixmap(40, 40))

        if hasattr(self, 'drop_zone'):
            self.drop_zone.update_list(self.selected_files, self.converted_success_files)

    def _apply_light_theme(self):
        self.is_dark = False
        app = QApplication.instance()
        palette = QPalette()
        app.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #ffffff; }
            QFrame#leftPanel { background-color: #f7f7f7; border-right: 1px solid #e0e0e0; }
            QLabel { color: #111; }
            QLabel.sectionHeader { color: #888; font-size: 10px; font-weight: bold; letter-spacing: 1px; }
            QPushButton { 
                background-color: #fff; border: 1px solid #ddd; 
                padding: 6px; border-radius: 6px; color: #333;
            }
            QPushButton:hover { background-color: #f0f0f0; }
            QPushButton#primaryBtn { 
                background-color: #111; border: none; color: #fff; font-weight: bold; font-size: 14px;
                border-radius: 8px;
            }
            QPushButton#primaryBtn:hover { background-color: #333; }
            QPushButton#clearBtn { background-color: transparent; border: none; color: #888; font-size: 10px; font-weight: bold; }
            QPushButton#clearBtn:hover { color: #333; }
            QPushButton#themeBtn { background-color: transparent; border: none; font-size: 16px; }
            
            QLineEdit, QComboBox, QTextEdit { 
                background-color: #fff; border: 1px solid #ddd; 
                color: #111; padding: 8px; border-radius: 6px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid #aaa; }
            QComboBox::drop-down { border: none; background: transparent; width: 30px; }
            QComboBox::down-arrow { image: url('%s'); width: 14px; height: 14px; }
            QComboBox QAbstractItemView {
                background-color: #fff;
                color: #111;
                selection-background-color: #f0f0f0;
                selection-color: #111;
                border: 1px solid #ddd;
            }
            
            QTabWidget::pane { border: none; border-top: 1px solid #ddd; background: transparent; }
            QTabBar::tab { 
                background: transparent; padding: 10px 16px; border: none; 
                border-bottom: 2px solid transparent; color: #888; font-weight: bold; font-size: 13px;
            }
            QTabBar::tab:selected { color: #111; border-bottom: 2px solid #111; }
            QTabBar::tab:hover { color: #555; }
            QProgressBar {
                border: none; border-radius: 2px; text-align: center;
                background-color: #e0e0e0; color: transparent; height: 4px;
            }
            QProgressBar::chunk { background-color: #111; border-radius: 2px; }
            
            QPushButton#iconBtn {
                background-color: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 4px 8px;
                color: #555;
            }
            QPushButton#iconBtn:hover { background-color: #f0f0f0; }
        """ % self.chevron_light_uri)
        
        self.theme_btn.setIcon(get_icon("moon", "#333"))
        self.btn_dest_browse.setIcon(get_icon("plus", "#555"))
        self.btn_select_files.setIcon(get_icon("file-plus", "#333"))
        self.btn_select_folder.setIcon(get_icon("folder-plus", "#333"))
        self.btn_convert.setIcon(get_icon("arrow-right", "#fff"))
        self.btn_copy.setIcon(get_icon("copy", "#888"))

        if hasattr(self, 'icon_lbl'):
            self.icon_lbl.setPixmap(get_icon("arrow-up-down", "#999").pixmap(40, 40))

        if hasattr(self, 'drop_zone'):
            self.drop_zone.update_list(self.selected_files, self.converted_success_files)

    def toggle_theme(self):
        if self.is_dark:
            self._apply_light_theme()
        else:
            self._apply_dark_theme()

    def create_section_header(self, text):
        lbl = QLabel(text)
        lbl.setProperty("class", "sectionHeader")
        return lbl

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ================= LEFT PANEL =================
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(25, 25, 25, 25)
        left_layout.setSpacing(20)
        
        # Window Controls Mock area / Theme Button
        top_ctrl_layout = QHBoxLayout()
        top_ctrl_layout.addStretch()
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        top_ctrl_layout.addWidget(self.theme_btn)
        left_layout.addLayout(top_ctrl_layout)

        # OUTPUT FORMAT
        left_layout.addWidget(self.create_section_header("OUTPUT FORMAT"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown (.md)", "Plain Text (.txt)", "HTML (.html)"])
        left_layout.addWidget(self.format_combo)

        # SETTINGS
        left_layout.addWidget(self.create_section_header("SETTINGS"))
        
        auto_save_layout = QHBoxLayout()
        auto_save_lbl = QLabel("Auto-save to directory")
        auto_save_lbl.setStyleSheet("color: #aaa; font-size: 13px;")
        auto_save_layout.addWidget(auto_save_lbl)
        auto_save_layout.addStretch()
        self.auto_save_switch = ToggleSwitch()
        auto_save_layout.addWidget(self.auto_save_switch)
        left_layout.addLayout(auto_save_layout)

        dest_layout = QHBoxLayout()
        self.dest_entry = QLineEdit()
        self.dest_entry.setPlaceholderText("Output Directory...")
        dest_layout.addWidget(self.dest_entry)
        self.btn_dest_browse = QPushButton()
        self.btn_dest_browse.setObjectName("iconBtn")
        self.btn_dest_browse.setFixedSize(34, 34)
        self.btn_dest_browse.clicked.connect(self.browse_output_dir)
        dest_layout.addWidget(self.btn_dest_browse)
        left_layout.addLayout(dest_layout)

        # SOURCE FILES
        left_layout.addWidget(self.create_section_header("SOURCE FILES"))
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_select_files = QPushButton("Files")
        self.btn_select_files.clicked.connect(self.browse_files)
        self.btn_select_folder = QPushButton("Folder")
        self.btn_select_folder.clicked.connect(self.browse_folder)
        btn_layout.addWidget(self.btn_select_files)
        btn_layout.addWidget(self.btn_select_folder)
        left_layout.addLayout(btn_layout)

        # QUEUE
        queue_header_layout = QHBoxLayout()
        self.lbl_queue = self.create_section_header("QUEUE  0")
        queue_header_layout.addWidget(self.lbl_queue)
        queue_header_layout.addStretch()
        self.btn_clear_queue = QPushButton("CLEAR")
        self.btn_clear_queue.setObjectName("clearBtn")
        self.btn_clear_queue.setCursor(Qt.PointingHandCursor)
        self.btn_clear_queue.clicked.connect(self.clear_all_files)
        queue_header_layout.addWidget(self.btn_clear_queue)
        left_layout.addLayout(queue_header_layout)

        # DropZone / Queue Widget
        self.drop_zone = QueueDropZoneWidget()
        self.drop_zone.files_dropped.connect(self._handle_dropped_files)
        self.drop_zone.remove_requested.connect(self.remove_single_file)
        left_layout.addWidget(self.drop_zone, stretch=1)

        # Progress line
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)

        # Convert Button
        self.btn_convert = QPushButton("Start Conversion")
        self.btn_convert.setObjectName("primaryBtn")
        self.btn_convert.setMinimumHeight(45)
        self.btn_convert.setCursor(Qt.PointingHandCursor)
        self.btn_convert.clicked.connect(self.start_conversion)
        left_layout.addWidget(self.btn_convert)

        self.status_label = QLabel("Status: Ready (0 files)")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_label)

        left_panel.setFixedWidth(340)
        main_layout.addWidget(left_panel)

        # ================= RIGHT PANEL =================
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.right_stack = QStackedWidget()
        right_layout.addWidget(self.right_stack)

        # Right Page 0: Empty State
        empty_state = QWidget()
        empty_layout = QVBoxLayout(empty_state)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(get_icon("arrow-up-down", "#444").pixmap(40, 40))
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("margin-bottom: 10px;")
        
        no_file_lbl = QLabel("No file selected")
        no_file_lbl.setAlignment(Qt.AlignCenter)
        no_file_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #ccc;")
        
        sub_no_file_lbl = QLabel("Select a file from the queue to preview its markdown output or start\na new conversion.")
        sub_no_file_lbl.setAlignment(Qt.AlignCenter)
        sub_no_file_lbl.setStyleSheet("font-size: 12px; color: #666;")
        
        empty_layout.addStretch()
        empty_layout.addWidget(self.icon_lbl)
        empty_layout.addWidget(no_file_lbl)
        empty_layout.addWidget(sub_no_file_lbl)
        empty_layout.addStretch()
        self.right_stack.addWidget(empty_state)

        # Right Page 1: Tabs
        tabs_page = QWidget()
        tabs_layout = QVBoxLayout(tabs_page)
        tabs_layout.setContentsMargins(10, 10, 10, 0)
        
        self.tabview = QTabWidget()
        self.tabview.setTabsClosable(True)
        self.tabview.tabCloseRequested.connect(self._close_preview_tab)
        self.tabview.currentChanged.connect(self._on_tab_changed)
        tabs_layout.addWidget(self.tabview)
        
        self.right_stack.addWidget(tabs_page)
        
        # Footer
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(15, 10, 15, 15)
        
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.setFixedSize(80, 26)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setStyleSheet("QPushButton { background: transparent; color: #888; border: none; font-size: 12px; } QPushButton:hover { color: #ccc; }")
        self.btn_copy.clicked.connect(self._copy_current_tab)
        footer_layout.addWidget(self.btn_copy)
        
        footer_layout.addStretch()
        
        self.stats_lbl = QLabel("Ln 0, Col 0    0 Bytes")
        self.stats_lbl.setStyleSheet("color: #555; font-size: 11px;")
        footer_layout.addWidget(self.stats_lbl)
        
        right_layout.addWidget(footer_widget)
        
        main_layout.addWidget(right_panel)
        
        self.update_graphical_file_queue()

    def _on_tab_changed(self, index):
        if index == -1:
            self.stats_lbl.setText("Ln 0, Col 0    0 Bytes")
            return
            
        widget = self.tabview.widget(index)
        if widget:
            text_edit = widget.findChild(QTextEdit)
            if text_edit:
                self._update_stats(text_edit)

    def _update_stats(self, text_edit):
        text = text_edit.toPlainText()
        cursor = text_edit.textCursor()
        ln = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        bytes_cnt = len(text.encode('utf-8'))
        self.stats_lbl.setText(f"Ln {ln}, Col {col}    {bytes_cnt} Bytes")

    def _on_text_cursor_changed(self):
        text_edit = self.sender()
        if text_edit:
            self._update_stats(text_edit)

    def clear_preview_tabs(self):
        for w in self.preview_tab_widgets:
            idx = self.tabview.indexOf(w)
            if idx != -1:
                self.tabview.removeTab(idx)
            w.deleteLater()
        self.preview_tab_widgets.clear()
        self.right_stack.setCurrentIndex(0)

    def _close_preview_tab(self, index: int):
        widget = self.tabview.widget(index)
        if widget in self.preview_tab_widgets:
            self.preview_tab_widgets.remove(widget)
        self.tabview.removeTab(index)
        widget.deleteLater()
        if self.tabview.count() == 0:
            self.right_stack.setCurrentIndex(0)

    def _add_single_preview_tab(self, title_name: str, content: str) -> QWidget:
        # If a tab with the same title already exists, just update its content
        for i in range(self.tabview.count()):
            if self.tabview.tabText(i) == title_name:
                widget = self.tabview.widget(i)
                text_edit = widget.findChild(QTextEdit)
                if text_edit:
                    text_edit.setPlainText(content)
                    self._update_stats(text_edit)
                self.tabview.setCurrentIndex(i)
                return widget

        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(0, 5, 0, 0)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(False)
        text_edit.setLineWrapMode(QTextEdit.NoWrap)
        text_edit.setPlainText(content)
        
        font_c = text_edit.font()
        font_c.setFamily("Consolas")
        font_c.setPointSize(10)
        text_edit.setFont(font_c)
        text_edit.cursorPositionChanged.connect(self._on_text_cursor_changed)
        layout.addWidget(text_edit)

        new_idx = self.tabview.addTab(tab_widget, title_name)
        self.preview_tab_widgets.append(tab_widget)
        self.right_stack.setCurrentIndex(1)
        self._update_stats(text_edit)
        return tab_widget

    def _copy_current_tab(self):
        idx = self.tabview.currentIndex()
        if idx == -1:
            QMessageBox.warning(self, "Empty", "No document open to copy.")
            return
        widget = self.tabview.widget(idx)
        text_edit = widget.findChild(QTextEdit)
        if text_edit:
            text = text_edit.toPlainText()
            if text.strip():
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                self.btn_copy.setText("Copied")
                QTimer = __import__("PySide6.QtCore").QtCore.QTimer
                QTimer.singleShot(1500, lambda: self.btn_copy.setText("Copy"))

    def _handle_dropped_files(self, raw_paths):
        valid_files = []
        for path in raw_paths:
            if os.path.isfile(path):
                if self.engine.is_supported(path):
                    valid_files.append(path)
            elif os.path.isdir(path):
                for root, _, fnames in os.walk(path):
                    for fn in fnames:
                        fp = os.path.join(root, fn)
                        if self.engine.is_supported(fp):
                            valid_files.append(fp)
        if valid_files:
            for vf in valid_files:
                if vf not in self.selected_files:
                    self.selected_files.append(vf)
            self.update_graphical_file_queue()

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Convert", "",
            "All Supported Files (*.docx *.pptx *.xlsx *.xls *.pdf *.html *.xml *.json *.csv *.zip *.txt *.mp3 *.wav *.png *.jpg *.jpeg);;All Files (*.*)"
        )
        if files:
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.update_graphical_file_queue()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Convert")
        if folder:
            found_files = []
            for root, _, files in os.walk(folder):
                for f in files:
                    fp = os.path.join(root, f)
                    if self.engine.is_supported(fp):
                        found_files.append(fp)
            if found_files:
                for ff in found_files:
                    if ff not in self.selected_files:
                        self.selected_files.append(ff)
                self.update_graphical_file_queue()

    def browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.dest_entry.setText(folder)

    def remove_single_file(self, file_path: str):
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
            if file_path in self.converted_success_files:
                self.converted_success_files.remove(file_path)
            self.update_graphical_file_queue()

    def clear_all_files(self):
        self.selected_files.clear()
        self.converted_success_files.clear()
        self.update_graphical_file_queue()

    def update_graphical_file_queue(self):
        count = len(self.selected_files)
        self.lbl_queue.setText(f"QUEUE  {count}")
        self.drop_zone.update_list(self.selected_files, self.converted_success_files)
        self.status_label.setText(f"Status: Ready ({count} files)")

    def get_output_format_code(self):
        val = self.format_combo.currentText()
        if "Text" in val:
            return "txt"
        elif "HTML" in val:
            return "html"
        return "md"

    def start_conversion(self):
        if not self.selected_files:
            return

        out_dir = self.dest_entry.text().strip()
        auto_save = self.auto_save_switch.isChecked()
        fmt = self.get_output_format_code()

        self.btn_convert.setEnabled(False)
        self.btn_convert.setText("Converting...")
        
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        self.status_label.setText("Processing conversion...")

        if len(self.selected_files) == 1:
            file_path = self.selected_files[0]
            threading.Thread(
                target=self._run_single_thread, 
                args=(file_path, out_dir, fmt, auto_save), 
                daemon=True
            ).start()
        else:
            def on_progress(c, t, f, s):
                self.signals.batch_progress.emit(c, t, f, s)
                
            def on_complete(tasks):
                self.signals.batch_done.emit(tasks)
                
            self.engine.convert_batch_async(
                file_paths=self.selected_files,
                output_dir=out_dir if out_dir else os.path.dirname(self.selected_files[0]),
                output_format=fmt,
                on_progress=on_progress,
                on_complete=on_complete
            )

    def _run_single_thread(self, file_path, out_dir, fmt, auto_save):
        success, result_text = self.engine.convert_single_file(file_path)
        self.signals.single_done.emit(file_path, out_dir, fmt, auto_save, success, result_text)

    def _finish_single(self, file_path, out_dir, fmt, auto_save, success, result_text):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("Start Conversion")
        
        self.progress_bar.setValue(100)
        self.progress_bar.hide()

        if success:
            self.converted_success_files.add(file_path)
            self.update_graphical_file_queue()
            
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            formatted = self.engine.format_output(result_text, fmt, title=base_name)
            
            ext_map = {"md": ".md", "txt": ".txt", "html": ".html"}
            tab_title = f"{base_name}{ext_map.get(fmt, '.md')}"
            
            self._add_single_preview_tab(tab_title, formatted)
            self.tabview.setCurrentIndex(0)

            if auto_save:
                if not out_dir:
                    out_dir = os.path.dirname(file_path)
                ext_map = {"md": ".md", "txt": ".txt", "html": ".html"}
                out_path = os.path.join(out_dir, f"{base_name}{ext_map.get(fmt, '.md')}")
                try:
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(formatted)
                    self.status_label.setText(f"Status: Saved to {os.path.basename(out_path)}")
                except Exception as e:
                    self.status_label.setText(f"Status: Error saving file")
            else:
                self.status_label.setText("Status: Converted successfully")
        else:
            self.status_label.setText("Status: Conversion failed")
            QMessageBox.critical(self, "Conversion Error", result_text)

    def _update_progress_ui(self, current, total, filename, status):
        fraction = int((current / total) * 100)
        self.progress_bar.setValue(fraction)
        self.status_label.setText(f"Status: [{current}/{total}] {os.path.basename(filename)}")

    def _finish_batch(self, tasks):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("Start Conversion")
        
        self.progress_bar.setValue(100)
        self.progress_bar.hide()

        success_tasks = [t for t in tasks if t.status == "Success"]
        total = len(tasks)
        success_count = len(success_tasks)

        for t in success_tasks:
            self.converted_success_files.add(t.file_path)
            
        self.update_graphical_file_queue()

        self.status_label.setText(f"Status: Batch complete ({success_count}/{total})")
        
        fmt = self.get_output_format_code()
        ext_map = {"md": ".md", "txt": ".txt", "html": ".html"}
        
        for task in success_tasks:
            base_name = os.path.splitext(os.path.basename(task.file_path))[0]
            formatted = self.engine.format_output(task.result_text, fmt, title=base_name)
            tab_title = f"{base_name}{ext_map.get(fmt, '.md')}"
            self._add_single_preview_tab(tab_title, formatted)

        if success_tasks:
            self.tabview.setCurrentIndex(0)

def main():
    app = QApplication(sys.argv)
    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)
    
    window = MarkItDownGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
