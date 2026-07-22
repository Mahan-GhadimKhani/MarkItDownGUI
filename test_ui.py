import sys
from PySide6.QtWidgets import QApplication, QPushButton, QLabel
from app import MarkItDownGUI

app = QApplication(sys.argv)
window = MarkItDownGUI()
for widget in window.findChildren(QPushButton):
    print(f"Button '{widget.objectName()}': text='{widget.text().encode('ascii', 'replace').decode()}'")
for widget in window.findChildren(QLabel):
    print(f"Label '{widget.objectName()}': text='{widget.text().encode('ascii', 'replace').decode()}'")
