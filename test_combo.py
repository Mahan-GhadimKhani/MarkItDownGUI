import sys
from PySide6.QtWidgets import QApplication, QComboBox
app = QApplication(sys.argv)
app.setStyleSheet("""
QComboBox { 
    background-color: #1a1a1a; border: 1px solid #2a2a2a; 
    color: #ddd; padding: 8px; border-radius: 6px;
}
QComboBox::drop-down {
    border: none;
    background: transparent;
}
""")
c = QComboBox()
c.addItems(["Markdown (.md)", "HTML (.html)"])
c.show()
app.exec()
