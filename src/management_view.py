import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QPushButton, QDialogButtonBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal

# Assuming database functions are in a sibling directory 'src' if this file is also in 'src'
# For direct execution, path adjustments might be needed if 'src' is not in PYTHONPATH
try:
    from .database import get_all_notes, update_note, get_note
except ImportError:
    # Fallback for direct execution if src module is not found easily
    print("Attempting fallback import for database due to potential direct execution.")
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # Go up to project root
    from src.database import get_all_notes, update_note, get_note


class ManagementView(QDialog):
    # Signal emitted when a note's status is changed by this dialog.
    # The main app/plasmoid controller would listen to this to show/hide actual widgets.
    # Arguments: note_id (int), new_status (str: "shown" or "hidden")
    note_status_changed_externally = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage All Notes")
        self.setMinimumSize(600, 400)

        self.layout = QVBoxLayout(self)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(3) # ID (hidden), File Path, Status
        self.table_widget.setHorizontalHeaderLabels(["ID", "File Path", "Status"])
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Read-only display
        self.table_widget.setSortingEnabled(True)

        # Hide the ID column, but keep it for internal use
        self.table_widget.setColumnHidden(0, True)

        # Stretch File Path column
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.table_widget.itemClicked.connect(self._handle_item_click)

        self.layout.addWidget(self.table_widget)

        self.refresh_button = QPushButton("Refresh List")
        self.refresh_button.clicked.connect(self.populate_notes)
        self.layout.addWidget(self.refresh_button)

        # Standard OK button to close
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)
        self.populate_notes()

    def populate_notes(self):
        self.table_widget.setSortingEnabled(False) # Disable sorting during population
        self.table_widget.setRowCount(0) # Clear existing rows

        notes = get_all_notes()
        if notes is None: # Ensure notes is iterable
            notes = []

        for note_data in notes:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)

            # Column 0: ID (hidden)
            id_item = QTableWidgetItem(str(note_data["id"]))
            id_item.setData(Qt.ItemDataRole.UserRole, note_data["id"]) # Store ID for retrieval
            self.table_widget.setItem(row_position, 0, id_item)

            # Column 1: File Path
            filepath = note_data.get("filepath", "N/A - No file selected")
            if not filepath: filepath = "N/A - No file selected"
            filepath_item = QTableWidgetItem(filepath)
            self.table_widget.setItem(row_position, 1, filepath_item)

            # Column 2: Status
            status = note_data.get("status", "unknown").capitalize()
            status_item = QTableWidgetItem(status)
            # Make status item checkable or clickable for toggling
            # For simplicity, we handle click on the item itself.
            self.table_widget.setItem(row_position, 2, status_item)

        self.table_widget.setSortingEnabled(True)

    def _handle_item_click(self, item: QTableWidgetItem):
        if item.column() == 2: # Clicked on the Status column
            row = item.row()
            note_id_item = self.table_widget.item(row, 0) # Get ID from hidden column
            if not note_id_item: return

            note_id = note_id_item.data(Qt.ItemDataRole.UserRole)
            current_status_text = item.text().lower() # "Shown" or "Hidden"

            new_status = "hidden" if current_status_text == "shown" else "shown"

            print(f"ManagementView: Toggling status for note ID {note_id} from '{current_status_text}' to '{new_status}'")

            if update_note(note_id, {"status": new_status}):
                print(f"  DB updated successfully for note ID {note_id}.")
                # Update the table item text
                item.setText(new_status.capitalize())
                # Emit signal so main application can react (e.g., show/hide actual widget)
                self.note_status_changed_externally.emit(note_id, new_status)
                print(f"  Emitted note_status_changed_externally({note_id}, '{new_status}')")
            else:
                print(f"  Error updating status in DB for note ID {note_id}.")
                # Optionally, show an error message to the user

        # Allow default click behavior (e.g. selection)
        # super().itemClicked(item) if QTableWidget had such a method directly.
        # For QTableWidget, itemClicked is a signal, not an overridable method.

if __name__ == '__main__':
    # Add some dummy data to the database for testing
    try:
        from .database import _init_db, add_note, delete_note, DATABASE_PATH
        _init_db(DATABASE_PATH) # Ensure DB exists

        # Clean up old test notes if any
        for old_note in get_all_notes() or []:
            delete_note(old_note['id'])

        add_note(filepath="/test/file1.txt", status="shown", position={"x":10,"y":10}, size={"width":100,"height":100})
        add_note(filepath="/another/file2.md", status="hidden", position={"x":20,"y":20}, size={"width":120,"height":120})
        add_note(filepath=None, status="shown", position={"x":30,"y":30}, size={"width":150,"height":150})
        print("Dummy notes added to database for testing ManagementView.")

    except ImportError as e:
        print(f"Could not import database for dummy data setup: {e}")
    except Exception as e_db:
        print(f"Error setting up dummy database data: {e_db}")


    app = QApplication(sys.argv)
    dialog = ManagementView()

    def handle_external_status_change(note_id, new_status):
        print(f"--- Main App (Test): Received signal! Note ID: {note_id}, New Status: {new_status} ---")
        # Here, a real application would find the corresponding plasmoid and show/hide it.
        # For example:
        # target_plasmoid = find_plasmoid_by_note_id(note_id)
        # if target_plasmoid:
        #     if new_status == "shown": target_plasmoid.show()
        #     else: target_plasmoid.hide()
        # else: if new_status == "shown": create_new_plasmoid_for_note(note_id)

    dialog.note_status_changed_externally.connect(handle_external_status_change)

    dialog.show() # Show non-modally for testing interaction
    # Or dialog.exec() for modal

    sys.exit(app.exec())
