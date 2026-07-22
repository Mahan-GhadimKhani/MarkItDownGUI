import os
import sys
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QCheckBox,
    QLineEdit, QProgressBar, QTabWidget, QTextEdit, QScrollArea,
    QFileDialog, QMessageBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QPalette, QColor, QFont, QGuiApplication, QClipboard

from converter_engine import MarkItDownEngine

# --- Threading Signals for UI Updates ---
class WorkerSignals(QObject):
    single_done = Signal(str, str, str, bool, bool, str)  # file_path, out_dir, fmt, auto_save, success, result_text
    batch_progress = Signal(int, int, str, str)  # current, total, filename, status
    batch_done = Signal(list)  # list of tasks

# --- Composite Drag & Drop Zone + Selected Files List ---
class DropZoneWidget(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("dropFrame")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Drag prompt label
        self.prompt_label = QLabel("📥 DRAG & DROP FILES HERE\n\n(Drop files or folders anywhere in this box)")
        self.prompt_label.setAlignment(Qt.AlignCenter)
        font = self.prompt_label.font()
        font.setPointSize(11)
        font.setBold(True)
        self.prompt_label.setFont(font)
        layout.addWidget(self.prompt_label)

        # Selected Files Header Bar inside DropZone
        self.files_header_layout = QHBoxLayout()
        self.files_count_lbl = QLabel("No files selected")
        self.files_header_layout.addWidget(self.files_count_lbl)
        self.files_header_layout.addStretch()

        self.btn_clear_queue = QPushButton("🗑️ Clear")
        self.btn_clear_queue.setObjectName("dangerBtn")
        self.btn_clear_queue.setToolTip("Clear all selected files")
        self.btn_clear_queue.setFixedSize(65, 26)
        self.btn_clear_queue.hide()
        self.files_header_layout.addWidget(self.btn_clear_queue)
        layout.addLayout(self.files_header_layout)

        # Scroll Area for Selected File Chips
        self.file_scroll = QScrollArea()
        self.file_scroll.setWidgetResizable(True)
        self.file_scroll.setMaximumHeight(160)
        self.file_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(4)
        self.scroll_layout.setAlignment(Qt.AlignTop)

        self.file_scroll.setWidget(self.scroll_content)
        layout.addWidget(self.file_scroll)
        
        self.update_theme(is_dark=True)

    def update_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._reset_style()
        if is_dark:
            self.prompt_label.setStyleSheet("color: #ccc; border: none; background: transparent;")
            self.files_count_lbl.setStyleSheet("color: #aaa; font-weight: bold; border: none; background: transparent;")
        else:
            self.prompt_label.setStyleSheet("color: #444; border: none; background: transparent;")
            self.files_count_lbl.setStyleSheet("color: #555; font-weight: bold; border: none; background: transparent;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            if self.is_dark:
                self.setStyleSheet("""
                    QFrame#dropFrame {
                        border: 2px dashed #4da6ff;
                        border-radius: 10px;
                        background-color: #1e3a5f;
                    }
                """)
            else:
                self.setStyleSheet("""
                    QFrame#dropFrame {
                        border: 2px dashed #007acc;
                        border-radius: 10px;
                        background-color: #e6f2ff;
                    }
                """)
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
        if getattr(self, "is_dark", True):
            self.setStyleSheet("""
                QFrame#dropFrame {
                    border: 2px dashed #555;
                    border-radius: 10px;
                    background-color: #2b2b2b;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#dropFrame {
                    border: 2px dashed #a0a0a0;
                    border-radius: 10px;
                    background-color: #f7f7f7;
                }
            """)


class MarkItDownGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microsoft MarkItDown - Desktop GUI")
        self.resize(1100, 750)
        self.setMinimumSize(950, 650)

        self.engine = MarkItDownEngine()
        self.selected_files = []
        self.converted_success_files = set()
        self.preview_tab_widgets = []
        self.is_dark = True

        # Setup Signals
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
        
        dark_bg = QColor(30, 30, 30)
        dark_text = QColor(240, 240, 240)
        
        palette.setColor(QPalette.Window, dark_bg)
        palette.setColor(QPalette.WindowText, dark_text)
        palette.setColor(QPalette.Base, QColor(40, 40, 40))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ToolTipBase, dark_text)
        palette.setColor(QPalette.ToolTipText, dark_bg)
        palette.setColor(QPalette.Text, dark_text)
        palette.setColor(QPalette.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ButtonText, dark_text)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        
        app.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QFrame { background-color: #252526; border-radius: 8px; }
            QLabel { color: #f0f0f0; }
            QCheckBox { color: #f0f0f0; }
            QPushButton { 
                background-color: #333337; border: 1px solid #555; 
                padding: 6px; border-radius: 4px; color: #fff;
            }
            QPushButton:hover { background-color: #3f3f46; }
            QPushButton#primaryBtn { 
                background-color: #007acc; border: none; font-weight: bold; font-size: 14px; color: #fff;
            }
            QPushButton#primaryBtn:hover { background-color: #0098ff; }
            QPushButton#dangerBtn { background-color: #cc3333; border: none; color: #fff; }
            QPushButton#dangerBtn:hover { background-color: #ff4d4d; }
            QPushButton#successBtn { background-color: #28a745; border: none; color: #fff; }
            QPushButton#successBtn:hover { background-color: #34d058; }
            QLineEdit, QComboBox, QTextEdit { 
                background-color: #3c3c3c; border: 1px solid #555; 
                color: #fff; padding: 4px; border-radius: 4px;
            }
            QTabWidget::pane { border: 1px solid #555; background: #252526; }
            QTabBar::tab { 
                background: #2d2d30; padding: 8px 16px; border: 1px solid #555; 
                border-bottom: none; color: #aaa;
            }
            QTabBar::tab:selected { background: #3c3c3c; color: #fff; }
            QProgressBar {
                border: 1px solid #555; border-radius: 4px; text-align: center;
                background-color: #2b2b2b; color: white;
            }
            QProgressBar::chunk { background-color: #007acc; width: 10px; }
            QLabel#headerLbl { font-size: 18px; font-weight: bold; color: #fff; }
            QLabel#subHeaderLbl { color: #aaa; }
            QLabel#statusLbl { color: #aaa; }
        """)
        if hasattr(self, "drop_zone"):
            self.drop_zone.update_theme(True)
            self.update_graphical_file_queue()

    def _apply_light_theme(self):
        self.is_dark = False
        app = QApplication.instance()
        palette = QPalette()
        app.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QFrame { background-color: #ffffff; border-radius: 8px; }
            QLabel { color: #111111; }
            QCheckBox { color: #111111; }
            QPushButton { 
                background-color: #e0e0e0; border: 1px solid #ccc; 
                padding: 6px; border-radius: 4px; color: #000;
            }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton#primaryBtn { 
                background-color: #007acc; border: none; color: #fff; font-weight: bold; font-size: 14px;
            }
            QPushButton#primaryBtn:hover { background-color: #0098ff; }
            QPushButton#dangerBtn { background-color: #cc3333; color: white; border: none; }
            QPushButton#dangerBtn:hover { background-color: #ff4d4d; }
            QPushButton#successBtn { background-color: #28a745; color: white; border: none; }
            QPushButton#successBtn:hover { background-color: #34d058; }
            QLineEdit, QComboBox, QTextEdit { 
                background-color: #ffffff; border: 1px solid #ccc; 
                color: #000; padding: 4px; border-radius: 4px;
            }
            QTabWidget::pane { border: 1px solid #ccc; background: #ffffff; }
            QTabBar::tab { 
                background: #f0f0f0; padding: 8px 16px; border: 1px solid #ccc; 
                border-bottom: none; color: #333;
            }
            QTabBar::tab:selected { background: #ffffff; color: #000; }
            QProgressBar {
                border: 1px solid #ccc; border-radius: 4px; text-align: center;
                background-color: #e0e0e0; color: black;
            }
            QProgressBar::chunk { background-color: #007acc; width: 10px; }
            QLabel#headerLbl { font-size: 18px; font-weight: bold; color: #000; }
            QLabel#subHeaderLbl { color: #666; }
            QLabel#statusLbl { color: #555; }
        """)
        if hasattr(self, "drop_zone"):
            self.drop_zone.update_theme(False)
            self.update_graphical_file_queue()

    def toggle_theme(self):
        if self.is_dark:
            self._apply_light_theme()
            self.theme_btn.setText("🌙 Dark Mode")
        else:
            self._apply_dark_theme()
            self.theme_btn.setText("☀️ Light Mode")

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ================= LEFT PANEL =================
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(12)

        # Header Row
        header_layout = QHBoxLayout()
        self.header_label = QLabel("MarkItDown Converter")
        self.header_label.setObjectName("headerLbl")
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        self.theme_btn = QPushButton("☀️ Light Mode")
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)
        left_layout.addLayout(header_layout)

        sub_header = QLabel("Convert Office, PDF, Audio, Images & HTML to Markdown")
        sub_header.setObjectName("subHeaderLbl")
        left_layout.addWidget(sub_header)

        # Settings
        fmt_label = QLabel("Output Format:")
        font_b = fmt_label.font()
        font_b.setBold(True)
        fmt_label.setFont(font_b)
        left_layout.addWidget(fmt_label)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["Markdown (.md)", "Plain Text (.txt)", "HTML (.html)"])
        left_layout.addWidget(self.format_combo)

        self.auto_save_check = QCheckBox("Auto-save converted files to output directory")
        left_layout.addWidget(self.auto_save_check)

        dest_layout = QHBoxLayout()
        self.dest_entry = QLineEdit()
        self.dest_entry.setPlaceholderText("Output Directory (Optional)")
        dest_layout.addWidget(self.dest_entry)
        btn_dest_browse = QPushButton("Browse")
        btn_dest_browse.clicked.connect(self.browse_output_dir)
        dest_layout.addWidget(btn_dest_browse)
        left_layout.addLayout(dest_layout)

        # File Select Buttons
        btn_layout = QHBoxLayout()
        btn_select_files = QPushButton("📁 Select Files")
        btn_select_files.clicked.connect(self.browse_files)
        btn_select_folder = QPushButton("📂 Select Folder")
        btn_select_folder.clicked.connect(self.browse_folder)
        btn_layout.addWidget(btn_select_files)
        btn_layout.addWidget(btn_select_folder)
        left_layout.addLayout(btn_layout)

        # Composite Drag & Drop Zone + Bottom Selected Files Mini-View
        self.drop_zone = DropZoneWidget()
        self.drop_zone.files_dropped.connect(self._handle_dropped_files)
        self.drop_zone.btn_clear_queue.clicked.connect(self.clear_all_files)
        left_layout.addWidget(self.drop_zone, stretch=1)

        # Convert Button
        self.btn_convert = QPushButton("🚀 Start Conversion")
        self.btn_convert.setObjectName("primaryBtn")
        self.btn_convert.setMinimumHeight(45)
        self.btn_convert.clicked.connect(self.start_conversion)
        left_layout.addWidget(self.btn_convert)

        # Progress Bar (HIDDEN BY DEFAULT)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLbl")
        self.status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_label)

        main_layout.addWidget(left_panel, stretch=4)

        # ================= RIGHT PANEL =================
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabview = QTabWidget()
        self.tabview.setTabsClosable(True)
        self.tabview.tabCloseRequested.connect(self._close_preview_tab)
        right_layout.addWidget(self.tabview)

        # Initial placeholder preview tab (Only Live Preview tabs exist in tabview)
        self._add_single_preview_tab("Live Preview", "")

        main_layout.addWidget(right_panel, stretch=6)
        self.update_graphical_file_queue()

    def clear_preview_tabs(self):
        """Remove all preview tabs from the TabWidget."""
        for w in self.preview_tab_widgets:
            idx = self.tabview.indexOf(w)
            if idx != -1:
                self.tabview.removeTab(idx)
            w.deleteLater()
        self.preview_tab_widgets.clear()

    def _close_preview_tab(self, index: int):
        """Close an individual preview tab by index."""
        widget = self.tabview.widget(index)
        if widget in self.preview_tab_widgets:
            self.preview_tab_widgets.remove(widget)
        self.tabview.removeTab(index)
        widget.deleteLater()

        # If all tabs closed, recreate default empty preview tab
        if self.tabview.count() == 0:
            self._add_single_preview_tab("Live Preview", "")

    def _add_single_preview_tab(self, title_name: str, content: str) -> QWidget:
        """Create and append a preview tab widget."""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(False)
        text_edit.setLineWrapMode(QTextEdit.NoWrap)
        text_edit.setPlainText(content)
        font_c = text_edit.font()
        font_c.setFamily("Consolas")
        font_c.setPointSize(10)
        text_edit.setFont(font_c)
        layout.addWidget(text_edit)

        btn_layout = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy Content")
        btn_copy.clicked.connect(lambda: self._copy_tab_content(text_edit))
        btn_layout.addWidget(btn_copy)

        btn_save = QPushButton("💾 Save Output...")
        btn_save.setObjectName("successBtn")
        btn_save.clicked.connect(lambda: self._save_tab_content(text_edit))
        btn_layout.addWidget(btn_save)
        
        btn_layout.addStretch()
        
        char_count = len(content)
        word_count = len(content.split())
        lbl_stats = QLabel(f"{char_count:,} Characters | {word_count:,} Words")
        lbl_stats.setStyleSheet("color: gray;")
        btn_layout.addWidget(lbl_stats)
        
        layout.addLayout(btn_layout)

        new_idx = self.tabview.addTab(tab_widget, f"📄 {title_name}")
        self.preview_tab_widgets.append(tab_widget)
        return tab_widget

    def _copy_tab_content(self, text_edit: QTextEdit):
        text = text_edit.toPlainText()
        if text.strip():
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Copied", "Content copied to clipboard!")
        else:
            QMessageBox.warning(self, "Empty", "There is no content to copy.")

    def _save_tab_content(self, text_edit: QTextEdit):
        text = text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Empty", "There is no content to save.")
            return

        fmt = self.get_output_format_code()
        ext_map = {"md": ("Markdown File (*.md)", ".md"), "txt": ("Text File (*.txt)", ".txt"), "html": ("HTML File (*.html)", ".html")}
        filter_str, default_ext = ext_map.get(fmt, ("Markdown File (*.md)", ".md"))
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Converted Document", "",
            f"{filter_str};;All Files (*.*)"
        )
        if filepath:
            if not filepath.endswith(default_ext) and "." not in os.path.basename(filepath):
                filepath += default_ext
                
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(text)
                QMessageBox.information(self, "Saved", f"Saved successfully to:\n{filepath}")
                self.status_label.setText(f"Saved to: {os.path.basename(filepath)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

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
            else:
                QMessageBox.information(self, "No Supported Files", "No supported files were found in the selected folder.")

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
        """Update the compact file list inside the bottom of the Drag & Drop widget with green highlights for success."""
        scroll_layout = self.drop_zone.scroll_layout
        
        # Clear previous chips
        while scroll_layout.count():
            item = scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        is_dark = getattr(self, "is_dark", True)
        count = len(self.selected_files)
        if count == 0:
            self.drop_zone.prompt_label.setText("📥 DRAG & DROP FILES HERE\n\n(Drop files or folders anywhere in this box)")
            self.drop_zone.files_count_lbl.setText("No files selected")
            self.drop_zone.btn_clear_queue.hide()
            
            empty_lbl = QLabel("No files added yet.")
            if is_dark:
                empty_lbl.setStyleSheet("color: #666; font-style: italic; border: none; background: transparent;")
            else:
                empty_lbl.setStyleSheet("color: #888; font-style: italic; border: none; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(empty_lbl)
            return

        self.drop_zone.prompt_label.setText(f"✅ {count} File(s) Selected")
        self.drop_zone.files_count_lbl.setText(f"Files in Queue ({count}):")
        self.drop_zone.btn_clear_queue.show()

        for idx, file_path in enumerate(self.selected_files, start=1):
            is_success = file_path in self.converted_success_files
            
            item_frame = QFrame()
            if is_success:
                if is_dark:
                    item_frame.setStyleSheet("""
                        QFrame {
                            border: 1px solid #28a745;
                            border-radius: 6px;
                            background-color: #1e3d29;
                        }
                    """)
                else:
                    item_frame.setStyleSheet("""
                        QFrame {
                            border: 1px solid #28a745;
                            border-radius: 6px;
                            background-color: #d4edda;
                        }
                    """)
            else:
                if is_dark:
                    item_frame.setStyleSheet("""
                        QFrame {
                            border: 1px solid #444;
                            border-radius: 6px;
                            background-color: #333;
                        }
                    """)
                else:
                    item_frame.setStyleSheet("""
                        QFrame {
                            border: 1px solid #ccc;
                            border-radius: 6px;
                            background-color: #ffffff;
                        }
                    """)
            
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(8, 4, 8, 4)
            item_layout.setSpacing(6)
            
            fname = os.path.basename(file_path)
            ext = os.path.splitext(fname)[1].upper().replace(".", "")
            
            status_icon = "✅ " if is_success else ""
            lbl_name = QLabel(f"{idx}. {status_icon}[{ext}] {fname}")
            font = lbl_name.font()
            font.setBold(True)
            lbl_name.setFont(font)
            
            if is_success:
                if is_dark:
                    lbl_name.setStyleSheet("border: none; background: transparent; color: #4cd97b;")
                else:
                    lbl_name.setStyleSheet("border: none; background: transparent; color: #155724;")
            else:
                if is_dark:
                    lbl_name.setStyleSheet("border: none; background: transparent; color: #eee;")
                else:
                    lbl_name.setStyleSheet("border: none; background: transparent; color: #222;")
                    
            lbl_name.setToolTip(file_path)
            item_layout.addWidget(lbl_name, stretch=1)

            btn_remove = QPushButton("❌")
            btn_remove.setObjectName("dangerBtn")
            btn_remove.setFixedSize(24, 24)
            btn_remove.setToolTip("Remove file")
            btn_remove.clicked.connect(lambda checked=False, fp=file_path: self.remove_single_file(fp))
            item_layout.addWidget(btn_remove)
            
            scroll_layout.addWidget(item_frame)

    def get_output_format_code(self):
        val = self.format_combo.currentText()
        if "Text" in val:
            return "txt"
        elif "HTML" in val:
            return "html"
        return "md"

    def start_conversion(self):
        if not self.selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select or drop at least one supported file first.")
            return

        out_dir = self.dest_entry.text().strip()
        auto_save = self.auto_save_check.isChecked()
        fmt = self.get_output_format_code()

        self.btn_convert.setEnabled(False)
        self.btn_convert.setText("⏳ Converting...")
        
        # Show & reset Progress Bar ONLY during conversion
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
        self.btn_convert.setText("🚀 Start Conversion")
        
        # Hide Progress Bar after conversion completes
        self.progress_bar.setValue(100)
        self.progress_bar.hide()

        if success:
            self.converted_success_files.add(file_path)
            self.update_graphical_file_queue()
            
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            formatted = self.engine.format_output(result_text, fmt, title=base_name)
            
            # Clear old tabs and add new tab for this file
            self.clear_preview_tabs()
            self._add_single_preview_tab(os.path.basename(file_path), formatted)
            self.tabview.setCurrentIndex(0)

            if auto_save:
                if not out_dir:
                    out_dir = os.path.dirname(file_path)
                ext_map = {"md": ".md", "txt": ".txt", "html": ".html"}
                out_path = os.path.join(out_dir, f"{base_name}{ext_map.get(fmt, '.md')}")
                try:
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(formatted)
                    self.status_label.setText(f"Converted & saved to: {os.path.basename(out_path)}")
                    QMessageBox.information(self, "Success", f"Conversion completed!\nFile saved to:\n{out_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error Saving File", str(e))
            else:
                self.status_label.setText("Converted successfully! Output shown in Live Preview.")
                QMessageBox.information(self, "Conversion Complete", "File converted successfully!\nCheck the preview tab and click 'Save Output...' when ready.")
        else:
            self.status_label.setText("Conversion failed!")
            QMessageBox.critical(self, "Conversion Error", result_text)

    def _update_progress_ui(self, current, total, filename, status):
        fraction = int((current / total) * 100)
        self.progress_bar.setValue(fraction)
        self.status_label.setText(f"[{current}/{total}] {filename} ({status})")

    def _finish_batch(self, tasks):
        self.btn_convert.setEnabled(True)
        self.btn_convert.setText("🚀 Start Conversion")
        
        # Hide Progress Bar after batch conversion completes
        self.progress_bar.setValue(100)
        self.progress_bar.hide()

        success_tasks = [t for t in tasks if t.status == "Success"]
        total = len(tasks)
        success_count = len(success_tasks)

        for t in success_tasks:
            self.converted_success_files.add(t.file_path)
            
        self.update_graphical_file_queue()

        self.status_label.setText(f"Batch complete: {success_count}/{total} files processed.")
        
        # Clear existing tabs and populate a tab for EACH converted file
        self.clear_preview_tabs()
        for task in success_tasks:
            fname = os.path.basename(task.file_path)
            self._add_single_preview_tab(fname, task.result_text)

        if success_tasks:
            self.tabview.setCurrentIndex(0)

        QMessageBox.information(
            self, "Batch Conversion Complete", 
            f"Successfully processed {success_count} out of {total} files.\nEach document has been opened in its own Live Preview tab on the right."
        )

def main():
    app = QApplication(sys.argv)
    
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    
    window = MarkItDownGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
