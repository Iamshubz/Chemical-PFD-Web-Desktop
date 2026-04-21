import os
import json
from PyQt5 import QtWidgets, QtGui, QtSvg, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QFileDialog, QSplitter
)

from src.api_client import post_component
import src.app_state as app_state

class DraggableGripItem(QtWidgets.QGraphicsEllipseItem):
    """A grip point that can be dragged, deleted, and shows its number"""
    
    def __init__(self, x, y, side, index, editor, radius=4):
        super().__init__(-radius, -radius, 2*radius, 2*radius)
        self.editor = editor
        self.index = index
        self.side = side
        self.radius = radius
        self.setPos(x, y) #Set the absolute position in the scene
        self.center_x = x
        self.center_y = y
        
        # Style - red circle with white border for better visibility
        self.setPen(QtGui.QPen(Qt.NoPen))
        self.setBrush(QtGui.QBrush(QtGui.QColor("cyan")))  # Bright red
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)
        self.setZValue(10)
        self.setCursor(Qt.OpenHandCursor)
        
        # Number label with better visibility
        # self.label = QtWidgets.QGraphicsTextItem(str(index + 1), self)
        # self.label.setDefaultTextColor(Qt.white)
        # font = self.label.font()
        # font.setPixelSize(12)
        # font.setBold(True)
        # self.label.setFont(font)
        
        # # Add text outline/shadow for better visibility
        # effect = QtWidgets.QGraphicsDropShadowEffect()
        # effect.setBlurRadius(2)
        # effect.setColor(QtGui.QColor(0, 0, 0, 180))
        # effect.setOffset(0, 0)
        # self.label.setGraphicsEffect(effect)
        
        # # Center the text
        # text_rect = self.label.boundingRect()
        # self.label.setPos(
        #     radius - text_rect.width() / 2,
        #     radius - text_rect.height() / 2
        # )
        
    def mousePressEvent(self, event):
        # Right-click OR Ctrl/Cmd+Click to delete (Mac trackpad friendly)
        if event.button() == Qt.RightButton or (
            event.button() == Qt.LeftButton and 
            event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier)
        ):
            self.editor.delete_grip(self.index)
            event.accept()
        else:
            self.setCursor(Qt.ClosedHandCursor)
            super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
    
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            # Update the stored coordinates when moved
            new_pos = value
            self.center_x = new_pos.x() 
            self.center_y = new_pos.y() 
            
            # Auto-detect nearest edge
            if self.editor.auto_detect_edge:
                self.side = self.editor.detect_nearest_edge(self.center_x, self.center_y)
            
            # Update in editor's points list
            if 0 <= self.index < len(self.editor.points):
                self.editor.points[self.index] = {
                    "x": self.center_x,
                    "y": self.center_y,
                    "side": self.side
                }
                
            # Update live preview
            self.editor.update_preview()
        
        return super().itemChange(change, value)

