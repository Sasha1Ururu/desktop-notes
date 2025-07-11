import sys
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QTextEdit, QApplication, QFrame
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import Qt, pyqtSignal
import markdown # For Markdown rendering
import os # For checking file extension

from .database import get_note, update_note # To load/save note specific data

# Placeholder for Plasma integration. In a real Plasma widget, this would be different.
# For now, QWidget serves as the base.
class NoteWidget(QWidget):
    # Signal to indicate that this widget wants to be closed/deleted
    # For example, if the underlying database entry is removed.
    widgetDeleted = pyqtSignal(int)
    # Signal to request opening file dialog
    requestSelectFile = pyqtSignal(int) # note_id
    # Signal to request opening file in editor
    requestOpenFileInEditor = pyqtSignal(str) # filepath
    # Signals for context menu actions that the container (plasmoid) might need to handle
    requestDragResizeMode = pyqtSignal(int) # note_id
    requestStylingDialog = pyqtSignal(int) # note_id
    requestAddNewNote = pyqtSignal(int) # source note_id
    requestOpenNotesManager = pyqtSignal()
    requestHideWidget = pyqtSignal(int) # note_id
    requestDeleteWidget = pyqtSignal(int) # note_id


    def __init__(self, note_id: int, parent=None):
        super().__init__(parent)
        self.note_id = note_id
        self.note_data = get_note(self.note_id)

        if not self.note_data:
            # This case should ideally be handled before widget creation,
            # but as a fallback, we make an unusable widget.
            print(f"Error: Note with ID {self.note_id} not found in database.")
            self._setup_error_ui("Note data not found.")
            return

        self._init_ui()
        self.load_note_content()

    def _setup_error_ui(self, error_message):
        """Sets up a simple UI to display an error if note data is missing."""
        self.layout = QVBoxLayout(self)
        self.error_label = QLabel(error_message)
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.error_label)
        self.setLayout(self.layout)
        self.setStyleSheet("background-color: #505050; color: white;") # Dark background for error
        self.resize(200,150)


    def _init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool) # Basic frameless window for now
        # In Plasma, it would be a Plasma::Applet

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0) # Will be controlled by note_data's margin

        # Content display area
        self.content_display = QTextEdit()
        self.content_display.setReadOnly(True)
        self.content_display.setFrameStyle(QFrame.Shape.NoFrame) # No border for QTextEdit itself

        self.layout.addWidget(self.content_display)
        self.setLayout(self.layout)

        self._apply_styling()
        self._apply_geometry()

        # Set attributes for transparency if using QWidget directly
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def _apply_geometry(self):
        """Applies position and size from note_data."""
        if not self.note_data: return

        pos = self.note_data.get("position", {"x": 50, "y": 50})
        size = self.note_data.get("size", {"width": 200, "height": 150})
        self.move(pos["x"], pos["y"])
        self.resize(size["width"], size["height"])

    def _apply_styling(self):
        """Applies visual styles from note_data."""
        if not self.note_data: return

        style = self.note_data.get("style", {})
        bg_color_hex = style.get("backgroundColor", "#FFFFE0")
        transparency = style.get("transparency", 1.0)
        margin = style.get("margin", 5)

        # For QWidget background:
        # Convert hex to QColor, then set alpha for transparency
        q_color = QColor(bg_color_hex)
        q_color.setAlphaF(transparency)

        # Update the widget's palette for background color
        # This approach works for top-level QWidget.
        # For Plasma integration, styling might be via QML or specific Plasma APIs.
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, q_color)
        self.setPalette(palette)
        self.setAutoFillBackground(True) # Important for the palette background to show

        # Set content margins for the layout (spacing between window edge and content_display)
        self.layout.setContentsMargins(margin, margin, margin, margin)

        # Text color: For now, let's try to make it readable based on background
        # A more robust solution would be needed for general color choices.
        if q_color.lightness() < 128 : # If background is dark
            self.content_display.setStyleSheet(f"QTextEdit {{ background-color: transparent; color: white; border: none; }}")
        else: # If background is light
            self.content_display.setStyleSheet(f"QTextEdit {{ background-color: transparent; color: black; border: none; }}")


    def load_note_content(self):
        """Loads and displays content from the file specified in note_data or placeholder."""
        if not self.note_data:
            self.show_placeholder("Error: Note data missing.")
            return

        filepath = self.note_data.get("filepath")

        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                _, ext = os.path.splitext(filepath)
                if ext.lower() == '.md':
                    # Basic Markdown rendering
                    html_content = markdown.markdown(content)
                    self.content_display.setHtml(html_content)
                else: # Plain text
                    self.content_display.setPlainText(content)
            except Exception as e:
                self.show_placeholder(f"Error loading file:\n{filepath}\n\n{str(e)}")
                self.content_display.setFont(QFont("Arial", 10)) # Smaller font for error
        else:
            self.show_placeholder("Select File...")
            # Placeholder font as per specs: 22pt
            font = QFont()
            font.setPointSize(22)
            self.content_display.setFont(font)
            self.content_display.setAlignment(Qt.AlignmentFlag.AlignCenter)


    def show_placeholder(self, text: str):
        """Displays placeholder text in the content area."""
        self.content_display.setPlainText(text)
        # Reset alignment and font that might have been set by error/file content
        font = QFont()
        font.setPointSize(22) # Default placeholder font
        self.content_display.setFont(font)
        self.content_display.setAlignment(Qt.AlignmentFlag.AlignCenter)


    def update_and_refresh(self, new_data: dict):
        """Updates the note_data with new_data, saves to DB, and refreshes the widget."""
        if not self.note_data: return False

        # Merge new_data into self.note_data
        # This is a shallow merge, for nested dicts like 'position', 'size', 'style',
        # ensure new_data provides the complete sub-dictionary if any part of it changes.
        for key, value in new_data.items():
            if key in self.note_data:
                if isinstance(self.note_data[key], dict) and isinstance(value, dict):
                    self.note_data[key].update(value)
                else:
                    self.note_data[key] = value
            else: # Allow adding new top-level keys if necessary, though spec is fixed
                self.note_data[key] = value

        if update_note(self.note_id, self.note_data):
            self.refresh_display()
            return True
        return False

    def refresh_display(self):
        """Refreshes the widget's appearance and content based on current self.note_data."""
        self._apply_styling()
        self._apply_geometry() # Position/size might change
        self.load_note_content() # Filepath or content might change
        self.update() # Force repaint

    # --- Interactions (to be expanded in later steps) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.note_data and self.note_data.get("filepath") is None:
                print(f"NoteWidget {self.note_id}: Left-click, no file. Emitting requestSelectFile.")
                self.requestSelectFile.emit(self.note_id)
            elif self.note_data and self.note_data.get("filepath"):
                print(f"NoteWidget {self.note_id}: Left-click, file present. Emitting requestOpenFileInEditor.")
                self.requestOpenFileInEditor.emit(self.note_data["filepath"])
            # Drag logic will be handled when "Drag/Resize" mode is active.
        # Right-click for context menu will be handled by overriding contextMenuEvent
        super().mousePressEvent(event)

    # --- Interface for StylingDialog ---
    def get_current_style_for_dialog(self) -> dict:
        """Returns the 'style' part of note_data for the dialog."""
        if not self.note_data: return {}
        return self.note_data.get("style", {}).copy()

    def update_style_preview(self, style_attribute: str, value: any):
        """Applies a single style attribute for live preview FROM the dialog."""
        if not self.note_data: return

        # Apply change visually without saving to DB yet.
        # Create a temporary style dict based on current note_data's style
        temp_style = self.note_data.get("style", {}).copy()
        temp_style[style_attribute] = value

        # Create a temporary full note_data structure for _apply_styling and _apply_geometry
        # This is a bit heavy-handed if only style changes, but reuses existing methods.
        preview_note_data = {
            "id": self.note_data["id"], # Keep same ID
            "status": self.note_data["status"],
            "filepath": self.note_data["filepath"],
            "position": self.note_data["position"], # Keep same position
            "size": self.note_data["size"],         # Keep same size
            "style": temp_style
        }

        # Temporarily swap self.note_data to use existing styling methods
        original_note_data = self.note_data
        self.note_data = preview_note_data
        try:
            self._apply_styling() # This uses self.note_data
            self.update() # Force repaint
        finally:
            self.note_data = original_note_data # Restore original
        print(f"NoteWidget {self.note_id}: Previewing style '{style_attribute}': {value}")

    def save_style(self, style_data_dict: dict):
        """Saves the complete style dict from the dialog to the database."""
        if not self.note_data: return False

        success = update_note(self.note_id, {"style": style_data_dict})
        if success:
            self.note_data["style"] = style_data_dict.copy() # Update local cache
            self.refresh_display() # Full refresh to apply and repaint
            print(f"NoteWidget {self.note_id}: Style saved and widget refreshed.")
        else:
            print(f"NoteWidget {self.note_id}: Failed to save style to DB.")
        return success

    def revert_style(self, style_data_dict: dict):
        """Reverts to a given style dict (e.g., initial style on cancel) and saves."""
        # "Cancel: Reverts all styling changes ... back to what they were ... Then closes the dialog."
        # This implies the revert should also be persisted.
        return self.save_style(style_data_dict)


    def contextMenuEvent(self, event):
        """Handles right-click to show context menu."""
        if not self.note_data:
            return

        menu = QMenu(self)

        # 1. Select file
        select_file_action = menu.addAction("Select file")
        select_file_action.triggered.connect(lambda: self.requestSelectFile.emit(self.note_id))

        # 2. Drag/Resize
        # This action might toggle a mode managed by the plasmoid or the widget itself.
        # For now, it emits a signal.
        drag_resize_action = menu.addAction("Drag/Resize")
        drag_resize_action.triggered.connect(lambda: self.requestDragResizeMode.emit(self.note_id))

        # 3. Styling
        styling_action = menu.addAction("Styling")
        styling_action.triggered.connect(lambda: self.requestStylingDialog.emit(self.note_id))

        menu.addSeparator()

        # 5. Add New Note
        add_new_note_action = menu.addAction("Add New Note")
        add_new_note_action.triggered.connect(lambda: self.requestAddNewNote.emit(self.note_id))

        # 6. Open Notes (manages all notes)
        open_notes_action = menu.addAction("Open Notes")
        open_notes_action.triggered.connect(lambda: self.requestOpenNotesManager.emit())

        menu.addSeparator()

        # 8. Hide (hides this widget)
        hide_action = menu.addAction("Hide")
        hide_action.triggered.connect(lambda: self.requestHideWidget.emit(self.note_id))

        # 9. Delete (deletes this widget's entry from the app)
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.requestDeleteWidget.emit(self.note_id))

        menu.exec(event.globalPos())


