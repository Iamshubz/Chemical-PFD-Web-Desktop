import os
import csv
import json
import requests
import src.app_state as app_state
from src.theme_manager import theme_manager
from src import api_client
from src.flow_layout import FlowLayout
from PyQt5.QtCore import Qt, QMimeData, QSize, QTimer, QPropertyAnimation, QEasingCurve, QEvent, pyqtSignal
from PyQt5.QtGui import QIcon, QDrag, QMovie, QPixmap, QPalette
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QFrame, QSizePolicy,
    QScrollArea, QLabel, QToolButton, QGridLayout, QLabel, QApplication, QGraphicsOpacityEffect, QHBoxLayout,
    QMenu, QMessageBox, QDialog, QFormLayout, QDialogButtonBox
)
import threading
import time

class FunctionEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, fn):
        super().__init__(FunctionEvent.EVENT_TYPE)
        self.fn = fn

    def execute(self):
        self.fn()

class ToastMessage(QLabel):
    def __init__(self, parent, message):
        super().__init__(message, parent)
        self.setStyleSheet("""
            background-color: rgba(40, 40, 40, 200);
            color: white;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
        """)
        self.setAlignment(Qt.AlignCenter)

        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)

        self.anim = QPropertyAnimation(self.opacity, b"opacity")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.InOutQuad)

    def show_toast(self):
        # Position bottom-right inside the sidebar
        x = self.parent().width() - self.width() - 20
        y = self.parent().height() - self.height() - 20
        self.setGeometry(x, y, self.width(), self.height())
        self.raise_()

        # Fade In
        self.anim.stop()
        self.opacity.setOpacity(0)
        self.show()

        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.start()

        # Fade Out after 2 seconds
        QTimer.singleShot(2000, self.fade_out)

    def fade_out(self):
        self.anim.stop()
        self.anim.setStartValue(1)
        self.anim.setEndValue(0)
        self.anim.start()

        # Hide after fade-out completes
        QTimer.singleShot(400, self.hide)

        QTimer.singleShot(400, self.hide)

class FlowContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def sizeHint(self):
        if self.layout():
             h = self.layout().heightForWidth(self.width())
             return QSize(280, h)
        return super().sizeHint()
        
    def minimumSizeHint(self):
        return QSize(100, 0)

    def resizeEvent(self, event):
        if self.layout():
            h = self.layout().heightForWidth(event.size().width())
            self.setFixedHeight(h)
        super().resizeEvent(event)

class ComponentButton(QToolButton):
    def __init__(self, component_data, icon_path, parent=None):
        super().__init__(parent)
        self.component_data = component_data
        
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            pix.setDevicePixelRatio(2.0)
            # print(icon_path, pix.width(), pix.height())
            pix = pix.scaled(
                128, 128,                     # upscale
                Qt.KeepAspectRatio,
                Qt.FastTransformation
            )
            self.setIcon(QIcon(pix))
            self.setIconSize(QSize(42, 42))

        # BADGE for added components
        if component_data.get("is_new"):
            # print(f"[BADGE] Creating NEW badge for: {component_data['name']} (s_no: {component_data.get('s_no')})")
            badge = QLabel("NEW", self)
            badge.setStyleSheet("""
                background-color: #3b82f6;
                color: white;
                font-size: 8px;
                font-weight: bold;
                padding: 2px 4px;
                border-radius: 4px;
            """)
            badge.move(24, 2)  # top-right corner
            badge.show()
            badge.raise_()

        
        self.setToolTip(component_data['name'])
        self.setFixedSize(56, 56)
        # self.setStyleSheet("""
        #     QToolButton {
        #         border: 1px solid #ccc;
        #         border-radius: 4px;
        #         background-color: white;
        #         padding: 2px;
        #     }
        #     QToolButton:hover {
        #         border: 2px solid #0078d7;
        #         background-color: #e5f3ff;
        #     }
        # """)
        
        self.dragStartPosition = None
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.dragStartPosition = event.pos()
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.dragStartPosition:
            return
        if (event.pos() - self.dragStartPosition).manhattanLength() < 10:
            return
        
        drag = QDrag(self)
        mimeData = QMimeData()
        # Pass complete component data as JSON (including s_no)
        component_json = json.dumps({
            "s_no": self.component_data.get('s_no', ''),
            "object": self.component_data.get('object', ''),
            "name": self.component_data.get('name', ''),
            "parent": self.component_data.get('parent', ''),
            "legend": self.component_data.get('legend', ''),
            "suffix": self.component_data.get('suffix', ''),
            "grips": self.component_data.get('grips', ''),
            "svg": self.component_data.get('svg', ''),
            "png": self.component_data.get('png', '')
        })
        mimeData.setText(component_json)
        drag.setMimeData(mimeData)
        
        if not self.icon().isNull():
            drag.setPixmap(self.icon().pixmap(32, 32))
        
        drag.exec_(Qt.CopyAction)