class GripEditorDialog(QDialog):
    def __init__(self, svg_path, parent=None, theme="light"):
        super().__init__(parent)

        self.setWindowTitle("Grip Editor")
        self.setMinimumSize(1000, 700)
        self.resize(1400, 800)
        self.svg_path = svg_path
        self.auto_detect_edge = True  # Auto-detect edge by default

        # state
        self.points = []
        self.undo_stack = []
        self.redo_stack = []
        self.grip_items = []  # Track grip graphics items
        self._press_pos = QtCore.QPoint()
        self._last_mouse_pos = QtCore.QPoint()
        self._is_dragging = False

        # Main layout
        main_layout = QVBoxLayout(self)

        # ---------------- MENU BAR ----------------
        menu_bar = QtWidgets.QMenuBar(self)
        help_menu = menu_bar.addMenu("Help")

        help_text = (
            "🎯 GRIP EDITOR CONTROLS\n\n"
            
            "📌 Adding Grips\n"
            "  • Left Click → Add new grip\n"
            "  • Auto-detects nearest edge (unless manual side selected)\n\n"
            
            "✏️ Editing Grips\n"
            "  • Drag (Left Click + Move) → Move grip\n"
            "  • Right Click → Delete grip\n"
            "  • Ctrl/Cmd + Left Click → Delete grip (Mac trackpad)\n"
            "  • Side updates automatically during drag when Auto mode is enabled\n\n"
            
            "🔍 Zoom Controls\n"
            "  • Mouse Wheel / Trackpad Pinch → Zoom in/out\n"
            "  • Windows/Linux: Ctrl + '+'  /  Ctrl + '-'\n"
            "  • macOS: Cmd + '+'  /  Cmd + '-'\n"
            "  • Ctrl/Cmd + 0 → Reset zoom\n\n"
            
            "🌍 Panning the Canvas\n"
            "  • macOS Trackpad: Two-finger drag\n"
            "  • Windows/Linux Mouse: Left-drag on empty area\n"
            "  • Middle-button drag (if available) also pans\n\n"
            
            "⚡ Undo / Redo\n"
            "  • Ctrl/Cmd + Z → Undo\n"
            "  • Ctrl/Cmd + Shift + Z → Redo\n\n"
            
            "📍 Live Preview\n"
            "  • Right panel shows real-time preview of grips\n"
            "  • Updates automatically as you add/move/delete grips\n"
        )

        help_action = QtWidgets.QAction("Show Commands", self)
        help_action.triggered.connect(
            lambda: QtWidgets.QMessageBox.information(self, "Help", help_text)
        )

        help_menu.addAction(help_action)
        main_layout.setMenuBar(menu_bar)

        # ---------------- TOOLBAR ----------------
        toolbar = QHBoxLayout()
        
        # Reset Zoom button
        reset_zoom_btn = QPushButton("Reset Zoom (Ctrl+0)")
        reset_zoom_btn.clicked.connect(self.reset_zoom)
        toolbar.addWidget(reset_zoom_btn)
        
        # Auto-detect edge toggle
        self.auto_edge_checkbox = QtWidgets.QCheckBox("Auto-detect Edge")
        self.auto_edge_checkbox.setChecked(True)
        self.auto_edge_checkbox.stateChanged.connect(self.toggle_auto_edge)
        toolbar.addWidget(self.auto_edge_checkbox)

        self.grip_count_label = QLabel("Grips: 0")
        self.grip_count_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        toolbar.addWidget(self.grip_count_label)
        
        toolbar.addStretch()
        
        # Info label
        self.info_label = QLabel("Click to add • Drag to move • Right-click or Ctrl+Click to delete")
        self.info_label.setStyleSheet("color: #666; font-size: 12px;")
        toolbar.addWidget(self.info_label)
        
        main_layout.addLayout(toolbar)

        # ---------------- SPLITTER WITH EDITOR AND PREVIEW ----------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #ddd;
            }
        """)
        
        # Left side: Editor
        editor_widget = QtWidgets.QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(5, 5, 5, 5)
        editor_layout.setSpacing(5)
        
        self.editor_title = QLabel("Editor")
        editor_layout.addWidget(self.editor_title)

        
        self.scene = QtWidgets.QGraphicsScene()
        self.svg_item = QtSvg.QGraphicsSvgItem(svg_path)
        self.scene.addItem(self.svg_item)
        self.svg_bounds = self.svg_item.boundingRect()

        self.view = QtWidgets.QGraphicsView(self.scene)
        self.view.setRenderHints(
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform
        )
        self.view.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.view.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.view.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.view.viewport().installEventFilter(self)

        
        editor_layout.addWidget(self.view)
        
        # Right side: Live Preview (Fixed size)
        preview_widget = QtWidgets.QWidget()
        preview_widget.setMaximumWidth(350)
        preview_widget.setMinimumWidth(300)
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        preview_layout.setSpacing(5)
        
        self.preview_title = QLabel("Live Preview")
        preview_layout.addWidget(self.preview_title)
        
        self.preview_scene = QtWidgets.QGraphicsScene()
        self.preview_svg_item = QtSvg.QGraphicsSvgItem(svg_path)
        self.preview_scene.addItem(self.preview_svg_item)
        
        self.preview_view = QtWidgets.QGraphicsView(self.preview_scene)
        self.preview_view.setRenderHints(
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.SmoothPixmapTransform
        )

        preview_layout.addWidget(self.preview_view)
        
        # Fit preview to view
        self.preview_view.fitInView(self.preview_svg_item, Qt.KeepAspectRatio)
        
        # Add both to splitter
        splitter.addWidget(editor_widget)
        splitter.addWidget(preview_widget)
        splitter.setStretchFactor(0, 3)  # Editor takes more space
        splitter.setStretchFactor(1, 1)  # Preview is smaller
        
        main_layout.addWidget(splitter)

        # ---------------- SIDE SELECT ----------------
        side_layout = QHBoxLayout()
        side_layout.addWidget(QLabel("Manual Side Override:"))
        self.side_select = QtWidgets.QComboBox()
        self.side_select.addItems(["Auto", "top", "right", "bottom", "left"])
        side_layout.addWidget(self.side_select)
        side_layout.addStretch()
        main_layout.addLayout(side_layout)

        # ---------------- BUTTONS ----------------
        btn_row = QHBoxLayout()
        
        undo_btn = QPushButton("Undo (Ctrl+Z)")
        undo_btn.clicked.connect(self.undo)
        btn_row.addWidget(undo_btn)
        
        redo_btn = QPushButton("Redo (Ctrl+Shift+Z)")
        redo_btn.clicked.connect(self.redo)
        btn_row.addWidget(redo_btn)
        
        btn_row.addStretch()
        
        save_btn = QPushButton("Save Grips")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 8px 16px;")
        btn_row.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        
        main_layout.addLayout(btn_row)

        # Apply theme at the end of init
        self.apply_theme(theme)

        # ---------------- SHORTCUTS ----------------
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self, self.undo)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+Z"), self, self.redo)
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl++"), self, lambda: self.zoom(True))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+="), self, lambda: self.zoom(True))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+-"), self, lambda: self.zoom(False))
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+0"), self, self.reset_zoom)

        QtWidgets.QShortcut(QtGui.QKeySequence("Meta+Z"), self, self.undo)
        QtWidgets.QShortcut(QtGui.QKeySequence("Meta+Shift+Z"), self, self.redo)
        QtWidgets.QShortcut(QtGui.QKeySequence("Meta++"), self, lambda: self.zoom(True))
        QtWidgets.QShortcut(QtGui.QKeySequence("Meta+="), self, lambda: self.zoom(True))
        QtWidgets.QShortcut(QtGui.QKeySequence("Meta+-"), self, lambda: self.zoom(False))

        self._update_grip_count()

    def _update_grip_count(self):
        self.grip_count_label.setText(f"Grips: {len(self.points)}")

    def load_grips_json(self, grips_json):
        if not grips_json:
            self.points = []
            self.refresh_grips()
            self.update_preview()
            self._update_grip_count()
            return

        try:
            loaded = json.loads(grips_json)
        except Exception:
            loaded = []

        bounds = self.svg_bounds
        width = bounds.width()
        height = bounds.height()
        left = bounds.left()
        top = bounds.top()

        self.points = []
        for item in loaded:
            try:
                x_percent = float(item.get("x", 0))
                y_percent = float(item.get("y", 0))
                side = str(item.get("side", "right"))
            except Exception:
                continue

            x_abs = left + (x_percent / 100.0) * width if width > 0 else left
            # Stored grips use renderer convention: y=100 at top, y=0 at bottom.
            y_abs = top + ((100.0 - y_percent) / 100.0) * height if height > 0 else top
            self.points.append({"x": x_abs, "y": y_abs, "side": side})

        self.refresh_grips()
        self.update_preview()
        self._update_grip_count()

    def apply_theme(self, theme):
        if theme == "dark":
            bg_main = "#0f172a"
            text_main = "#f8fafc"
            
            # Titles
            title_bg = "#1e293b"
            title_text = "#94a3b8"
            
            # Views
            view_bg = "#1e293b"
            view_border = "#334155"
            
            # Button/Inputs
            btn_bg = "#334155" 
            btn_text = "#f8fafc"
            
        else:
            bg_main = "#ffffff"
            text_main = "#333333"
            
            title_bg = "#f8f9fa"
            title_text = "#495057"
            
            view_bg = "#ffffff"
            view_border = "#dee2e6"
            
            btn_bg = "#e5e7eb"
            btn_text = "#374151"

        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_main}; color: {text_main}; }}
            QLabel {{ color: {text_main}; }}
            QCheckBox {{ color: {text_main}; }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border-radius: 4px;
                padding: 6px;
            }}
        """)
        
        # Specific widgets
        title_style = f"""
            font-size: 13px; 
            font-weight: 600; 
            padding: 8px; 
            background-color: {title_bg};
            border-radius: 4px;
            color: {title_text};
        """
        self.editor_title.setStyleSheet(title_style)
        self.preview_title.setStyleSheet(title_style)
        
        view_style = f"""
            QGraphicsView {{
                border: 1px solid {view_border};
                border-radius: 6px;
                background-color: {view_bg};
            }}
        """
        self.view.setStyleSheet(view_style)
        self.preview_view.setStyleSheet(view_style)

    def update_preview(self):
        """Update the live preview with current grips"""
        # Clear existing preview grips
        for item in self.preview_scene.items():
            if isinstance(item, QtWidgets.QGraphicsEllipseItem):
                self.preview_scene.removeItem(item)
        
        # Draw all current grips on preview
        svg_bounds = self.preview_svg_item.boundingRect()
        for i, point in enumerate(self.points):
            # Convert percentage to absolute (for display purposes, calculate from editor coords)
            x = point["x"]
            y = point["y"]
            
            # Draw grip point
            radius = 5
            ellipse = QtWidgets.QGraphicsEllipseItem(
                x - radius, y - radius, 2*radius, 2*radius
            )
            ellipse.setPen(QtGui.QPen(Qt.NoPen))
            ellipse.setBrush(QtGui.QBrush(QtGui.QColor(220, 53, 69, 180)))
            ellipse.setZValue(10)
            self.preview_scene.addItem(ellipse)

    def detect_nearest_edge(self, x, y):
        """Detect which edge of the SVG is nearest to the point"""
        bounds = self.svg_bounds
        
        dist_top = abs(y - bounds.top())
        dist_bottom = abs(y - bounds.bottom())
        dist_left = abs(x - bounds.left())
        dist_right = abs(x - bounds.right())
        
        min_dist = min(dist_top, dist_bottom, dist_left, dist_right)
        
        if min_dist == dist_top:
            return "top"
        elif min_dist == dist_bottom:
            return "bottom"
        elif min_dist == dist_left:
            return "left"
        else:
            return "right"
    
    def toggle_auto_edge(self, state):
        self.auto_detect_edge = (state == Qt.Checked)

    def eventFilter(self, obj, event):
        if obj == self.view.viewport():
            if event.type() == QtCore.QEvent.MouseMove:
                scene_pos = self.view.mapToScene(event.pos())
                item = self.scene.itemAt(scene_pos, self.view.transform())
                
                if not isinstance(item, DraggableGripItem):
                    if getattr(self, "_is_dragging", False):
                        delta = event.pos() - self._last_mouse_pos
                        self.view.horizontalScrollBar().setValue(
                            self.view.horizontalScrollBar().value() - delta.x()
                        )
                        self.view.verticalScrollBar().setValue(
                            self.view.verticalScrollBar().value() - delta.y()
                        )
                        self._last_mouse_pos = event.pos()
                        return True

                    if (event.buttons() & Qt.LeftButton):
                        if (event.pos() - self._press_pos).manhattanLength() > 4:
                            self._is_dragging = True
                            self.view.setCursor(Qt.ClosedHandCursor)
                            self._last_mouse_pos = event.pos()
                            return True

            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self._press_pos = event.pos()
                    self._is_dragging = False
                    
                    scene_pos = self.view.mapToScene(event.pos())
                    item = self.scene.itemAt(scene_pos, self.view.transform())
                    if isinstance(item, DraggableGripItem):
                        return False
                    
                    return True

            if event.type() == QtCore.QEvent.MouseButtonRelease:
                self.view.setCursor(Qt.ArrowCursor)

                if event.button() == Qt.LeftButton:
                    if getattr(self, "_is_dragging", False):
                        self._is_dragging = False
                        return True

                    scene_pos = self.view.mapToScene(event.pos())
                    item = self.scene.itemAt(scene_pos, self.view.transform())
                    if isinstance(item, DraggableGripItem):
                        return False

                    self.push_undo()
                    self.add_point(scene_pos)
                    return True

            if event.type() == QtCore.QEvent.Wheel:
                self.zoom(event.angleDelta().y() > 0)
                return True

        return super().eventFilter(obj, event)

    def zoom(self, zoom_in=True):
        factor = 1.15 if zoom_in else 1 / 1.15
        current = self.view.transform().m11()
        if zoom_in and current > 40:
            return
        if (not zoom_in) and current < 0.05:
            return
        self.view.scale(factor, factor)
    
    def reset_zoom(self):
        self.view.resetTransform()
        self.view.fitInView(self.svg_item, Qt.KeepAspectRatio)

    def add_point(self, pos):
        if self.side_select.currentText() == "Auto":
            side = self.detect_nearest_edge(pos.x(), pos.y())
        else:
            side = self.side_select.currentText()
        
        index = len(self.points)
        self.points.append({"x": pos.x(), "y": pos.y(), "side": side})
        
        self.draw_grip(pos.x(), pos.y(), side, index)
        self.update_preview()
        self._update_grip_count()

    def draw_grip(self, x, y, side, index):
        grip = DraggableGripItem(x, y, side, index, self)
        self.scene.addItem(grip)
        self.grip_items.append(grip)

    def delete_grip(self, index):
        if 0 <= index < len(self.points):
            self.push_undo()
            self.points.pop(index)
            self.refresh_grips()
            self.update_preview()
            self._update_grip_count()

    def push_undo(self):
        import copy
        self.undo_stack.append(copy.deepcopy(self.points))
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        import copy
        self.redo_stack.append(copy.deepcopy(self.points))
        self.points = self.undo_stack.pop()
        self.refresh_grips()
        self.update_preview()
        self._update_grip_count()

    def redo(self):
        if not self.redo_stack:
            return
        import copy
        self.undo_stack.append(copy.deepcopy(self.points))
        self.points = self.redo_stack.pop()
        self.refresh_grips()
        self.update_preview()
        self._update_grip_count()

    def refresh_grips(self):
        for grip in self.grip_items:
            self.scene.removeItem(grip)
        self.grip_items.clear()

        for i, p in enumerate(self.points):
            self.draw_grip(p["x"], p["y"], p["side"], i)

    def get_grips_json(self):
        bounds = self.svg_bounds
        width = bounds.width()
        height = bounds.height()
        left = bounds.left()
        top = bounds.top()
        
        percentage_grips = []
        for p in self.points:
            x_percent = ((p["x"] - left) / width) * 100.0 if width > 0 else 0
            # Persist Y in renderer convention: y=100 at top, y=0 at bottom.
            y_percent = (100.0 - ((p["y"] - top) / height) * 100.0) if height > 0 else 0
            
            percentage_grips.append({
                "x": round(x_percent, 2),
                "y": round(y_percent, 2),
                "side": p["side"]
            })
        
        return json.dumps(percentage_grips, indent=2)

class AddSymbolDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Add New Symbol")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.setMinimumHeight(800)

        # Modern rounded popup
        self.setStyleSheet("""
            QDialog {
                border-radius: 16px;
                background-color: #ffffff;
            }
            QLabel {
                font-size: 14px;
                font-weight: 500;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 6px;
                font-size: 14px;
            }
            QPushButton {
                padding: 8px 18px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#submitBtn {
                background-color: #3b82f6;
                color: white;
            }
            QPushButton#submitBtn:hover {
                background-color: #2563eb;
            }
            QPushButton#cancelBtn {
                background-color: #e5e7eb;
            }
            QPushButton#fileBtn {
                background-color: #d1d5db;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 13px;
            }
        """)

        self.svg_path = None
        self.png_path = None

        outer_layout = QVBoxLayout(self)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        container = QtWidgets.QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(14)

        scroll.setWidget(container)

        # Header
        title = QLabel("Add New Symbol")
        title.setStyleSheet("font-size: 20px; font-weight: 600; margin-bottom: 10px;")
        layout.addWidget(title)

        # --- Input Fields ---
        self.sno = self._line(layout, "S No")
        self.parent = self._line(layout, "Parent")
        self.name = self._line(layout, "Name")
        self.legend = self._line(layout, "Legend")
        self.suffix = self._line(layout, "Suffix")
        self.object = self._line(layout, "Object")

        # Grips field
        grips_label = QLabel("Grips (JSON)")
        layout.addWidget(grips_label)

        self.grips = QTextEdit()
        self.grips.setPlaceholderText('[{"x":50,"y":100,"side":"top"}]')
        layout.addWidget(self.grips)

        # File pickers
        layout.addWidget(QLabel("SVG File"))
        self.svg_btn = QPushButton("Choose SVG File")
        self.svg_btn.setObjectName("fileBtn")
        self.svg_btn.clicked.connect(self.pick_svg)
        layout.addWidget(self.svg_btn)

        # Grip Editor
        self.edit_grips_btn = QPushButton("Open Grip Editor")
        self.edit_grips_btn.setObjectName("fileBtn")
        self.edit_grips_btn.clicked.connect(self.open_grip_editor)
        layout.addWidget(self.edit_grips_btn)

        layout.addWidget(QLabel("PNG File"))
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

        self.submit_btn = QPushButton("Submit")
        self.submit_btn.setObjectName("submitBtn")
        self.submit_btn.clicked.connect(self.submit)
        btn_row.addWidget(self.submit_btn)

        layout.addLayout(btn_row)

    def _line(self, layout, placeholder):
        lbl = QLabel(placeholder)
        layout.addWidget(lbl)
        line = QLineEdit()
        line.setPlaceholderText(placeholder)
        layout.addWidget(line)
        return line

    def pick_svg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select SVG", "", "SVG Files (*.svg)")
        if path:
            self.svg_path = path
            self.svg_btn.setText(os.path.basename(path))

    def pick_png(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select PNG", "", "PNG Files (*.png)")
        if path:
            self.png_path = path
            self.png_btn.setText(os.path.basename(path))

    def submit(self):
        if not all([self.sno.text(), self.name.text(), self.object.text()]):
            QtWidgets.QMessageBox.warning(self, "Missing Fields", "S No, Name & Object are required.")
            return

        data = {
            "s_no": self.sno.text(),
            "parent": self.parent.text(),
            "name": self.name.text(),
            "legend": self.legend.text(),
            "suffix": self.suffix.text(),
            "object": self.object.text(),
            "grips": self.grips.toPlainText(),
        }

        files = {}
        if self.svg_path:
            files["svg"] = open(self.svg_path, "rb")
        if self.png_path:
            files["png"] = open(self.png_path, "rb")

        response = post_component(data, files)

        if hasattr(response, "status_code") and response.status_code in (200, 201):
            QtWidgets.QMessageBox.information(self, "Success", "Symbol added successfully.")
            self.accept()
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "Failed to add component.")

    def open_grip_editor(self):
        if not self.svg_path:
            QtWidgets.QMessageBox.warning(self, "No SVG", "Please select an SVG file first.")
            return

        dlg = GripEditorDialog(self.svg_path, self)
        if dlg.exec_() == QDialog.Accepted:
            grips_json = dlg.get_grips_json()
            self.grips.setText(grips_json)

    def apply_theme(self, theme):
        """
        Applies theme to the dialog elements.
        """
        if theme == "dark":
            bg_main       = "#0f172a" 
            text_main     = "#f8fafc"
            
            # Labels and Text
            title_bg      = "#1e293b"
            title_text    = "#f8fafc"
            
            # Buttons
            btn_bg        = "#3a5073"
            btn_border    = "#334155"
            btn_text      = "#f8fafc"
            btn_hover     = "#334155"
            
            save_bg       = "#3b82f6"
            save_text     = "#ffffff"
            
            # Inputs/Splitter
            input_bg      = "#1e293b" # For combo box etc
            input_text    = "#ffffff"
            input_border  = "#334155"
            
        else:
            # Light Theme
            bg_main       = "#fffaf5"
            text_main     = "#3A2A20"
            
            title_bg      = "#f8f9fa"
            title_text    = "#495057"
            
            btn_bg        = "#f4e8dc"
            btn_border    = "#C97B5A"
            btn_text      = "#3A2A20"
            btn_hover     = "#ffffff"
            
            save_bg       = "#3b82f6"
            save_text     = "#ffffff"
            
            input_bg      = "#ffffff"
            input_text    = "#3A2A20"
            input_border  = "#cccccc"

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
            }}
            
            /* Section Titles (Editor/Live Preview) */
            QLabel {{
                font-size: 13px; 
            }}
            
            /* Buttons */
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {btn_border};
                padding: 6px 14px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
            QPushButton {{
                background-color: {save_bg};
                color: {save_text};
                border: none;
            }}
            
            /* Combo Box */
            QComboBox {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QMenuBar {{
                background-color: {bg_main};
                color: {text_main};
            }}
            QMenuBar::item:selected {{
                background-color: {btn_hover};
            }}
            QMenu {{
                background-color: {bg_main};
                color: {text_main};
                border: 1px solid {input_border};
            }}
            QMenu::item:selected {{
                background-color: {btn_hover};
            }}
        """)