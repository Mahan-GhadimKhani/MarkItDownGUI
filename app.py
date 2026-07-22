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

# --- Drag & Drop Label Component ---
class DropZoneLabel(QLabel):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setText("📥 DRAG & DROP FILES HERE\n\n(Drop files or folders anywhere in this box)")
        font = self.font()
        font.setPointSize(12)
        font.setBold(True)
        self.setFont(font)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #555;
                border-radius: 10px;
                background-color: #2b2b2b;
                color: #ccc;
            }
        """)
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #4da6ff;
                    border-radius: 10px;
                    background-color: #1e3a5f;
                    color: #fff;
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
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #555;
                border-radius: 10px;
                background-color: #2b2b2b;
                color: #ccc;
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
        self.current_converted_text = ""

        # Setup Signals
        self.signals = WorkerSignals()
        self.signals.single_done.connect(self._finish_single)
        self.signals.batch_progress.connect(self._update_progress_ui)
        self.signals.batch_done.connect(self._finish_batch)

        self._apply_dark_theme()
        self._build_ui()

    def _apply_dark_theme(self):
        self.is_dark = True
        app = QApplication.instance()
        palette = QPalette()
        
        # Base colors
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
        
        # General StyleSheet
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QFrame { background-color: #252526; border-radius: 8px; }
            QPushButton { 
                background-color: #333337; border: 1px solid #555; 
                padding: 6px; border-radius: 4px; color: #fff;
            }
            QPushButton:hover { background-color: #3f3f46; }
            QPushButton#primaryBtn { 
                background-color: #007acc; border: none; font-weight: bold; font-size: 14px;
            }
            QPushButton#primaryBtn:hover { background-color: #0098ff; }
            QPushButton#dangerBtn { background-color: #cc3333; border: none; }
            QPushButton#dangerBtn:hover { background-color: #ff4d4d; }
            QPushButton#successBtn { background-color: #28a745; border: none; }
            QPushButton#successBtn:hover { background-color: #34d058; }
            QLineEdit, QComboBox, QTextEdit { 
                background-color: #3c3c3c; border: 1px solid #555; 
                color: #fff; padding: 4px; border-radius: 4px;
            }
            QTabWidget::pane { border: 1px solid #555; background: #252526; }
            QTabBar::tab { 
                background: #2d2d30; padding: 8px 20px; border: 1px solid #555; 
                border-bottom: none; color: #aaa;
            }
            QTabBar::tab:selected { background: #3c3c3c; color: #fff; }
            QProgressBar {
                border: 1px solid #555; border-radius: 4px; text-align: center;
                background-color: #2b2b2b; color: white;
            }
            QProgressBar::chunk { background-color: #007acc; width: 10px; }
            QLabel#headerLbl { font-size: 18px; font-weight: bold; }
        """)

    def _apply_light_theme(self):
        self.is_dark = False
        app = QApplication.instance()
        palette = QPalette()
        app.setPalette(palette)  # Reset to default light
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QFrame { background-color: #ffffff; border-radius: 8px; }
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
                background: #f0f0f0; padding: 8px 20px; border: 1px solid #ccc; 
                border-bottom: none; color: #333;
            }
            QTabBar::tab:selected { background: #ffffff; color: #000; }
            QProgressBar {
                border: 1px solid #ccc; border-radius: 4px; text-align: center;
                background-color: #e0e0e0; color: black;
            }
            QProgressBar::chunk { background-color: #007acc; width: 10px; }
            QLabel#headerLbl { font-size: 18px; font-weight: bold; color: black; }
        """)

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
        sub_header.setStyleSheet("color: gray;")
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

        # Drag & Drop Zone
        self.drop_zone = DropZoneLabel()
        self.drop_zone.files_dropped.connect(self._handle_dropped_files)
        left_layout.addWidget(self.drop_zone, stretch=1)

        # Convert Button
        self.btn_convert = QPushButton("🚀 Start Conversion")
        self.btn_convert.setObjectName("primaryBtn")
        self.btn_convert.setMinimumHeight(45)
        self.btn_convert.clicked.connect(self.start_conversion)
        left_layout.addWidget(self.btn_convert)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: gray;")
        left_layout.addWidget(self.status_label)

        main_layout.addWidget(left_panel, stretch=4)

        # ================= RIGHT PANEL =================
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabview = QTabWidget()
        right_layout.addWidget(self.tabview)

        # Tab 1: Live Preview
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(False)
        self.preview_text.setLineWrapMode(QTextEdit.NoWrap)
        font_c = self.preview_text.font()
        font_c.setFamily("Consolas")
        font_c.setPointSize(10)
        self.preview_text.setFont(font_c)
        preview_layout.addWidget(self.preview_text)

        preview_btn_layout = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy Content")
        btn_copy.clicked.connect(self.copy_preview_content)
        preview_btn_layout.addWidget(btn_copy)

        btn_save = QPushButton("💾 Save Output...")
        btn_save.setObjectName("successBtn")
        btn_save.clicked.connect(self.save_preview_content)
        preview_btn_layout.addWidget(btn_save)
        
        preview_btn_layout.addStretch()
        
        self.info_stats_label = QLabel("0 Characters | 0 Words")
        self.info_stats_label.setStyleSheet("color: gray;")
        preview_btn_layout.addWidget(self.info_stats_label)
        
        preview_layout.addLayout(preview_btn_layout)
        self.tabview.addTab(preview_tab, "📄 Live Preview")

        # Tab 2: Queue
        queue_tab = QWidget()
        queue_layout = QVBoxLayout(queue_tab)
        
        qheader_layout = QHBoxLayout()
        self.queue_count_label = QLabel("No files selected")
        font_b2 = self.queue_count_label.font()
        font_b2.setBold(True)
        self.queue_count_label.setFont(font_b2)
        qheader_layout.addWidget(self.queue_count_label)
        qheader_layout.addStretch()
        btn_clear = QPushButton("🗑️ Clear All")
        btn_clear.setObjectName("dangerBtn")
        btn_clear.clicked.connect(self.clear_all_files)
        qheader_layout.addWidget(btn_clear)
        queue_layout.addLayout(qheader_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_widget)
        queue_layout.addWidget(self.scroll_area)
        
        self.tabview.addTab(queue_tab, "📋 Selected Files")

        main_layout.addWidget(right_panel, stretch=6)
        
        self.update_graphical_file_queue()

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
            self.update_graphical_file_queue()

    def clear_all_files(self):
        self.selected_files.clear()
        self.update_graphical_file_queue()

    def update_graphical_file_queue(self):
        # Clear layout
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        count = len(self.selected_files)
        if count == 0:
            self.drop_zone.setText("📥 DRAG & DROP FILES HERE\n\n(Drop files or folders anywhere in this box)")
            self.queue_count_label.setText("No files selected")
            empty_lbl = QLabel("No files added yet. Drag and drop or click 'Select Files'.")
            empty_lbl.setStyleSheet("color: gray;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(empty_lbl)
            return

        self.drop_zone.setText(f"✅ {count} File(s) Selected\n\nDrag more files here or click Start Conversion")
        self.queue_count_label.setText(f"Files in Queue: {count}")

        for idx, file_path in enumerate(self.selected_files, start=1):
            item_frame = QFrame()
            item_frame.setStyleSheet("QFrame { border: 1px solid #555; background-color: transparent; }")
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(10, 5, 10, 5)
            
            fname = os.path.basename(file_path)
            ext = os.path.splitext(fname)[1].upper()
            
            lbl_name = QLabel(f"{idx}. [{ext}] {fname}")
            font = lbl_name.font()
            font.setBold(True)
            lbl_name.setFont(font)
            lbl_name.setStyleSheet("border: none;")
            item_layout.addWidget(lbl_name, stretch=1)

            btn_remove = QPushButton("❌")
            btn_remove.setObjectName("dangerBtn")
            btn_remove.setFixedSize(30, 30)
            # Use default arguments trick for lambda in loop
            btn_remove.clicked.connect(lambda checked=False, fp=file_path: self.remove_single_file(fp))
            item_layout.addWidget(btn_remove)
            
            self.scroll_layout.addWidget(item_frame)

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
        self.progress_bar.setValue(0)
        self.status_label.setText("Processing conversion...")

        if len(self.selected_files) == 1:
            # Single file conversion in thread
            file_path = self.selected_files[0]
            threading.Thread(
                target=self._run_single_thread, 
                args=(file_path, out_dir, fmt, auto_save), 
                daemon=True
            ).start()
        else:
            # Batch conversion natively asynchronous via converter_engine
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
        self.progress_bar.setValue(100)

        if success:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            formatted = self.engine.format_output(result_text, fmt, title=base_name)
            self.current_converted_text = formatted
            self.show_preview(formatted)
            
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
                QMessageBox.information(self, "Conversion Complete", "File converted successfully!\nCheck the 'Live Preview' tab and click 'Save Output...' when ready.")
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
        self.progress_bar.setValue(100)

        success_count = sum(1 for t in tasks if t.status == "Success")
        total = len(tasks)

        self.status_label.setText(f"Batch complete: {success_count}/{total} files processed.")
        
        first_success = next((t for t in tasks if t.status == "Success"), None)
        if first_success:
            self.current_converted_text = first_success.result_text
            self.show_preview(first_success.result_text)

        QMessageBox.information(
            self, "Batch Conversion Complete", 
            f"Successfully processed {success_count} out of {total} files.\nPreview of the first document is displayed on the right."
        )

    def show_preview(self, text: str):
        self.tabview.setCurrentIndex(0)
        self.preview_text.setPlainText(text)

        char_count = len(text)
        word_count = len(text.split())
        self.info_stats_label.setText(f"{char_count:,} Characters | {word_count:,} Words")

    def copy_preview_content(self):
        text = self.preview_text.toPlainText()
        if text.strip():
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Copied", "Converted content copied to clipboard!")
        else:
            QMessageBox.warning(self, "Empty", "There is no content to copy.")

    def save_preview_content(self):
        text = self.preview_text.toPlainText()
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

def main():
    app = QApplication(sys.argv)
    
    # Modern font
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)
    
    window = MarkItDownGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
