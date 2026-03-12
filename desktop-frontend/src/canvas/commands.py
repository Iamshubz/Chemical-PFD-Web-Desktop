"""
File operation and Undo/Redo commands for canvas.
"""
import os
from PyQt5.QtWidgets import QUndoCommand, QMessageBox, QFileDialog
from src.canvas.export import ( load_from_pfd, 
    export_to_image, export_to_pdf, generate_report_pdf,
    export_to_excel, save_canvas_state
)
from src.canvas.validation import GraphValidator
from src.api_client import delete_project
from src.toast import show_toast


def _build_validation_message(canvas):
    validator = GraphValidator(canvas.components, canvas.connections)
    errors = validator.validate()

    parts = []
    if errors.get("missing_inlet"):
        parts.append("⚠ Missing inlet")
    if errors.get("missing_outlet"):
        parts.append("⚠ Missing outlet")
    if errors.get("isolated"):
        parts.append(f"⚠ {len(errors['isolated'])} isolated")
    if errors.get("loops"):
        parts.append(f"⚠ {len(errors['loops'])} loop")
    if errors.get("flow_errors"):
        parts.append(f"⚠ {len(errors['flow_errors'])} flow error")

    return " | ".join(parts)

# ---------------------- UNDO COMMANDS ----------------------

class AddCommand(QUndoCommand):
    def __init__(self, canvas, component, pos):
        super().__init__()
        self.canvas = canvas
        self.component = component
        # Assuming pos is LOGICAL position passed from CanvasWidget
        self.component.logical_rect.moveTo(pos.x(), pos.y())
        if hasattr(self.canvas, "zoom_level"):
            self.component.update_visuals(self.canvas.zoom_level)
        self.setText(f"Add {component.config.get('component', 'Component')}")

    def redo(self):
        if self.component not in self.canvas.components:
            self.canvas.components.append(self.component)
            self.component.show()
            self.canvas.update()

    def undo(self):
        if self.component in self.canvas.components:
            self.canvas.components.remove(self.component)
            self.component.hide()
            self.canvas.update()

class AddConnectionCommand(QUndoCommand):
    def __init__(self, canvas, connection):
        super().__init__()
        self.canvas = canvas
        self.connection = connection
        self.setText("Add Connection")

    def redo(self):
        if self.connection not in self.canvas.connections:
            self.canvas.connections.append(self.connection)
            
            # Enable smart auto-routing for new connections
            if hasattr(self.connection, 'enable_auto_router'):
                self.connection.enable_auto_router(True)
                # Recalculate path with auto-routing enabled
                self.connection.update_path(self.canvas.components, self.canvas.connections)
            
            self.canvas.update()

            message = _build_validation_message(self.canvas)
            if message:
                show_toast(message, duration=3000)

    def undo(self):
        if self.connection in self.canvas.connections:
            self.canvas.connections.remove(self.connection)
            self.canvas.update()

class DeleteCommand(QUndoCommand):
    def __init__(self, canvas, components, connections):
        super().__init__()
        self.canvas = canvas
        self.components = components
        self.connections = connections
        self.setText(f"Delete {len(components)} items")

    def redo(self):
        for conn in self.connections:
            if conn in self.canvas.connections:
                self.canvas.connections.remove(conn)
        for comp in self.components:
            if comp in self.canvas.components:
                self.canvas.components.remove(comp)
                comp.hide()
        self.canvas.update()

    def undo(self):
        for comp in self.components:
            if comp not in self.canvas.components:
                self.canvas.components.append(comp)
                comp.show()
        for conn in self.connections:
            if conn not in self.canvas.connections:
                self.canvas.connections.append(conn)
        self.canvas.update()

