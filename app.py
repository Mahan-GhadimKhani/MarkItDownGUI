import os
import sys
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Try importing TkinterDnD2 for drag and drop support
HAS_DND = False
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    TkinterDnD = None

from converter_engine import MarkItDownEngine, ConversionTask, SUPPORTED_EXTENSIONS

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MarkItDownGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        if HAS_DND:
            try:
                TkinterDnD._require(self)
            except Exception:
                pass

        self.title("Microsoft MarkItDown - Desktop GUI")
        self.geometry("1100x750")
        self.minsize(950, 650)

        self.engine = MarkItDownEngine()
        self.selected_files = []
        self.output_dir = ""
        self.current_converted_text = ""

        self._build_ui()
        self._setup_drag_and_drop()

    def _build_ui(self):
        # Grid layout: 2 columns (Left: Options, Drop Zone & Action, Right: Preview & Graphical Queue)
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(0, weight=1)

        # ================= LEFT PANEL =================
        self.left_frame = ctk.CTkFrame(self, corner_radius=12)
        self.left_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        # Top Header Bar with Theme Switcher
        self.top_header_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.top_header_frame.pack(padx=20, pady=(15, 5), fill="x")

        self.header_label = ctk.CTkLabel(
            self.top_header_frame, 
            text="MarkItDown Converter", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.header_label.pack(side="left")

        # Dark Mode Switcher (Moved to TOP of page)
        self.theme_switch = ctk.CTkSwitch(
            self.top_header_frame, 
            text="Dark", 
            command=self.toggle_theme,
            width=60
        )
        self.theme_switch.select()
        self.theme_switch.pack(side="right")

        self.sub_header = ctk.CTkLabel(
            self.left_frame,
            text="Convert Office, PDF, Audio, Images & HTML to Markdown",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.sub_header.pack(padx=20, pady=(0, 10), anchor="w")

        # Output Format Selector Group (Dropdown / OptionMenu)
        self.settings_group = ctk.CTkFrame(self.left_frame, corner_radius=10)
        self.settings_group.pack(padx=20, pady=10, fill="x")

        self.fmt_label = ctk.CTkLabel(
            self.settings_group, 
            text="Output Format:", 
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.fmt_label.pack(anchor="w", padx=15, pady=(10, 2))

        self.format_optionmenu = ctk.CTkOptionMenu(
            self.settings_group,
            values=["Markdown (.md)", "Plain Text (.txt)", "HTML (.html)"],
            height=34
        )
        self.format_optionmenu.set("Markdown (.md)")
        self.format_optionmenu.pack(padx=15, pady=(0, 10), fill="x")

        # Auto-Save Checkbox (Optional Saving)
        self.auto_save_var = ctk.BooleanVar(value=False)
        self.auto_save_checkbox = ctk.CTkCheckBox(
            self.settings_group,
            text="Auto-save converted files to output directory",
            variable=self.auto_save_var,
            font=ctk.CTkFont(size=12)
        )
        self.auto_save_checkbox.pack(anchor="w", padx=15, pady=(0, 10))

        # Destination Directory Frame
        self.dest_frame = ctk.CTkFrame(self.settings_group, fg_color="transparent")
        self.dest_frame.pack(padx=15, pady=(0, 10), fill="x")

        self.dest_entry = ctk.CTkEntry(
            self.dest_frame, 
            placeholder_text="Output Directory (Optional)",
            height=32
        )
        self.dest_entry.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_dest_browse = ctk.CTkButton(
            self.dest_frame, 
            text="Browse", 
            width=70, 
            height=32,
            command=self.browse_output_dir
        )
        self.btn_dest_browse.pack(side="right")

        # File Selection Buttons
        self.btn_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.btn_frame.pack(padx=20, pady=5, fill="x")

        self.btn_select_files = ctk.CTkButton(
            self.btn_frame,
            text="📁 Select Files",
            command=self.browse_files,
            height=36
        )
        self.btn_select_files.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_select_folder = ctk.CTkButton(
            self.btn_frame,
            text="📂 Select Folder",
            command=self.browse_folder,
            fg_color=("gray60", "gray40"),
            hover_color=("gray50", "gray30"),
            height=36
        )
        self.btn_select_folder.pack(side="right", expand=True, fill="x", padx=(5, 0))

        # Larger Drag & Drop Placeholder Frame (Positioned lower, right above Convert)
        self.drop_frame = ctk.CTkFrame(
            self.left_frame, 
            fg_color=("gray85", "gray20"),
            border_width=2,
            border_color=("gray70", "gray35"),
            corner_radius=12
        )
        self.drop_frame.pack(padx=20, pady=(15, 10), fill="both", expand=True)

        self.drop_label = ctk.CTkLabel(
            self.drop_frame,
            text="📥 DRAG & DROP FILES HERE\n\n(Drop files/folders anywhere in this box)",
            font=ctk.CTkFont(size=14, weight="bold"),
            justify="center"
        )
        self.drop_label.pack(fill="both", expand=True, padx=20, pady=20)

        # Action Convert Button (Positioned at bottom)
        self.btn_convert = ctk.CTkButton(
            self.left_frame,
            text="🚀 Start Conversion",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=48,
            fg_color="#1f6aa5",
            hover_color="#144870",
            command=self.start_conversion
        )
        self.btn_convert.pack(padx=20, pady=(5, 10), fill="x")

        # Progress Bar & Status
        self.progress_bar = ctk.CTkProgressBar(self.left_frame)
        self.progress_bar.pack(padx=20, pady=(0, 5), fill="x")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            self.left_frame, 
            text="Ready", 
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(padx=20, pady=(0, 15))

        # ================= RIGHT PANEL =================
        self.right_frame = ctk.CTkFrame(self, corner_radius=12)
        self.right_frame.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")

        # Tabview for Live Preview and Graphical Queue List
        self.tabview = ctk.CTkTabview(self.right_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_preview = self.tabview.add("📄 Live Preview")
        self.tab_queue = self.tabview.add("📋 Selected Files")

        # Tab 1: Preview Text Box
        self.preview_textbox = ctk.CTkTextbox(
            self.tab_preview, 
            font=ctk.CTkFont(family="Consolas", size=13),
            wrap="none"
        )
        self.preview_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        # Action Buttons below Preview (Save As is optional!)
        self.preview_btn_frame = ctk.CTkFrame(self.tab_preview, fg_color="transparent")
        self.preview_btn_frame.pack(fill="x", padx=5, pady=(5, 0))

        self.btn_copy = ctk.CTkButton(
            self.preview_btn_frame,
            text="📋 Copy Content",
            width=120,
            command=self.copy_preview_content
        )
        self.btn_copy.pack(side="left", padx=5)

        self.btn_save_as = ctk.CTkButton(
            self.preview_btn_frame,
            text="💾 Save Output...",
            width=120,
            fg_color="#27ae60",
            hover_color="#1e8449",
            command=self.save_preview_content
        )
        self.btn_save_as.pack(side="left", padx=5)

        self.info_stats_label = ctk.CTkLabel(
            self.preview_btn_frame,
            text="0 Characters | 0 Words",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.info_stats_label.pack(side="right", padx=10)

        # Tab 2: Graphical File List (Scrollable Frame with Remove Buttons)
        self.queue_header_frame = ctk.CTkFrame(self.tab_queue, fg_color="transparent")
        self.queue_header_frame.pack(fill="x", padx=5, pady=5)

        self.queue_count_label = ctk.CTkLabel(
            self.queue_header_frame,
            text="No files selected",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.queue_count_label.pack(side="left", padx=5)

        self.btn_clear_all = ctk.CTkButton(
            self.queue_header_frame,
            text="🗑️ Clear All",
            width=90,
            height=28,
            fg_color="#c0392b",
            hover_color="#962d22",
            command=self.clear_all_files
        )
        self.btn_clear_all.pack(side="right", padx=5)

        self.queue_scrollable_frame = ctk.CTkScrollableFrame(
            self.tab_queue,
            label_text="Queued Files (Click ❌ to remove individual files)"
        )
        self.queue_scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def _setup_drag_and_drop(self):
        if HAS_DND:
            try:
                self.drop_frame.drop_target_register(DND_FILES)
                self.drop_frame.dnd_bind('<<Drop>>', self._on_drop_files)
                self.drop_label.drop_target_register(DND_FILES)
                self.drop_label.dnd_bind('<<Drop>>', self._on_drop_files)
            except Exception as e:
                print("Drag & Drop initialization note:", e)

    def _on_drop_files(self, event):
        files_str = event.data
        raw_files = self.split_dnd_paths(files_str)
        valid_files = []
        for path in raw_files:
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

    @staticmethod
    def split_dnd_paths(data_str: str):
        if not data_str or not isinstance(data_str, str):
            return []
        import re
        paths = re.findall(r'\{[^}]+\}|[^\s]+', data_str)
        cleaned = [p.strip('{}').strip() for p in paths]
        return [p for p in cleaned if p]

    def browse_files(self):
        filetypes = [
            ("All Supported Files", "*.docx *.pptx *.xlsx *.xls *.pdf *.html *.xml *.json *.csv *.zip *.txt *.mp3 *.wav *.png *.jpg *.jpeg"),
            ("Office Documents", "*.docx *.pptx *.xlsx *.xls"),
            ("PDF Files", "*.pdf"),
            ("Audio Files", "*.mp3 *.wav *.m4a"),
            ("Images", "*.png *.jpg *.jpeg"),
            ("All Files", "*.*")
        ]
        files = filedialog.askopenfilenames(title="Select Files to Convert", filetypes=filetypes)
        if files:
            for f in files:
                if f not in self.selected_files:
                    self.selected_files.append(f)
            self.update_graphical_file_queue()

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Folder to Convert")
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
                messagebox.showinfo("No Supported Files", "No supported files were found in the selected folder.")

    def browse_output_dir(self):
        folder = filedialog.askdirectory(title="Select Output Directory")
        if folder:
            self.output_dir = folder
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, folder)

    def remove_single_file(self, file_path: str):
        """Remove an individual file from the graphical file queue."""
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
            self.update_graphical_file_queue()

    def clear_all_files(self):
        """Clear all selected files from queue."""
        self.selected_files.clear()
        self.update_graphical_file_queue()

    def update_graphical_file_queue(self):
        """Render graphical cards for each file in the scrollable queue frame."""
        for widget in self.queue_scrollable_frame.winfo_children():
            widget.destroy()

        count = len(self.selected_files)
        if count == 0:
            self.drop_label.configure(
                text="📥 DRAG & DROP FILES HERE\n\n(Drop files/folders anywhere in this box)"
            )
            self.queue_count_label.configure(text="No files selected")
            empty_lbl = ctk.CTkLabel(
                self.queue_scrollable_frame, 
                text="No files added yet. Drag and drop or click 'Select Files'.",
                text_color="gray"
            )
            empty_lbl.pack(pady=30)
            return

        self.drop_label.configure(
            text=f"✅ {count} File(s) Selected\n\nDrag more files here or click Start Conversion"
        )
        self.queue_count_label.configure(text=f"Files in Queue: {count}")

        for idx, file_path in enumerate(self.selected_files, start=1):
            item_frame = ctk.CTkFrame(self.queue_scrollable_frame, corner_radius=8)
            item_frame.pack(fill="x", padx=5, pady=4)

            # Icon & Filename
            fname = os.path.basename(file_path)
            ext = os.path.splitext(fname)[1].upper()
            
            lbl_name = ctk.CTkLabel(
                item_frame, 
                text=f"{idx}. [{ext}] {fname}",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w"
            )
            lbl_name.pack(side="left", padx=10, pady=8, expand=True, fill="x")

            # Remove Button for each file
            btn_remove = ctk.CTkButton(
                item_frame,
                text="❌",
                width=32,
                height=28,
                fg_color="#c0392b",
                hover_color="#962d22",
                command=lambda fp=file_path: self.remove_single_file(fp)
            )
            btn_remove.pack(side="right", padx=8, pady=4)

    def get_output_format_code(self):
        val = self.format_optionmenu.get()
        if "Text" in val:
            return "txt"
        elif "HTML" in val:
            return "html"
        return "md"

    def start_conversion(self):
        if not self.selected_files:
            messagebox.showwarning("No Files Selected", "Please select or drop at least one supported file first.")
            return

        out_dir = self.dest_entry.get().strip()
        auto_save = self.auto_save_var.get()
        fmt = self.get_output_format_code()

        self.btn_convert.configure(state="disabled", text="⏳ Converting...")
        self.progress_bar.set(0)
        self.status_label.configure(text="Processing conversion...")

        if len(self.selected_files) == 1:
            threading.Thread(
                target=self._convert_single, 
                args=(self.selected_files[0], out_dir, fmt, auto_save), 
                daemon=True
            ).start()
        else:
            self.engine.convert_batch_async(
                file_paths=self.selected_files,
                output_dir=out_dir if out_dir else os.path.dirname(self.selected_files[0]),
                output_format=fmt,
                on_progress=self._on_batch_progress,
                on_complete=self._on_batch_complete
            )

    def _convert_single(self, file_path: str, out_dir: str, fmt: str, auto_save: bool):
        success, result_text = self.engine.convert_single_file(file_path)
        self.after(0, self._finish_single, file_path, out_dir, fmt, auto_save, success, result_text)

    def _finish_single(self, file_path: str, out_dir: str, fmt: str, auto_save: bool, success: bool, result_text: str):
        self.btn_convert.configure(state="normal", text="🚀 Start Conversion")
        self.progress_bar.set(1.0)

        if success:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            formatted = self.engine.format_output(result_text, fmt, title=base_name)
            self.current_converted_text = formatted
            
            # Show Live Preview
            self.show_preview(formatted)
            
            if auto_save:
                if not out_dir:
                    out_dir = os.path.dirname(file_path)
                ext_map = {"md": ".md", "txt": ".txt", "html": ".html"}
                out_path = os.path.join(out_dir, f"{base_name}{ext_map.get(fmt, '.md')}")
                try:
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(formatted)
                    self.status_label.configure(text=f"Converted & saved to: {os.path.basename(out_path)}")
                    messagebox.showinfo("Success", f"Conversion completed!\nFile saved to:\n{out_path}")
                except Exception as e:
                    messagebox.showerror("Error Saving File", str(e))
            else:
                self.status_label.configure(text="Converted successfully! Output shown in Live Preview. Click 'Save Output...' to save.")
                messagebox.showinfo("Conversion Complete", "File converted successfully!\nCheck the 'Live Preview' tab and click 'Save Output...' whenever you are ready to save.")
        else:
            self.status_label.configure(text="Conversion failed!")
            messagebox.showerror("Conversion Error", result_text)

    def _on_batch_progress(self, current: int, total: int, filename: str, status: str):
        fraction = current / total
        self.after(0, self._update_progress_ui, fraction, f"[{current}/{total}] {filename} ({status})")

    def _update_progress_ui(self, fraction: float, status_text: str):
        self.progress_bar.set(fraction)
        self.status_label.configure(text=status_text)

    def _on_batch_complete(self, tasks):
        self.after(0, self._finish_batch, tasks)

    def _finish_batch(self, tasks):
        self.btn_convert.configure(state="normal", text="🚀 Start Conversion")
        self.progress_bar.set(1.0)

        success_count = sum(1 for t in tasks if t.status == "Success")
        total = len(tasks)

        self.status_label.configure(text=f"Batch complete: {success_count}/{total} files processed.")
        
        # Show first success preview
        first_success = next((t for t in tasks if t.status == "Success"), None)
        if first_success:
            self.current_converted_text = first_success.result_text
            self.show_preview(first_success.result_text)

        messagebox.showinfo(
            "Batch Conversion Complete", 
            f"Successfully processed {success_count} out of {total} files.\nPreview of the first document is displayed on the right."
        )

    def show_preview(self, text: str):
        self.tabview.set("📄 Live Preview")
        self.preview_textbox.delete("1.0", "end")
        self.preview_textbox.insert("1.0", text)

        char_count = len(text)
        word_count = len(text.split())
        self.info_stats_label.configure(text=f"{char_count:,} Characters | {word_count:,} Words")

    def copy_preview_content(self):
        text = self.preview_textbox.get("1.0", "end-1c")
        if text.strip():
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Converted content copied to clipboard!")
        else:
            messagebox.showwarning("Empty", "There is no content to copy.")

    def save_preview_content(self):
        text = self.preview_textbox.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showwarning("Empty", "There is no content to save.")
            return

        fmt = self.get_output_format_code()
        ext_map = {"md": ("Markdown File", "*.md"), "txt": ("Text File", "*.txt"), "html": ("HTML File", "*.html")}
        default_ext = f".{fmt}"
        
        filepath = filedialog.asksaveasfilename(
            title="Save Converted Document",
            defaultextension=default_ext,
            filetypes=[ext_map.get(fmt, ("Markdown File", "*.md")), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo("Saved", f"Saved successfully to:\n{filepath}")
                self.status_label.configure(text=f"Saved to: {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")

    def toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")


def main():
    app = MarkItDownGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
