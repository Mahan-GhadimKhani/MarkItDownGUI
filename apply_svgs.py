import re

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Right Panel Empty State Icon
code = code.replace('icon_lbl = QLabel("?")', 'icon_lbl = QLabel()\n        icon_lbl.setPixmap(get_icon("arrow-up-down", "#444").pixmap(40, 40))')
code = code.replace('icon_lbl.setStyleSheet("font-size: 40px; color: #444; margin-bottom: 10px;")', 'icon_lbl.setStyleSheet("margin-bottom: 10px;")')

# 2. QueueDropZoneWidget 'btn_del'
code = code.replace('btn_del = QPushButton("?")', 'btn_del = QPushButton()\n                btn_del.setIcon(get_icon("x", "#666"))')

# 3. _apply_dark_theme (Update Icons)
dark_add = '''
        self.theme_btn.setIcon(get_icon("sun", "#ccc"))
        self.btn_dest_browse.setIcon(get_icon("plus", "#ccc"))
        self.btn_select_files.setIcon(get_icon("file-plus", "#ccc"))
        self.btn_select_folder.setIcon(get_icon("folder-plus", "#ccc"))
        self.btn_convert.setIcon(get_icon("arrow-right", "#111"))
        self.btn_copy.setIcon(get_icon("copy", "#888"))
        self.btn_clear_queue.setIcon(get_icon("x", "#666"))
        
        # update right stack empty icon color
        if hasattr(self, 'icon_lbl'):
            self.icon_lbl.setPixmap(get_icon("arrow-up-down", "#444").pixmap(40, 40))
'''
code = code.replace('self.drop_zone.update_list(self.selected_files, self.converted_success_files)', dark_add + '\n        self.drop_zone.update_list(self.selected_files, self.converted_success_files)', 1)

# 4. _apply_light_theme (Update Icons)
light_add = '''
        self.theme_btn.setIcon(get_icon("moon", "#333"))
        self.btn_dest_browse.setIcon(get_icon("plus", "#555"))
        self.btn_select_files.setIcon(get_icon("file-plus", "#333"))
        self.btn_select_folder.setIcon(get_icon("folder-plus", "#333"))
        self.btn_convert.setIcon(get_icon("arrow-right", "#fff"))
        self.btn_copy.setIcon(get_icon("copy", "#888"))
        self.btn_clear_queue.setIcon(get_icon("x", "#888"))

        # update right stack empty icon color
        if hasattr(self, 'icon_lbl'):
            self.icon_lbl.setPixmap(get_icon("arrow-up-down", "#999").pixmap(40, 40))
'''
code = code.replace('self.drop_zone.update_list(self.selected_files, self.converted_success_files)', light_add + '\n        self.drop_zone.update_list(self.selected_files, self.converted_success_files)')

# 5. Make btn_select_files and btn_select_folder instance variables
code = code.replace('btn_select_files = QPushButton("+ Files")', 'self.btn_select_files = QPushButton("Files")')
code = code.replace('btn_select_folder = QPushButton("+ Folder")', 'self.btn_select_folder = QPushButton("Folder")')
code = code.replace('btn_select_files.clicked.connect', 'self.btn_select_files.clicked.connect')
code = code.replace('btn_select_folder.clicked.connect', 'self.btn_select_folder.clicked.connect')
code = code.replace('btn_layout.addWidget(btn_select_files)', 'btn_layout.addWidget(self.btn_select_files)')
code = code.replace('btn_layout.addWidget(btn_select_folder)', 'btn_layout.addWidget(self.btn_select_folder)')

# 6. Make btn_dest_browse instance variable
code = code.replace('btn_dest_browse = QPushButton("+")', 'self.btn_dest_browse = QPushButton()')
code = code.replace('btn_dest_browse.setObjectName', 'self.btn_dest_browse.setObjectName')
code = code.replace('btn_dest_browse.setFixedSize', 'self.btn_dest_browse.setFixedSize')
code = code.replace('btn_dest_browse.clicked.connect', 'self.btn_dest_browse.clicked.connect')
code = code.replace('dest_layout.addWidget(btn_dest_browse)', 'dest_layout.addWidget(self.btn_dest_browse)')

# 7. Remove texts from buttons that now use icons
code = code.replace('self.theme_btn = QPushButton("??")', 'self.theme_btn = QPushButton()')
code = code.replace('self.theme_btn.setText("??")', 'pass # Set in theme change')
code = code.replace('self.theme_btn.setText("??")', 'pass # Set in theme change')
code = code.replace('self.btn_convert = QPushButton("? Start Conversion")', 'self.btn_convert = QPushButton("Start Conversion")')
code = code.replace('self.btn_convert.setText("? Start Conversion")', 'self.btn_convert.setText("Start Conversion")')

# 8. Set Right Panel icon_lbl as instance variable so theme can access it
code = code.replace('icon_lbl = QLabel()', 'self.icon_lbl = QLabel()')
code = code.replace('icon_lbl.setPixmap', 'self.icon_lbl.setPixmap')
code = code.replace('icon_lbl.setAlignment', 'self.icon_lbl.setAlignment')
code = code.replace('icon_lbl.setStyleSheet', 'self.icon_lbl.setStyleSheet')
code = code.replace('empty_layout.addWidget(icon_lbl)', 'empty_layout.addWidget(self.icon_lbl)')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("app.py updated with SVG icons!")