class ComponentLibrary(QWidget):
    def __init__(self, parent=None):
        super(ComponentLibrary, self).__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.new_snos = set()  # holds S.No added in last sync
        
        self.setMinimumWidth(200)
        # self.setMaximumWidth(260)  <-- Removed to allow resizing
        
        self.component_data = []
        self.icon_buttons = []
        self.category_widgets = []

        # Connect to global theme manager
        theme_manager.theme_changed.connect(self.on_theme_changed)
        
        # Get initial theme from theme manager
        self.current_library_theme = theme_manager.current_theme
        
        self._setup_ui()
        self.apply_theme(self.current_library_theme)
        self._populate_icons()  # shows empty initially

        # Loader animation (hidden by default)
        self.loader_label = QLabel(self)
        self.loader_label.setAlignment(Qt.AlignCenter)
        self.loader_label.setStyleSheet("background: transparent;")
        self.loader_movie = QMovie("ui/assets/loading.gif")
        self.loader_movie.setScaledSize(QSize(64, 64))
        self.loader_label.setMovie(self.loader_movie)
        self.loader_label.setVisible(False)

    def reload_components(self):
        """Fetch components from API on a background thread, then refresh UI."""
        def _worker():
            self._load_components_from_api()
            QApplication.postEvent(self, FunctionEvent(self._on_api_load_done))
        
        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _on_api_load_done(self):
        """Main-thread callback: repopulate icons after API fetch."""
        self._populate_icons()

    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # --- Header with Toggle Button ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 5)
        
        title = QLabel("Components")
        title.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        
        # Theme Toggle Button
        self.theme_toggle = QToolButton()
        self.theme_toggle.setObjectName("themeToggle")
        self.theme_toggle.setCursor(Qt.PointingHandCursor)
        self.theme_toggle.setStyleSheet("border: none; background: transparent; font-size: 14px;")
        self.theme_toggle.clicked.connect(self.toggle_theme)
        
        self.sync_btn = QToolButton()
        self.sync_btn.setText("Sync")
        self.sync_btn.setCursor(Qt.PointingHandCursor)
        self.sync_btn.clicked.connect(self.reload_components)
        self.sync_btn.setStyleSheet("border: none; background: transparent; font-size: 12px; color: #666;")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.sync_btn)
        header_layout.addWidget(self.theme_toggle)
        
        main_layout.addWidget(header_widget)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search components...")
        self.search_box.textChanged.connect(self._filter_icons)
        main_layout.addWidget(self.search_box)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area)
        
    def _show_loader(self):
        size = 80
        self.loader_label.setGeometry(
            (self.width() - size) // 2,
            (self.height() - size) // 2,
            size, size
        )
        self.loader_label.setVisible(True)
        self.loader_label.setStyleSheet("background-color: rgba(0,0,0,120); border-radius: 6px;")
        self.loader_movie.start()
        self.loader_label.raise_()
        QApplication.processEvents()

    def _hide_loader(self):
        self.loader_movie.stop()
        self.loader_label.setVisible(False)

    def _load_components_from_api(self):
        """Fetch components directly from backend API (network call — run on bg thread)."""
        try:
            api_components = api_client.get_components()
            if not api_components:
                print("[SYNC] No components received or API failed.")
                return

            new_data = []
            for comp in api_components:
                s_no = str(comp.get("s_no", "")).strip()
                if not s_no:
                    continue

                # Download assets if missing
                png_url = comp.get("png_url") or comp.get("png")
                svg_url = comp.get("svg_url") or comp.get("svg")
                png_filename = os.path.basename(png_url) if png_url else ""
                svg_filename = os.path.basename(svg_url) if svg_url else ""

                parent = comp.get("parent", "").strip()
                parent_folder = self.FOLDER_MAP.get(parent, parent)

                if png_url:
                    self._download_asset(png_url, png_filename, "png", parent_folder)
                if svg_url:
                    self._download_asset(svg_url, svg_filename, "svg", parent_folder)

                new_data.append({
                    "id": comp.get("id"),
                    "s_no": s_no,
                    "parent": parent,
                    "name": comp.get("name", "").strip(),
                    "legend": comp.get("legend", ""),
                    "suffix": comp.get("suffix", ""),
                    "object": comp.get("object", "").strip(),
                    "svg": svg_filename,
                    "png": png_filename,
                    "grips": comp.get("grips", ""),
                    "created_by": comp.get("created_by"),
                })

            # Sort by s_no
            try:
                new_data.sort(key=lambda x: int(x["s_no"]) if x["s_no"].isdigit() else x["s_no"])
            except Exception:
                pass

            # Replace component_data atomically
            self.component_data = new_data
            print(f"[SYNC] Loaded {len(new_data)} components from API.")

        except Exception as e:
            print(f"[SYNC ERROR] {e}")

    # _sync_components_with_backend removed — replaced by _load_components_from_api above

    def _download_asset(self, url, filename, asset_type, parent_folder):
        """Helper to download assets if missing."""
        try:
            if not url:
                return

            if not url.startswith("http"):
                url = f"{app_state.BACKEND_BASE_URL}{url}"

            target_dir = os.path.join("ui", "assets", asset_type, parent_folder)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, filename)

            # Only download if missing 
            # (Optimization: We could check file size or headers, but 'exists' is safe for now)
            if not os.path.exists(target_path):
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    with open(target_path, "wb") as f:
                        f.write(res.content)
                    # print(f"[SYNC] Downloaded {asset_type}: {filename}")
                else:
                    print(f"[SYNC WARNING] Failed to download {url} ({res.status_code})")
        except Exception as e:
            print(f"[SYNC ERROR] Failed to download asset {filename}: {e}")


    def _populate_icons(self):
        for i in reversed(range(self.scroll_layout.count())):
            w = self.scroll_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        
        self.icon_buttons.clear()
        self.category_widgets.clear()
        
        grouped = {}
        seen_components = set()
        
        for component in self.component_data:
            parent = component['parent']
            name = component['name']
            
            unique_key = (parent, name, component.get('object', ''))
            
            if unique_key in seen_components:
                continue
            
            seen_components.add(unique_key)
            
            # Additional check: If name is "Filter" in "Fittings", only allow one
            if parent == "Fittings" and name == "Filter":
                filter_key = ("Fittings", "Filter")
                if any(key[:2] == filter_key for key in seen_components if key != unique_key):
                    continue
            
            if parent not in grouped:
                grouped[parent] = []
            grouped[parent].append(component)
        
        for parent_name in sorted(grouped.keys()):
            category_label = QLabel(parent_name)
            category_label.setObjectName("categoryLabel")
            # category_label.setStyleSheet("""
            #     QLabel {
            #         font-size: 8pt;
            #         padding: 5px;
            #         background-color: #f0f0f0;
            #         border-radius: 3px;
            #     }
            # """)
            
            # grid_widget = QWidget()  <-- REPLACED
            grid_widget = FlowContainer()
            
            # Policy is now handled in FlowContainer __init__
            
            flow_layout = FlowLayout(grid_widget, margin=5, hSpacing=5, vSpacing=5)
            # grid_layout.setSpacing(5)
            # grid_layout.setContentsMargins(5, 5, 5, 5)
            # grid_layout.setAlignment(Qt.AlignLeft)
            
            # row, col = 0, 0
            # max_cols = 3  # Changed to 3 columns
            category_cards = []
            
            for component in sorted(grouped[parent_name], key=lambda x: x['name']):
                icon_path = self._get_icon_path(parent_name, component['name'], component.get('object', ''))
                
                if os.path.exists(icon_path):
                    # --- Create Card Frame ---
                    card = QFrame()
                    card.setObjectName("componentCard")
                    card.setProperty('component_name', component['name'])
                    card.setProperty('category', parent_name)
                    
                    card_layout = QVBoxLayout(card)
                    card_layout.setContentsMargins(5, 5, 5, 5)
                    card_layout.setSpacing(2)
                    card_layout.setAlignment(Qt.AlignCenter)
                    
                    # Button (Icon)
                    button = ComponentButton(component, icon_path)
                    button.setContextMenuPolicy(Qt.CustomContextMenu)
                    button.customContextMenuRequested.connect(
                        lambda pos, b=button: self._show_component_context_menu(b, pos)
                    )
                    # Reset button size policy or fixed size if needed, but 56x56 is fine
                    card_layout.addWidget(button, 0, Qt.AlignCenter)
                    
                    # Label (Text)
                    label = QLabel(component['name'])
                    label.setWordWrap(True)
                    label.setAlignment(Qt.AlignCenter)
                    label.setStyleSheet("border: none; background: transparent; font-size: 10px;")
                    card_layout.addWidget(label)
                    
                    # grid_layout.addWidget(card, row, col)
                    flow_layout.addWidget(card)
                    
                    self.icon_buttons.append(button)
                    category_cards.append(card)
                    
                    # col += 1
                    # if col >= max_cols:
                    #     col = 0
                    #     row += 1
            
            if category_cards:
                self.scroll_layout.addWidget(category_label)
                self.scroll_layout.addWidget(grid_widget)
                self.category_widgets.append({
                    'label': category_label,
                    'grid': grid_widget,
                    'cards': category_cards,
                    'name': parent_name
                })

    def event(self, e):
        if isinstance(e, FunctionEvent):
            e.execute()
            return True
        return super().event(e)

    # Mappings for icon path resolution
    FOLDER_MAP = {
        "Furnance and Boilers": "Furnaces and Boilers",
        "Storage Vessels/ Tanks": "Storage Vessels Tanks",
        "Size Reduction Equipments": "Size Reduction Equipements"
    }

    def _get_icon_path(self, parent, name, obj=''):
        csv_row = None
        for c in self.component_data:
            if c["parent"] == parent and c["name"] == name:
                csv_row = c
                break

        backend_png_filename = csv_row.get("png", "") if csv_row else ""

        folder = self.FOLDER_MAP.get(parent, parent)
        local_dir = os.path.join("ui", "assets", "png", folder)
        os.makedirs(local_dir, exist_ok=True)

        if backend_png_filename:
            local_path = os.path.join(local_dir, backend_png_filename)

            if os.path.exists(local_path):
                return local_path

            backend_url = f"{app_state.BACKEND_BASE_URL}/media/components/{backend_png_filename}"

            try:
                r = requests.get(backend_url, timeout=5)
                if r.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(r.content)
                    return local_path
            except Exception as e:
                print("[IMG FETCH ERROR]", e)

        return ""

    
    def _filter_icons(self, search_text):
        search_text = search_text.lower()
        
        if not search_text:
            for category in self.category_widgets:
                category['label'].setVisible(True)
                category['grid'].setVisible(True)
                for card in category['cards']:
                    card.setVisible(True)
            return
        
        for category in self.category_widgets:
            has_match = False
            
            for card in category['cards']:
                component = card.property('component_name').lower()
                category_name = card.property('category').lower()
                
                matches = search_text in component or search_text in category_name
                card.setVisible(matches)
                
                if matches:
                    has_match = True
            
            category['label'].setVisible(has_match)
            category['grid'].setVisible(has_match)

    def _show_update_toast(self):
        toast = ToastMessage(self, "Components updated from backend")
        toast.adjustSize()
        toast.show_toast()

    def _show_component_context_menu(self, button, pos):
        component = button.component_data
        if not component:
            return

        menu = QMenu(self)
        edit_action = menu.addAction("Edit Component")
        delete_action = menu.addAction("Delete Component")

        selected_action = menu.exec_(button.mapToGlobal(pos))

        if selected_action == edit_action:
            self._open_edit_component_dialog(component)
        elif selected_action == delete_action:
            self._delete_component(component)

    def _open_edit_component_dialog(self, component):
        component_id = component.get("id")
        if component_id is None:
            QMessageBox.warning(self, "Edit Component", "Component ID missing. Please sync components and try again.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Component")
        dialog.setModal(True)
        form_layout = QFormLayout(dialog)

        name_input = QLineEdit(component.get("name", ""))
        parent_input = QLineEdit(component.get("parent", ""))
        legend_input = QLineEdit(component.get("legend", ""))
        suffix_input = QLineEdit(component.get("suffix", ""))

        form_layout.addRow("Name", name_input)
        form_layout.addRow("Category", parent_input)
        form_layout.addRow("Legend", legend_input)
        form_layout.addRow("Suffix", suffix_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form_layout.addRow(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return

        updated_name = name_input.text().strip()
        updated_parent = parent_input.text().strip()
        updated_legend = legend_input.text().strip()
        updated_suffix = suffix_input.text().strip()

        if not updated_name or not updated_parent:
            QMessageBox.warning(self, "Edit Component", "Name and Category are required.")
            return

        payload = {
            "s_no": component.get("s_no", ""),
            "name": updated_name,
            "parent": updated_parent,
            "legend": updated_legend,
            "suffix": updated_suffix,
            "object": component.get("object", ""),
            "grips": json.dumps(component.get("grips", [])) if isinstance(component.get("grips"), list) else component.get("grips", "[]"),
        }

        response = api_client.update_component(component_id, payload)
        if response is not None and response.status_code in (200, 202):
            QMessageBox.information(self, "Edit Component", "Component updated successfully.")
            self.reload_components()
            return

        details = ""
        if response is not None:
            try:
                details = response.text
            except Exception:
                details = ""
        error_message = "Failed to update component."
        if details:
            error_message += f"\n\n{details}"
        QMessageBox.critical(self, "Edit Component", error_message)

    def _delete_component(self, component):
        component_id = component.get("id")
        component_name = component.get("name", "Component")

        if component_id is None:
            QMessageBox.warning(self, "Delete Component", "Component ID missing. Please sync components and try again.")
            return

        confirmed = QMessageBox.question(
            self,
            "Delete Component",
            f"Delete '{component_name}'? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmed != QMessageBox.Yes:
            return

        response = api_client.delete_component(component_id)
        if response is not None and response.status_code in (200, 204):
            QMessageBox.information(self, "Delete Component", "Component deleted successfully.")
            self.reload_components()
            return

        details = ""
        if response is not None:
            try:
                details = response.text
            except Exception:
                details = ""
        error_message = "Failed to delete component."
        if details:
            error_message += f"\n\n{details}"
        QMessageBox.critical(self, "Delete Component", error_message)

    def reload_components(self):
        """
        Async reload with loading animation.
        Ensures loader is visible for at least 1 second.
        """
        self._show_loader()

        import time
        start_time = time.time()

        def task():
            # 1. Background work
            self.component_data.clear()
            self._load_components_from_api()

            # 2. Ensure minimum loader time (1 second)
            elapsed = time.time() - start_time
            min_duration = 1.5
            if elapsed < min_duration:
                time.sleep(min_duration - elapsed)

            # 3. Push UI update to main thread
            QApplication.instance().postEvent(
                self,
                FunctionEvent(lambda: (
                    self._populate_icons(),
                    self._hide_loader(),
                    self._show_update_toast(),
                    QTimer.singleShot(3000, self.new_snos.clear)
                ))
            )

        import threading
        threading.Thread(target=task, daemon=True).start()

    def toggle_theme(self):
        """Toggle theme via global theme manager."""
        theme_manager.toggle_theme()

    def on_theme_changed(self, theme):
        """Called when theme changes from theme manager."""
        self.current_library_theme = theme
        self.apply_theme(theme)

    # Update apply_theme to NOT emit signal (theme manager handles it):
    def apply_theme(self, theme):
        """
        Apply theme to component library only.
        DO NOT emit signal - theme manager handles coordination.
        """
        if theme == "dark":
            # --- DARK THEME ---
            bg_main       = "#0f172a"  
            text_main     = "#f8fafc"
            
            # Input
            input_bg      = "#1e293b"
            input_border  = "#3b82f6"
            input_text    = "#ffffff"
            
            # Category Label
            cat_bg        = "#1e293b"
            cat_text      = "#60a5fa"
            cat_border    = "1px solid #334155"
            
            # Component Buttons
            btn_bg        = "#3a5073"
            btn_border    = "#334155"
            btn_hover_bg  = "#334155"
            btn_hover_border = "#60a5fa"
            
            # Scrollbar
            scroll_track  = "#0f172a"
            scroll_handle = "#334155"
            scroll_hover  = "#475569"
            
            toggle_icon_path = os.path.join("ui", "res", "sun.png")

            # Card Styling (Dark)
            card_bg = "#1e293b"
            card_border = "#334155"
            card_text = "#f8fafc"
            card_hover_bg = "#334155"
            card_hover_border = "#60a5fa"

        else:
            # --- LIGHT THEME ---
            bg_main       = "#fffaf5"  
            text_main     = "#3A2A20"
            
            # Input
            input_bg      = "#FFFFFF"
            input_border  = "#C97B5A"
            input_text    = "#3A2A20"

            # Category Label
            cat_bg        = "#faeadd"
            cat_text      = "#8B4731"
            cat_border    = "none"
            
            # Component Buttons
            btn_bg        = "#f4e8dc" 
            btn_border    = "#C97B5A"
            btn_hover_bg  = "#FFFFFF"
            btn_hover_border = "#B06345"
            
            # Scrollbar
            scroll_track  = "#fffaf5"
            scroll_handle = "#E0C0A8"
            scroll_hover  = "#C97B5A"
            
            toggle_icon_path = os.path.join("ui", "res", "moon.png")

            # Card Styling (Light)
            card_bg = "#ffffff"
            card_border = "#e2e8f0"
            card_text = "#334155"
            card_hover_bg = "#eff6ff"
            card_hover_border = "#3b82f6"

        # Icon Logic
        if os.path.exists(toggle_icon_path):
            self.theme_toggle.setIcon(QIcon(toggle_icon_path))
            self.theme_toggle.setText("") 
        else:
            self.theme_toggle.setIcon(QIcon())
            self.theme_toggle.setText("☼" if theme == "dark" else "☾")

        # Apply CSS (same as before)
        self.setStyleSheet(f"""
            ComponentLibrary {{
                background-color: {bg_main};
            }}
            QLabel {{
                color: {text_main};
                font-family: "Segoe UI";
            }}
            
            /* ... rest of your stylesheet ... */
            
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {input_border};
            }}
            
            QScrollArea {{
                border: none;
                background-color: {bg_main};
            }}
            QWidget#scrollWidget {{
                background-color: {bg_main};
            }}
            
            QScrollBar:vertical {{
                border: none;
                background: {scroll_track};
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                border: none;
                background: {scroll_track};
                height: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {scroll_handle};
                min-width: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {scroll_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
            
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
            
            QLabel#categoryLabel {{
                background-color: {cat_bg};
                color: {cat_text};
                border: {cat_border};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                margin-top: 10px;
                margin-bottom: 2px;
            }}
            
            QToolButton {{
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 6px;
                padding: 4px;
            }}

            /* Card Styling */
            QFrame#componentCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                min-height: 90px;
            }}
            QFrame#componentCard:hover {{
                background-color: {card_hover_bg};
                border: 1px solid {card_hover_border};
            }}
            
            QFrame#componentCard QLabel {{
                color: {card_text};
                border: none;
                background: transparent;
                font-size: 10px;
                qproperty-wordWrap: true;
            }}
            /* Hover effects for buttons */
            QToolButton:hover {{
                background-color: {btn_hover_bg};
                border: 1px solid {btn_hover_border};
            }}
            
            ComponentLibrary > QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {text_main}; 
                padding-bottom: 5px;
            }}

            QToolButton#themeToggle {{
                font-size: 16px;
                border: none;
                background: transparent;
                color: {text_main};
            }}
            QToolButton#themeToggle:hover {{
                background: rgba(128, 128, 128, 0.1);
                border-radius: 12px;
            }}
            
            QToolTip {{
                color: {text_main};
                background-color: {bg_main};
                border: 1px solid {input_border};
            }}
        """)

        # Force Style Recompute
        self.style().unpolish(self)
        self.style().polish(self)
        
        for child in self.findChildren(QWidget):
            child.style().unpolish(child)
            child.style().polish(child)

    def changeEvent(self, event):
        """Detect system theme changes."""
        if event.type() in (QEvent.PaletteChange, QEvent.ApplicationPaletteChange):
            theme_manager.on_system_theme_changed()
        super().changeEvent(event)