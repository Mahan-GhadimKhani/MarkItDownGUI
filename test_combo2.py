import sys
from PySide6.QtWidgets import QApplication, QComboBox
app = QApplication(sys.argv)
svg_data = """<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>"""
import urllib.parse
svg_encoded = urllib.parse.quote(svg_data)
css = f"""
QComboBox {{ 
    background-color: #1a1a1a; border: 1px solid #2a2a2a; 
    color: #ddd; padding: 8px; border-radius: 6px;
}}
QComboBox::drop-down {{
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: url("data:image/svg+xml;utf8,{svg_encoded}");
    width: 14px;
    height: 14px;
    padding-right: 10px;
}}
"""
app.setStyleSheet(css)
c = QComboBox()
c.addItems(["Markdown (.md)", "HTML (.html)"])
c.show()
app.exec()
