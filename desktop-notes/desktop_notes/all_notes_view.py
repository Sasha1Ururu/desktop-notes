from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QHBoxLayout, QAbstractItemView, QApplication, QWidget # Added QWidget for main test parent
)
from PyQt6.QtCore import Qt, pyqtSignal

from . import config
from .data_manager import DataManager
# Assuming main_app is the entry point or a manager class that handles widget display
# from .main import DesktopNotesApplet # Avoid direct import if possible, use signals or callbacks

class AllNotesManagementView(QDialog):
    # Signal to request showing/hiding a specific note widget by its ID
    # True to show, False to hide
    request_note_visibility_change = pyqtSignal(int, bool)

    def __init__(self, data_manager, parent_applet_manager=None, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.parent_applet_manager = parent_applet_manager # For emitting signals or direct calls

        self.setWindowTitle("All Notes")
        self.setMinimumSize(500, 300) # Decent default size
        self._init_ui()
        self.populate_notes()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.notes_table = QTableWidget()
        self.notes_table.setColumnCount(3) # ID (hidden), File Path, Status
        self.notes_table.setHorizontalHeaderLabels(["ID", "File Path", "Status"])

        # Hide the ID column, but keep it for internal use
        self.notes_table.setColumnHidden(0, True)

        self.notes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # File path stretches
        self.notes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Status to contents

        self.notes_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.notes_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Read-only table
        self.notes_table.setSortingEnabled(True)

        layout.addWidget(self.notes_table)

        # Buttons (e.g., Close, or maybe Refresh in future)
        # For now, QDialog's default close button is fine. Can add explicit later.
        # self.close_button = QPushButton("Close")
        # self.close_button.clicked.connect(self.accept) # Or self.close
        # layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)

        # Connect cell click for status toggle
        self.notes_table.cellClicked.connect(self._handle_cell_click)


    def populate_notes(self):
        self.notes_table.setSortingEnabled(False) # Disable sorting during population
        self.notes_table.setRowCount(0) # Clear existing rows

        all_notes = self.data_manager.get_all_notes()
        if not all_notes:
            return

        for note_data in all_notes:
            row_position = self.notes_table.rowCount()
            self.notes_table.insertRow(row_position)

            # Column 0: ID (hidden, but useful for mapping back)
            id_item = QTableWidgetItem(str(note_data['id']))
            id_item.setData(Qt.ItemDataRole.UserRole, note_data['id']) # Store ID in item data
            self.notes_table.setItem(row_position, 0, id_item)

            # Column 1: File Path
            filepath_display = note_data.get('filepath', "N/A - No file selected")
            filepath_item = QTableWidgetItem(filepath_display)
            self.notes_table.setItem(row_position, 1, filepath_item)

            # Column 2: Status (with a button for toggling)
            status_widget = QPushButton(note_data.get('status', config.NOTE_STATUS_HIDDEN).capitalize())
            status_widget.setProperty("note_id", note_data['id']) # Store note_id in button
            status_widget.setProperty("current_status", note_data.get('status'))
            status_widget.clicked.connect(self._toggle_note_status_button)

            # Make button flat for better table appearance
            status_widget.setFlat(True)
            # Center the button in the cell
            cell_widget_container = QWidget()
            cell_layout = QHBoxLayout(cell_widget_container)
            cell_layout.addWidget(status_widget)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.setContentsMargins(0,0,0,0)
            self.notes_table.setCellWidget(row_position, 2, cell_widget_container)

        self.notes_table.setSortingEnabled(True)


    def _handle_cell_click(self, row, column):
        # This is an alternative to button clicks if we just want to click the cell.
        # For now, using QPushButton in cell is more explicit.
        # if column == 2: # Status column
        #     note_id_item = self.notes_table.item(row, 0) # Get ID from hidden column
        #     if note_id_item:
        #         note_id = note_id_item.data(Qt.ItemDataRole.UserRole)
        #         current_status_item = self.notes_table.item(row, column) # This would be the text item
        #         current_status_text = current_status_item.text().lower()
        #         self._toggle_note_status(note_id, current_status_text, row, column)
        pass


    def _toggle_note_status_button(self):
        """Handles click from a status button within a table cell."""
        button = self.sender()
        if not button: return

        note_id = button.property("note_id")
        current_status = button.property("current_status")

        if note_id is None or current_status is None: return

        new_status = config.NOTE_STATUS_SHOWN if current_status == config.NOTE_STATUS_HIDDEN else config.NOTE_STATUS_HIDDEN

        if self.data_manager.update_note(note_id, {"status": new_status}):
            print(f"Note {note_id} status changed to {new_status} in DB.")
            button.setText(new_status.capitalize())
            button.setProperty("current_status", new_status)

            # Emit signal to notify the main application/applet manager
            self.request_note_visibility_change.emit(note_id, new_status == config.NOTE_STATUS_SHOWN)
        else:
            print(f"Error updating status for note {note_id} in DB.")
            # TODO: Inform user (e.g., QMessageBox)


    def refresh_notes(self):
        """Public method to reload and display notes, e.g., after external changes."""
        self.populate_notes()


# Example Usage:
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    # --- Mock DataManager ---
    class MockDataManagerForView:
        _notes_data = [
            {"id": 1, "filepath": "/path/to/note1.txt", "status": config.NOTE_STATUS_SHOWN, "style": {}, "position":{}, "size":{}},
            {"id": 2, "filepath": "/path/to/markdown.md", "status": config.NOTE_STATUS_HIDDEN, "style": {}, "position":{}, "size":{}},
            {"id": 3, "filepath": None, "status": config.NOTE_STATUS_SHOWN, "style": {}, "position":{}, "size":{}},
        ]
        def get_all_notes(self):
            print("MockDM_View: get_all_notes() called.")
            return self._notes_data

        def update_note(self, note_id, data):
            print(f"MockDM_View: update_note(note_id={note_id}, data={data}) called.")
            for note in self._notes_data:
                if note['id'] == note_id:
                    note.update(data)
                    return True
            return False

    # --- Mock Applet Manager (to receive signals) ---
    class MockAppletManager(QWidget): # Inherit QWidget to be a valid Qt object for signals
        def __init__(self):
            super().__init__() # Important for QObject initialization for signals/slots
            print("MockAppletManager Initialized")

        def handle_visibility_change(self, note_id, show_widget):
            action = "show" if show_widget else "hide"
            print(f"MockAppletManager: Received request to {action} note ID {note_id}.")
            # In a real app, find the Plasmoid/NoteWidget and show/hide it.

    mock_dm_view = MockDataManagerForView()
    mock_app_manager = MockAppletManager()

    dialog = AllNotesManagementView(data_manager=mock_dm_view, parent_applet_manager=mock_app_manager)

    # Connect the dialog's signal to the mock manager's slot
    dialog.request_note_visibility_change.connect(mock_app_manager.handle_visibility_change)

    dialog.show()
    sys.exit(app.exec())