class MoveCommand(QUndoCommand):
    def __init__(self, component, old_pos, new_pos):
        super().__init__()
        self.component = component
        self.old_pos = old_pos # Expecting LOGICAL pos
        self.new_pos = new_pos # Expecting LOGICAL pos
        self.setText(f"Move {component.config.get('component', 'Component')}")

    def redo(self):
        self.component.logical_rect.moveTo(self.new_pos.x(), self.new_pos.y())
        canvas = self.component.parent()
        z = canvas.zoom_level if hasattr(canvas, "zoom_level") else 1.0
        self.component.update_visuals(z)
        
        # Trigger connection re-routing for all connected connections
        self._update_connected_connections(canvas)
        
        canvas.update()

    def undo(self):
        self.component.logical_rect.moveTo(self.old_pos.x(), self.old_pos.y())
        canvas = self.component.parent()
        z = canvas.zoom_level if hasattr(canvas, "zoom_level") else 1.0
        self.component.update_visuals(z)
        
        # Trigger connection re-routing for all connected connections
        self._update_connected_connections(canvas)
        
        canvas.update()
    
    def _update_connected_connections(self, canvas):
        """
        Update all connections attached to this component.
        Triggers auto-routing and visual path recalculation.
        
        Args:
            canvas: The CanvasWidget containing components and connections
        """
        if not hasattr(canvas, 'connections'):
            return
        
        for conn in canvas.connections:
            # Check if connection is attached to this component
            if conn.start_component == self.component or conn.end_component == self.component:
                # Recalculate connection path with auto-routing
                conn.update_path(canvas.components, canvas.connections)


# ---------------------- FILE OPERATIONS ----------------------
def save_project(canvas, filename):
    """Saves project - ONLY for legacy .pfd files."""
    from src.canvas.export import save_to_pfd
    save_to_pfd(canvas, filename)
    canvas.file_path = filename
    canvas.undo_stack.setClean()


def open_project(canvas, filename):
    """Opens project from .pfd file."""
    if load_from_pfd(canvas, filename):
        canvas.file_path = filename
        canvas.undo_stack.clear()
        return True
    return False

def handle_close_event(canvas, event):
    """Handles window close event with unsaved changes check."""
    if canvas.is_modified:
        reply = QMessageBox.question(
            canvas, 'Save Changes?',
            "There are unsaved changes in the current project.\nWould you like to save them before closing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save
        )

        if reply == QMessageBox.Save:
            # Try to save to backend if project_id exists
            if hasattr(canvas, 'project_id') and canvas.project_id:
                import src.app_state as app_state
                app_state.current_project_id = canvas.project_id
                app_state.current_project_name = canvas.project_name
                
                result = save_canvas_state(canvas)
                if result:
                    # Update flag on success
                    if hasattr(canvas, 'is_new_project'):
                        canvas.is_new_project = False
                    event.accept()
                else:
                    QMessageBox.critical(canvas, "Error", "Failed to save project.")
                    event.ignore()
            # Otherwise save to file
            elif canvas.file_path:
                save_project(canvas, canvas.file_path)
                event.accept()
            else:
                # Ask for filename
                options = QFileDialog.Options()
                filename, _ = QFileDialog.getSaveFileName(
                    canvas, "Save Project", "", 
                    "Process Flow Diagram (*.pfd)", 
                    options=options
                )
                if filename:
                    if not filename.lower().endswith(".pfd"):
                        filename += ".pfd"
                    save_project(canvas, filename)
                    event.accept()
                else:
                    event.ignore()
                    
        elif reply == QMessageBox.Discard:
            # Delete if it was a new unsaved project ---
            if hasattr(canvas, 'is_new_project') and canvas.is_new_project and canvas.project_id:
                print(f"[CLOSE] Discarding new project {canvas.project_id}. Deleting from backend...")
                delete_project(canvas.project_id)
            event.accept()
        else:
            event.ignore()
    else:
        # If it wasn't modified, but it's NEW (empty/fresh), we might also want to delete it?
        # Usually, if you open a new project and close it immediately without touching it (is_modified=False),
        # you probably don't want to keep that empty project ID.
        if hasattr(canvas, 'is_new_project') and canvas.is_new_project and canvas.project_id:
             print(f"[CLOSE] Discarding empty/untouched new project {canvas.project_id}.")
             delete_project(canvas.project_id)
        event.accept()

def export_image(canvas, filename):
    export_to_image(canvas, filename)

def export_pdf(canvas, filename):
    export_to_pdf(canvas, filename)

def generate_report(canvas, filename):
    generate_report_pdf(canvas, filename)

def export_excel(canvas, filename):
    export_to_excel(canvas, filename)
