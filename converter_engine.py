import html
import os
import threading
from typing import List, Callable, Optional, Tuple
from markitdown import MarkItDown

SUPPORTED_EXTENSIONS = {
    '.docx', '.pptx', '.xlsx', '.xls', '.pdf',
    '.html', '.htm', '.xhtml', '.xml', '.json', '.csv',
    '.zip', '.txt', '.text', '.log', '.md',
    '.mp3', '.wav', '.m4a', '.ogg',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp'
}

class ConversionTask:
    def __init__(self, file_path: str, output_dir: Optional[str] = None, output_format: str = "md"):
        self.file_path = file_path
        self.output_dir = output_dir
        self.output_format = output_format
        self.status = "Pending"  # Pending, Processing, Success, Error
        self.error_message = ""
        self.result_text = ""
        self.output_file = ""

class MarkItDownEngine:
    def __init__(self):
        self.markitdown = MarkItDown()

    def is_supported(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    def convert_single_file(self, file_path: str) -> Tuple[bool, str]:
        """Convert a single file to markdown text."""
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            
            result = self.markitdown.convert(file_path)
            content = result.text_content if hasattr(result, 'text_content') else str(result)
            return True, content
        except Exception as e:
            return False, f"Error converting {os.path.basename(file_path)}: {str(e)}"

    def convert_batch_async(
        self,
        file_paths: List[str],
        output_dir: str,
        output_format: str,
        on_progress: Callable[[int, int, str, str], None], # (current, total, filename, status)
        on_complete: Callable[[List[ConversionTask]], None]
    ):
        """Run batch conversion in a separate thread."""
        thread = threading.Thread(
            target=self._run_batch,
            args=(file_paths, output_dir, output_format, on_progress, on_complete),
            daemon=True
        )
        thread.start()

    def _run_batch(
        self,
        file_paths: List[str],
        output_dir: str,
        output_format: str,
        on_progress: Callable[[int, int, str, str], None],
        on_complete: Callable[[List[ConversionTask]], None]
    ):
        tasks = [ConversionTask(fp, output_dir, output_format) for fp in file_paths]
        total = len(tasks)

        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                for t in tasks:
                    t.status = "Error"
                    t.error_message = f"Failed to create output directory: {str(e)}"
                on_complete(tasks)
                return

        for idx, task in enumerate(tasks, start=1):
            fname = os.path.basename(task.file_path)
            task.status = "Processing"
            on_progress(idx, total, fname, "Processing")

            success, result_or_err = self.convert_single_file(task.file_path)
            if success:
                task.status = "Success"
                task.result_text = result_or_err
                
                # Determine output filename
                base_name = os.path.splitext(fname)[0]
                ext_map = {"md": ".md", "txt": ".txt", "html": ".html"}
                out_ext = ext_map.get(output_format.lower(), ".md")
                out_path = os.path.join(output_dir, f"{base_name}{out_ext}")

                try:
                    formatted_content = self.format_output(task.result_text, output_format, title=base_name)
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(formatted_content)
                    task.output_file = out_path
                except Exception as ex:
                    task.status = "Error"
                    task.error_message = f"Failed to save file: {str(ex)}"
            else:
                task.status = "Error"
                task.error_message = result_or_err

            on_progress(idx, total, fname, task.status)

        on_complete(tasks)

    @staticmethod
    def format_output(markdown_text: str, fmt: str, title: str = "Converted Document") -> str:
        fmt = fmt.lower()
        if fmt == "html":
            html_body = html.escape(markdown_text)
            lines = html_body.split("\n")
            html_lines = []
            for line in lines:
                if line.startswith("# "):
                    html_lines.append(f"<h1>{line[2:]}</h1>")
                elif line.startswith("## "):
                    html_lines.append(f"<h2>{line[3:]}</h2>")
                elif line.startswith("### "):
                    html_lines.append(f"<h3>{line[4:]}</h3>")
                elif line.strip():
                    html_lines.append(f"<p>{line}</p>")
                else:
                    html_lines.append("<br/>")
            
            body_content = "\n".join(html_lines)
            return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; padding: 20px; max-width: 900px; margin: 0 auto; color: #333; }}
        h1, h2, h3 {{ color: #1a1a1a; }}
        code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: monospace; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
{body_content}
</body>
</html>"""
        elif fmt == "txt":
            return markdown_text
        else:  # md
            return markdown_text
