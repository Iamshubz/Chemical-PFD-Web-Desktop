import os
import json
from datetime import datetime
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QComboBox
)
from PyQt5.QtCore import Qt

from src.api_client import post_component, get_components
from src.grip_editor_dialog import GripEditorDialog

class AddSymbolDialog(QDialog):
    def __init__(self, parent=None, theme="light"):
        super().__init__(parent)

        self.setWindowTitle("Add New Symbol")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setMinimumHeight(800)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Store theme for child dialogs
        self.current_theme = theme

        # Modern rounded popup
        # self.setStyleSheet("""
        #     QDialog {
        #         border-radius: 16px;
        #         background-color: #ffffff;
        #     }
        #     QLabel {
        #         font-size: 14px;
        #         font-weight: 500;
        #     }
        #     QLineEdit, QTextEdit {
        #         border: 1px solid #ccc;
        #         border-radius: 8px;
        #         padding: 6px;
        #         font-size: 14px;
        #     }
        #     QPushButton {
        #         padding: 8px 18px;
        #         border-radius: 8px;
        #         font-size: 14px;
        #         font-weight: 600;
        #     }
        #     QPushButton#submitBtn {
        #         background-color: #3b82f6;
        #         color: white;
        #     }
        #     QPushButton#submitBtn:hover {
        #         background-color: #2563eb;
        #     }
        #     QPushButton#cancelBtn {
        #         background-color: #e5e7eb;
        #     }
        #     QPushButton#fileBtn {
        #         background-color: #d1d5db;
        #         padding: 6px 12px;
        #         border-radius: 6px;
        #         font-size: 13px;
        #     }
        # """)

        self.svg_path = ""
        self.png_path = ""
        self.grips_json = "[]"

        # Apply the passed theme immediately
        self.apply_theme(theme)

        outer_layout = QVBoxLayout(self)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        container = QtWidgets.QWidget()
        container.setObjectName("container")
        layout = QVBoxLayout(container)
        layout.setSpacing(14)

        scroll.setWidget(container)

        # Header with Help Button
        header_layout = QHBoxLayout()
        
        title = QLabel("Add New Symbol")
        title.setStyleSheet("font-size: 20px; font-weight: 600; margin-bottom: 10px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        self.help_btn = QPushButton("i")
        self.help_btn.setObjectName("helpCircleBtn")
        self.help_btn.setFixedSize(30, 30)
        self.help_btn.clicked.connect(self.show_help)
        header_layout.addWidget(self.help_btn)
        
        layout.addLayout(header_layout)

        # --- Input Fields ---
        self.name = self._line(layout, "Component Name", "e.g. My Custom Heat Exchanger")

        layout.addWidget(QLabel("Category"))
        self.category = QComboBox()
        self.category.addItem("Select category")
        self._load_categories()
        layout.addWidget(self.category)

        self.new_category = self._line(layout, "New Category (Optional)", "Or create new...")
        self.legend = self._line(layout, "Legend", "e.g. P, HEX, V")
        self.suffix = self._line(layout, "Suffix", "e.g. A, B")

        self.label_format = QLabel("Label format: Legend-Count-Suffix (e.g. P-01-A)")
        self.label_format.setStyleSheet("font-size: 12px; opacity: 0.85;")
        layout.addWidget(self.label_format)

        self.label_preview = QLabel("Preview: --")
        self.label_preview.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self.label_preview)
        self.legend.textChanged.connect(self._update_label_preview)
        self.suffix.textChanged.connect(self._update_label_preview)

        # File pickers
        layout.addWidget(QLabel("Canvas SVG *"))
        self.svg_btn = QPushButton("Choose SVG File")
        self.svg_btn.setObjectName("fileBtn")
        self.svg_btn.clicked.connect(self.pick_svg)
        layout.addWidget(self.svg_btn)

        # Grip Editor
        self.edit_grips_btn = QPushButton("Open Grip Editor")
        self.edit_grips_btn.setObjectName("fileBtn")
        self.edit_grips_btn.clicked.connect(self.open_grip_editor)
        self.edit_grips_btn.setEnabled(False)
        layout.addWidget(self.edit_grips_btn)

        self.grips_status = QLabel("Grips: 0 configured")
        self.grips_status.setStyleSheet("font-size: 12px; opacity: 0.85;")
        layout.addWidget(self.grips_status)

        layout.addWidget(QLabel("Toolbar Icon (PNG) *"))
        self.png_btn = QPushButton("Choose PNG File")
        self.png_btn.setObjectName("fileBtn")
        self.png_btn.clicked.connect(self.pick_png)
        layout.addWidget(self.png_btn)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelBtn")
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)

        self.submit_btn = QPushButton("Create Component")
        self.submit_btn.setObjectName("submitBtn")
        self.submit_btn.clicked.connect(self.submit)
        btn_row.addWidget(self.submit_btn)

        layout.addLayout(btn_row)

    def apply_theme(self, theme):
        """
        Applies styles based on the ComponentLibrary color scheme.
        """
        if theme == "dark":
            bg_main       = "#0f172a" 
            text_main     = "#f8fafc"
            
            input_bg      = "#1e293b"
            input_border  = "#3b82f6"
            input_text    = "#ffffff"
            
            btn_bg        = "#1e293b"
            btn_border    = "#334155"
            btn_text      = "#f8fafc"
            btn_hover     = "#334155"
            
            submit_bg     = "#3b82f6"
            submit_text   = "#ffffff"
            submit_hover  = "#2563eb"

        else:
            bg_main       = "#fffaf5"
            text_main     = "#3A2A20"
            
            input_bg      = "#FFFFFF"
            input_border  = "#C97B5A"
            input_text    = "#3A2A20"

            btn_bg        = "#f4e8dc"
            btn_border    = "#C97B5A"
            btn_text      = "#3A2A20"
            btn_hover     = "#ffffff"
            
            submit_bg     = "#C97B5A"
            submit_text   = "#ffffff"
            submit_hover  = "#B06345"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_main};
                color: {text_main};
            }}
            QWidget {{
                background-color: {bg_main};
                color: {text_main};
            }}
            QLabel {{
                color: {text_main};
                font-size: 14px;
                font-weight: 500;
            }}
            
            QLineEdit, QComboBox {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px;
                font-size: 14px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid {input_border};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}

            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {btn_border};
                padding: 8px 18px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}

            QPushButton#submitBtn {{
                background-color: {submit_bg};
                color: {submit_text};
                border: none;
            }}
            QPushButton#submitBtn:hover {{
                background-color: {submit_hover};
            }}

            QPushButton#helpCircleBtn {{
                background-color: transparent;
                border: 2px solid {btn_border};
                border-radius: 15px;
                color: {btn_border};
                padding: 0;
                font-family: serif;
                font-size: 16px;
                font-style: italic;
                font-weight: bold;
            }}
            QPushButton#helpCircleBtn:hover {{
                background-color: {btn_border};
                color: {bg_main};
            }}
            
            QScrollArea {{
                background-color: {bg_main};
                border: none;
            }}
        """)

    def _line(self, layout, label_text, placeholder=None):
        if placeholder is None:
            placeholder = label_text
        lbl = QLabel(label_text)
        layout.addWidget(lbl)
        line = QLineEdit()
        line.setPlaceholderText(placeholder)
        layout.addWidget(line)
        return line

    def _load_categories(self):
        categories = set()
        try:
            components = get_components() or []
            for item in components:
                parent = (item.get("parent") or "").strip()
                if parent:
                    categories.add(parent)
        except Exception:
            categories = set()

        for category in sorted(categories):
            self.category.addItem(category)

    def _update_label_preview(self):
        legend = self.legend.text().strip()
        suffix = self.suffix.text().strip()
        if not legend:
            self.label_preview.setText("Preview: --")
            return
        label = f"{legend}-01-{suffix}" if suffix else f"{legend}-01"
        self.label_preview.setText(f"Preview: {label}")

    def _selected_category(self):
        custom_category = self.new_category.text().strip()
        if custom_category:
            return custom_category
        selected = self.category.currentText().strip()
        if selected and selected != "Select category":
            return selected
        return ""

    def _generate_s_no(self):
        return datetime.now().strftime("%H%M%S%f")[-10:]

    def pick_svg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select SVG", "", "SVG Files (*.svg)")
        if path:
            self.svg_path = path
            self.svg_btn.setText(os.path.basename(path))
            self.edit_grips_btn.setEnabled(True)
            self.grips_json = "[]"
            self.grips_status.setText("Grips: 0 configured")

    def pick_png(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PNG", "", "PNG Files (*.png)")
        if path:
            self.png_path = path
            self.png_btn.setText(os.path.basename(path))

    def submit(self):
        component_name = self.name.text().strip()
        category = self._selected_category()

        missing = []
        if not component_name:
            missing.append("Component Name")
        if not category:
            missing.append("Category or New Category")
        if not self.svg_path:
            missing.append("Canvas SVG")
        if not self.png_path:
            missing.append("Toolbar Icon (PNG)")

        if missing:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing Required Fields",
                "Please provide:\n- " + "\n- ".join(missing),
            )
            return

        object_name = "".join(component_name.split())
        legend = self.legend.text().strip()
        suffix = self.suffix.text().strip()

        data = {
            "s_no": self._generate_s_no(),
            "parent": category,
            "name": component_name,
            "legend": legend,
            "suffix": suffix,
            "object": object_name,
            "grips": self.grips_json,
        }

        files = {
            "svg": open(str(self.svg_path), "rb"),
            "png": open(str(self.png_path), "rb"),
        }

        try:
            response = post_component(data, files)
        finally:
            for file_obj in files.values():
                try:
                    file_obj.close()
                except Exception:
                    pass

        if response is not None and response.status_code in (200, 201):
            QtWidgets.QMessageBox.information(self, "Success", "Symbol added successfully.")
            self.accept()
        else:
            details = ""
            if response is not None:
                try:
                    details = response.text
                except Exception:
                    details = ""
            error_msg = "Failed to add component."
            if details:
                error_msg += f"\n\n{details}"
            QtWidgets.QMessageBox.critical(self, "Error", error_msg)

    def open_grip_editor(self):
        if not self.svg_path:
            QtWidgets.QMessageBox.warning(self, "No SVG", "Please select an SVG file first.")
            return

        if not os.path.exists(self.svg_path):
            QtWidgets.QMessageBox.warning(self, "Invalid SVG", "Selected SVG file was not found. Please reselect it.")
            self.svg_path = ""
            self.svg_btn.setText("Choose SVG File")
            self.edit_grips_btn.setEnabled(False)
            self.grips_json = "[]"
            self.grips_status.setText("Grips: 0 configured")
            return

        dlg = GripEditorDialog(self.svg_path, self, theme=self.current_theme)
        dlg.load_grips_json(self.grips_json)
        if dlg.exec_() == QDialog.Accepted:
            grips_json = dlg.get_grips_json()
            self.grips_json = grips_json
            try:
                grip_count = len(json.loads(grips_json))
            except Exception:
                grip_count = 0
            self.grips_status.setText(f"Grips: {grip_count} configured")

    def show_help(self):
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Help / Info")
        help_dialog.setWindowFlags(help_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        help_dialog.setModal(True)
        help_dialog.setMinimumWidth(400)
        
        # Inherit main dialog stylesheet for perfect theme consistency
        help_dialog.setStyleSheet(self.styleSheet())
        
        layout = QVBoxLayout(help_dialog)
        layout.setSpacing(15)
        
        help_text = """
        <h3 style="margin-top:0; margin-bottom:5px; font-weight:600;">Required Files</h3>
        <ul style="margin-top:0;">
            <li><span style="font-weight:600;">PNG</span> :- used for toolbar display</li>
            <li><span style="font-weight:600;">SVG</span> :- used for canvas rendering</li>
        </ul>
        
        <h3 style="margin-bottom:5px; font-weight:600;">Fields Explanation</h3>
        <ul style="margin-top:0;">
            <li><span style="font-weight:600;">Component Name</span> :- Custom name</li>
            <li><span style="font-weight:600;">Category</span> :- Select existing category</li>
            <li><span style="font-weight:600;">New Category</span> :- Create new group</li>
            <li><span style="font-weight:600;">Legend</span> :- Used for label prefix</li>
            <li><span style="font-weight:600;">Suffix</span> :- Optional label suffix</li>
        </ul>
        
        <h3 style="margin-bottom:5px; font-weight:600;">Label Format</h3>
        <p style="margin-top:0;">Example: Legend-Count-Suffix :- <span style="font-weight:600;">P-01-A</span></p>
        
        <h3 style="margin-bottom:5px; font-weight:600;">Grip / Connector Info</h3>
        <p style="margin-top:0;">Grips are connection points for linking components.<br>
        Must be defined using the Grip Editor after SVG upload.</p>
        """
        
        label = QLabel(help_text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        
        # Ensure the text adopts the correct theme color and clean system font
        label.setStyleSheet("font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; font-weight: 400; line-height: 1.4;")
        layout.addWidget(label)
        
        close_btn = QPushButton("Close")
        close_btn.setObjectName("submitBtn")
        close_btn.clicked.connect(help_dialog.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        help_dialog.exec_()