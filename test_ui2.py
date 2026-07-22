import sys
from PySide6.QtWidgets import QApplication, QPushButton, QLabel
from app import MarkItDownGUI

app = QApplication(sys.argv)
window = MarkItDownGUI()
for widget in window.findChildren(QPushButton):
    t = widget.text()
    if t: print(f"Button: {repr(t)}".encode('ascii', 'replace').decode())
for widget in window.findChildren(QLabel):
    t = widget.text()
    if t: print(f"Label: {repr(t)}".encode('ascii', 'replace').decode())