# --- Test Application ---
if __name__ == '__main__':
    from PyQt6.QtWidgets import QMenu # Added for context menu test
    from .database import add_note, delete_note, _init_db, DATABASE_PATH

    # Ensure DB is clean for test
    _init_db(DATABASE_PATH)
    for note in get_note(None) or []: # Assuming get_note(None) would be get_all_notes
        delete_note(note['id'])

    # Create test notes in DB
    note1_id = add_note(filepath=None, position={"x": 50, "y": 50}, size={"width":250, "height":180}, style={"backgroundColor":"#E0E0FF", "margin":10})

    # Create a dummy text file
    test_txt_file = "test_note.txt"
    with open(test_txt_file, "w") as f:
        f.write("This is a plain text file for testing the NoteWidget.\nHello World!")

    # Create a dummy markdown file
    test_md_file = "test_note.md"
    with open(test_md_file, "w") as f:
        f.write("# Markdown Test\n\nThis is a *Markdown* file.\n\n- Item 1\n- Item 2\n\n**Bold Text**")

    note2_id = add_note(filepath=os.path.abspath(test_txt_file), position={"x":350, "y":50}, size={"width":300, "height":200}, style={"transparency":0.8, "backgroundColor":"#D0F0D0"})
    note3_id = add_note(filepath=os.path.abspath(test_md_file), position={"x":50, "y":300}, size={"width":300, "height":250}, style={"margin":15, "backgroundColor":"#2c3e50", "transparency": 0.9})


    app = QApplication(sys.argv)

    widget1 = NoteWidget(note_id=note1_id)
    widget1.setWindowTitle(f"Note ID: {note1_id} (Placeholder)")
    widget1.show()

    widget2 = NoteWidget(note_id=note2_id)
    widget2.setWindowTitle(f"Note ID: {note2_id} (Text File)")
    widget2.show()

    widget3 = NoteWidget(note_id=note3_id)
    widget3.setWindowTitle(f"Note ID: {note3_id} (Markdown File)")
    widget3.show()

    # Test updating a widget
    def test_update_widget1():
        print("Updating widget 1's content and style after 3 seconds...")
        new_data_widget1 = {
            "filepath": os.path.abspath(test_txt_file), # Change to show text file
            "style": {"backgroundColor": "#FFDDC1", "margin": 20, "transparency": 0.95}
        }
        widget1.update_and_refresh(new_data_widget1)
        # Check if data in db is updated
        updated_db_data = get_note(note1_id)
        print(f"Widget 1 data in DB after update: {updated_db_data['filepath']}, {updated_db_data['style']}")


    from PyQt6.QtCore import QTimer
    QTimer.singleShot(3000, test_update_widget1)


    sys.exit(app.exec())

    # Clean up dummy files
    # os.remove(test_txt_file)
    # os.remove(test_md_file)
    # print("Cleaned up test files.")
    # Need to delete notes from db too for full cleanup, or handle in database.py test section
    # delete_note(note1_id)
    # delete_note(note2_id)
    # delete_note(note3_id)
    # print("Cleaned up test notes from DB.")
