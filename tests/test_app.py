import os
import sys

# Ensure MarkItDownGUI module path is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import MarkItDownGUI


def test_split_dnd_paths_single_unquoted():
    data = "C:/Users/Test/Document.pdf"
    result = MarkItDownGUI.split_dnd_paths(data)
    assert result == ["C:/Users/Test/Document.pdf"]


def test_split_dnd_paths_single_braced():
    data = "{C:/Users/Test User/My Document.pdf}"
    result = MarkItDownGUI.split_dnd_paths(data)
    assert result == ["C:/Users/Test User/My Document.pdf"]


def test_split_dnd_paths_multiple_mixed():
    data = "{C:/Folder One/a.pdf} C:/FolderTwo/b.pdf {D:/Folder Three/c.txt}"
    result = MarkItDownGUI.split_dnd_paths(data)
    assert result == [
        "C:/Folder One/a.pdf",
        "C:/FolderTwo/b.pdf",
        "D:/Folder Three/c.txt"
    ]


def test_split_dnd_paths_empty_or_none():
    assert MarkItDownGUI.split_dnd_paths("") == []
    assert MarkItDownGUI.split_dnd_paths("   ") == []
    assert MarkItDownGUI.split_dnd_paths(None) == []


def test_split_dnd_paths_extra_whitespace():
    data = "  { C:/Path With Spaces/file.docx }   C:/SimplePath.xlsx  "
    result = MarkItDownGUI.split_dnd_paths(data)
    assert result == [
        "C:/Path With Spaces/file.docx",
        "C:/SimplePath.xlsx"
    ]


def test_split_dnd_paths_unicode():
    data = "{C:/اسناد/گزارش.pdf} C:/Filing/data.csv"
    result = MarkItDownGUI.split_dnd_paths(data)
    assert result == ["C:/اسناد/گزارش.pdf", "C:/Filing/data.csv"]
