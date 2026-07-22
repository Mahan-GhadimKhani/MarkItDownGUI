import os
import sys

# Ensure MarkItDownGUI module path is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from converter_engine import MarkItDownEngine


def test_is_supported():
    engine = MarkItDownEngine()

    # Supported file extensions
    assert engine.is_supported("document.docx") is True
    assert engine.is_supported("presentation.pptx") is True
    assert engine.is_supported("sheet.xlsx") is True
    assert engine.is_supported("sample.pdf") is True
    assert engine.is_supported("index.html") is True
    assert engine.is_supported("image.PNG") is True  # Case sensitivity check
    assert engine.is_supported("notes.txt") is True

    # Unsupported file extensions
    assert engine.is_supported("app.exe") is False
    assert engine.is_supported("file.unknown_ext") is False
    assert engine.is_supported("script.py") is False


def test_format_output_markdown():
    text = "# Title\n\nThis is a sample markdown text."
    result = MarkItDownEngine.format_output(text, "md")
    assert result == text


def test_format_output_txt():
    text = "# Title\n\nThis is a sample markdown text."
    result = MarkItDownEngine.format_output(text, "txt")
    assert result == text


def test_format_output_html():
    text = "# Header 1\n## Header 2\n### Header 3\nParagraph text"
    title = "Test Document"
    result = MarkItDownEngine.format_output(text, "html", title=title)

    assert "<!DOCTYPE html>" in result
    assert f"<title>{title}</title>" in result
    assert "<h1>Header 1</h1>" in result
    assert "<h2>Header 2</h2>" in result
    assert "<h3>Header 3</h3>" in result
    assert "<p>Paragraph text</p>" in result


def test_format_output_html_escaping():
    text = 'Text with & special <chars> like "quotes" and \'single\''
    result = MarkItDownEngine.format_output(text, "html")
    assert "&amp;" in result
    assert "&lt;chars&gt;" in result
    assert "&quot;quotes&quot;" in result

