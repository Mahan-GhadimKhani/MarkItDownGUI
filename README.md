<img width="1280" height="640" alt="MarkItDownGUI-banner" src="https://github.com/user-attachments/assets/dd94e8ed-470a-4a37-a2bc-f2a3d46c0fc9" />

# MarkItDown GUI

A modern, fast, and feature-rich graphical user interface for converting various file formats (Office, PDF, Images, etc.) into clean Markdown or HTML. Powered by Microsoft's MarkItDown and a beautifully crafted PySide6 (Qt) interface.

## Features

- **Multi-format Support**: Convert `.docx`, `.pptx`, `.xlsx`, `.pdf`, `.html`, `.csv`, `.json`, `.xml`, `.zip`, `.txt`, `.mp3`, `.wav`, and more.
- **Batch Processing**: Convert entire folders or select multiple files to process them concurrently with full progress tracking.
- **Rich Markdown Preview**: Toggle seamlessly between raw Markdown code and a fully-styled, native HTML preview powered by GitHub-flavored CSS.
- **Chrome-Style Tabs**: Modern, sleek tab navigation with seamless design and dynamic light/dark theme sync.
- **Drag & Drop**: Simply drop files into the app to start building your conversion queue.
- **Light & Dark Themes**: Fully polished Light and Dark modes to match your OS or preference seamlessly.
- **Native Experience**: Native Windows executable available, no Python installation required for end users.

## Installation

### For End Users

You don't need to install Python or any dependencies! We offer two ways to run the app:

1. Go to the **[Releases](../../releases/latest)** page on GitHub.
2. Choose the version that suits you best:
   - **`MarkItDown-Portable.exe`**: A single, standalone file. Just download and double-click. (Note: Takes a few seconds to launch as it unpacks in the background).
   - **`MarkItDown.zip`**: A fast-launch package. Download, extract the folder, and run the `MarkItDown.exe` inside it. Opens instantly!

### For Developers
If you want to run the project from source or build it yourself:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Mahan-GhadimKhani/MarkItDownGUI.git
   cd MarkItDownGUI
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Build the executable:**
   ```bash
   python build_exe.py
   ```
   *The output `.exe` will be located in `dist/MarkItDown/`.*

## Testing

The project uses `pytest` for unit testing. To run tests:

```bash
pytest tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
