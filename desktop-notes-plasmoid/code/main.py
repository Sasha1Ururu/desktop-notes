import os
from PyKDE5.Plasma import Plasma
from PyKDE5.Plasma.Plasmoid import Applet
from PyQt5.QtCore import pyqtProperty, pyqtSignal, QUrl, QObject, QPoint, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMenu, QFileDialog # For context menu and file dialog

# Assuming data_model.py is in the same directory or Python path
try:
    from .data_model import Note, add_note, get_note_by_id, update_note, delete_note, generate_unique_id
except ImportError:
    from data_model import Note, add_note, get_note_by_id, update_note, delete_note, generate_unique_id


class DesktopNotesApplet(Applet, QObject):
    # Signals to update QML
    filepathChanged = pyqtSignal()
    statusChanged = pyqtSignal()
    noteContentChanged = pyqtSignal()
    backgroundColorChanged = pyqtSignal()
    transparencyChanged = pyqtSignal()
    marginChanged = pyqtSignal()
    showPlaceholderChanged = pyqtSignal()

from PyQt5.QtCore import QAbstractListModel, Qt, QModelIndex # For ListModel

# ... (other imports)

class NoteListModel(QAbstractListModel):
    IdRole = Qt.UserRole + 1
    FilepathRole = Qt.UserRole + 2
    StatusRole = Qt.UserRole + 3
    LastModifiedRole = Qt.UserRole + 4 # Optional

    def __init__(self, data=None, parent=None):
        super(NoteListModel, self).__init__(parent)
        self._data = data or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return None

        note_item = self._data[index.row()]

        if role == self.IdRole:
            return note_item.get("note_id_prop")
        elif role == self.FilepathRole:
            return note_item.get("filepath_prop", "N/A")
        elif role == self.StatusRole:
            return note_item.get("status_prop", "unknown")
        elif role == self.LastModifiedRole:
            return note_item.get("last_modified_prop", "") # Optional
        return None

    def roleNames(self):
        # These must match the 'role' strings used in TableViewColumn in QML
        return {
            self.IdRole: b'note_id_prop',
            self.FilepathRole: b'filepath_prop',
            self.StatusRole: b'status_prop',
            self.LastModifiedRole: b'last_modified_prop'
        }

    def updateData(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def setData(self, index, value, role):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return False

        note_item = self._data[index.row()]
        changed = False
        if role == self.StatusRole:
            if note_item["status_prop"] != value:
                note_item["status_prop"] = value
                changed = True
        # Add other roles if direct editing from model is needed

        if changed:
            self.dataChanged.emit(index, index, [role])
            return True
        return False


# In DesktopNotesApplet class:
    # Signals for specific actions that QML might need to react to (e.g., opening dialogs)
    requestStylingDialog = pyqtSignal(str, str, float, int) # noteId, bgColor, transparency, margin
    requestManagementView = pyqtSignal(QObject) # Pass the model as QObject
    dragResizeModeToggled = pyqtSignal(bool)

    def __init__(self, parent, args=None):
        Applet.__init__(self, parent)
        QObject.__init__(self)

        self.appletInstanceId = None
        if args and hasattr(args, "get"):
             self.appletInstanceId = args.get("id")
        elif args and isinstance(args, (list, tuple)) and len(args) > 0 and hasattr(args[0], "get"):
             self.appletInstanceId = args[0].get("id")

        print(f"Initializing DesktopNotesApplet with instance ID: {self.appletInstanceId}")

        self._note_id = None
        self._note = None

        self._filepath = ""
        self._status = "shown" # Default status
        self._note_content = ""
        self._show_placeholder = True

        self._backgroundColor = QColor("#333333")
        self._transparency = 0.8
        self._margin = 10

        self._drag_resize_mode = False # Internal state for drag/resize
        self._management_view_model = None # To hold the ListModel for the management view

    def init(self):
        # It's important Applet.init(self) is called, often it calls self.initQml()
        # which loads the QML file specified in metadata.json.
        # The context property must be set before QML tries to access it.
        self.rootContext().setContextProperty("plasmoid", self)
        Applet.init(self) # Call base Applet's init.

        self.setHasConfigurationInterface(False)
        self.setAspectRatioMode(Plasma.AspectRatioMode.Free)

        self.load_note_data()


    def load_note_data(self):
        config = self.configuration() # Plasma.ConfigGroup for this applet instance

        # Try to read our internal note_id from the plasmoid's persistent configuration
        self._note_id = config.readEntry("noteId", None) # Returns default if not found

        if self._note_id:
            print(f"Instance {self.appletInstanceId}: Found stored noteId '{self._note_id}' in instance config.")
            self._note = get_note_by_id(self._note_id)
            if not self._note:
                print(f"Instance {self.appletInstanceId}: Stored noteId '{self._note_id}' not found in DB! Treating as new note.")
                config.deleteEntry("noteId") # Remove invalid ID
                self._note_id = None # Fall through to new note creation
                # No sync needed for deleteEntry immediately, writeEntry will sync.
            else:
                print(f"Instance {self.appletInstanceId}: Successfully loaded note '{self._note_id}' from DB.")
        else:
            print(f"Instance {self.appletInstanceId}: No noteId found in instance config.")
            # self._note_id is None, so will proceed to create a new note.

        if not self._note_id: # Handles both "not found in config" and "found but invalid in DB"
            print(f"Instance {self.appletInstanceId}: Creating new note.")
            new_note = Note(
                applet_instance_id=self.appletInstanceId, # Store Plasma's ID if useful for future mapping
                filepath=None,
            )
            if add_note(new_note):
                self._note_id = new_note.id
                self._note = new_note
                # Store the new note_id in this plasmoid instance's persistent configuration
                config.writeEntry("noteId", self._note_id)
                config.sync() # Ensure it's written to disk
                print(f"Instance {self.appletInstanceId}: New note created with ID '{self._note_id}' and saved to instance config.")
            else:
                print(f"Instance {self.appletInstanceId}: Failed to create new note in DB.")
                self._show_placeholder = True
                self.showPlaceholderChanged.emit()
                return
        else:
            print(f"Found note_id {self._note_id} for instance {self.appletInstanceId}. Loading.")
            self._note = get_note_by_id(self._note_id)
            if not self._note:
                print(f"Error: Note with ID {self._note_id} not found in DB. Clearing association.")
                # config.deleteEntry("noteId")
                # config.sync()
                self._note_id = None
                self.load_note_data() # Attempt to create a new one
                return

        if self._note:
            self._filepath = self._note.filepath if self._note.filepath else ""
            self._status = self._note.status
            self._backgroundColor = QColor(self._note.style.get("backgroundColor", "#333333"))
            self._transparency = self._note.style.get("transparency", 0.8)
            self._margin = self._note.style.get("margin", 10)

            if self._filepath and os.path.exists(self._filepath):
                self._show_placeholder = False
                self.load_file_content()
            else:
                if self._filepath and not os.path.exists(self._filepath): # Filepath set but file missing
                    self._note_content = f"File not found:\n{self._filepath}"
                    self._show_placeholder = False # Show error, not placeholder
                else: # No filepath
                    self._show_placeholder = True
                    self._note_content = "Select File..."

            self.filepathChanged.emit()
            self.statusChanged.emit() # Emit current status
            self.noteContentChanged.emit()
            self.backgroundColorChanged.emit()
            self.transparencyChanged.emit()
            self.marginChanged.emit()
            self.showPlaceholderChanged.emit()

    # --- QML Exposed Properties ---
    @pyqtProperty(str, notify=filepathChanged)
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, path):
        if self._filepath != path:
            self._filepath = path
            self._note.filepath = path # Update Note object

            if self._filepath and os.path.exists(self._filepath):
                self._show_placeholder = False
                self.load_file_content()
            elif self._filepath and not os.path.exists(self._filepath):
                self._show_placeholder = False # Show error, not placeholder
                self._note_content = f"File not found:\n{self._filepath}"
            else: # Path is empty
                self._show_placeholder = True
                self._note_content = "Select File..."

            if update_note(self._note):
                print(f"Note {self._note.id} filepath updated to {path}")
            else:
                print(f"Failed to update note {self._note.id} filepath in DB.")

            self.filepathChanged.emit()
            self.showPlaceholderChanged.emit()
            self.noteContentChanged.emit()

    @pyqtProperty(str, notify=noteContentChanged)
    def noteContent(self):
        return self._note_content

    @pyqtProperty(bool, notify=showPlaceholderChanged)
    def showPlaceholder(self):
        return self._show_placeholder

    @pyqtProperty(QColor, notify=backgroundColorChanged)
    def backgroundColor(self):
        return self._backgroundColor

    @backgroundColor.setter
    def backgroundColor(self, color_name_or_obj):
        new_color = QColor(color_name_or_obj)
        if self._backgroundColor != new_color:
            self._backgroundColor = new_color
            self._note.style["backgroundColor"] = self._backgroundColor.name()
            update_note(self._note)
            self.backgroundColorChanged.emit()

    @pyqtProperty(float, notify=transparencyChanged)
    def transparency(self):
        return self._transparency

    @transparency.setter
    def transparency(self, value):
        if self._transparency != value:
            self._transparency = value
            self._note.style["transparency"] = value
            update_note(self._note)
            self.transparencyChanged.emit()

    @pyqtProperty(int, notify=marginChanged)
    def margin(self):
        return self._margin

    @margin.setter
    def margin(self, value):
        if self._margin != value:
            self._margin = value
            self._note.style["margin"] = value
            update_note(self._note)
            self.marginChanged.emit()

    @pyqtProperty(str, notify=statusChanged)
    def status(self):
        return self._status

    @pyqtProperty(bool, notify=dragResizeModeToggled)
    def dragResizeModeActive(self):
        return self._drag_resize_mode

    # --- Helper Methods ---
    def load_file_content(self):
        if not self._filepath: # Should not happen if called correctly
            self._show_placeholder = True
            self._note_content = "Select File..."
            self.showPlaceholderChanged.emit()
            self.noteContentChanged.emit()
            return

        if not os.path.exists(self._filepath):
            self._note_content = f"File not found:\n{self._filepath}"
            self._show_placeholder = False # Show the error message
            self.showPlaceholderChanged.emit()
            self.noteContentChanged.emit()
            return

        try:
            with open(self._filepath, 'r', encoding='utf-8') as f:
                self._note_content = f.read()
        except Exception as e:
            self._note_content = f"Error reading file:\n{str(e)}"

        self.noteContentChanged.emit()

    # --- Context Menu Action Handlers ---
    def onActionSelectFile(self):
        self.selectFile()

    def onActionDragResize(self):
        self._drag_resize_mode = not self._drag_resize_mode
        print(f"Action: Drag/Resize toggled. Mode active: {self._drag_resize_mode} (Note: {self._note_id})")
        self.dragResizeModeToggled.emit(self._drag_resize_mode)
        # QML will handle visual cues based on a property bound to _drag_resize_mode or this signal.

    def onActionStyling(self):
        print(f"Action: Styling triggered for note {self._note_id}")
        if self._note:
            bg_color_str = self._note.style.get("backgroundColor", "#333333")
            transparency_val = self._note.style.get("transparency", 0.8)
            margin_val = self._note.style.get("margin", 10)
            # Emit current style values to the QML dialog
            self.requestStylingDialog.emit(self._note_id, bg_color_str, transparency_val, margin_val)
        else:
            print(f"Error: Styling request for note {self._note_id}, but note data not loaded.")


    @pyqtSlot(str, str, 'QVariant') # noteId, propertyName, value
    def handleStyleChangeFromDialog(self, note_id, property_name, value):
        if self._note_id != note_id:
            print(f"Style change received for {note_id}, but current note is {self._note_id}. Ignoring.")
            return

        print(f"Received style update from dialog for note {self._note_id}: {property_name} = {value}")
        changed = False
        if property_name == "backgroundColor":
            new_color = QColor(value)
            if self._backgroundColor != new_color:
                self._backgroundColor = new_color
                self._note.style["backgroundColor"] = new_color.name()
                self.backgroundColorChanged.emit()
                changed = True
        elif property_name == "transparency":
            new_transparency = float(value)
            if self._transparency != new_transparency:
                self._transparency = new_transparency
                self._note.style["transparency"] = new_transparency
                self.transparencyChanged.emit()
                changed = True
        elif property_name == "margin":
            new_margin = int(value)
            if self._margin != new_margin:
                self._margin = new_margin
                self._note.style["margin"] = new_margin
                self.marginChanged.emit()
                changed = True

        if changed and self._note:
            if update_note(self._note):
                print(f"Note {self._note_id} style '{property_name}' updated in DB.")
            else:
                print(f"Failed to update note {self._note_id} style '{property_name}' in DB.")
        elif not self._note:
            print("Error: Cannot update style, self._note is not loaded.")


    def onActionAddNewNote(self):
        print("Action: Add New Note triggered")
        # Plasma shell interaction (e.g., D-Bus call to containment) is needed here.
        # Example: containment.addApplet("org.kde.plasma.desktopnotes", arguments, x, y)
        # Geometry calculation for placement:
        # if self.view() and hasattr(self.view(), "geometry"):
        #     current_geometry = self.view().geometry()
        #     new_x = current_geometry.right() + 10
        #     new_y = current_geometry.top()
        #     print(f"Placeholder: Request new plasmoid near x={new_x}, y={new_y}")
        # else:
        print("Placeholder: Logic to request new plasmoid instance from Plasma shell.")

    def onActionOpenNotes(self):
        print(f"Action: Open Notes (Management View) triggered for main plasmoid instance {self.appletInstanceId}")
        all_db_notes = get_all_notes() # From data_model

        model_data = []
        for note_obj in all_db_notes:
            filepath_display = note_obj.filepath if note_obj.filepath else "Note (no file)"
            # Try to get last modified time for the file if it exists
            last_modified_str = ""
            if note_obj.filepath and os.path.exists(note_obj.filepath):
                try:
                    timestamp = os.path.getmtime(note_obj.filepath)
                    # Format it nicely, e.g., YYYY-MM-DD HH:MM
                    from datetime import datetime
                    last_modified_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
                except Exception as e:
                    print(f"Could not get mtime for {note_obj.filepath}: {e}")
                    last_modified_str = "N/A"

            model_data.append({
                "note_id_prop": note_obj.id,
                "filepath_prop": filepath_display,
                "status_prop": note_obj.status,
                "last_modified_prop": last_modified_str
            })

        if self._management_view_model is None:
            self._management_view_model = NoteListModel(model_data, parent=self) # Parent it to applet
        else:
            self._management_view_model.updateData(model_data)

        self.requestManagementView.emit(self._management_view_model)

    @pyqtSlot(str, bool) # noteId, newIsShownStatus (true for "shown", false for "hidden")
    def handleToggleNoteStatus(self, note_id, new_is_shown):
        print(f"Request to toggle status for note {note_id} to {'shown' if new_is_shown else 'hidden'}")
        target_note = get_note_by_id(note_id)
        if not target_note:
            print(f"Error: Cannot toggle status, note {note_id} not found in DB.")
            return

        new_status_str = "shown" if new_is_shown else "hidden"
        if target_note.status == new_status_str:
            print(f"Note {note_id} is already {new_status_str}. No change.")
            return

        target_note.status = new_status_str
        if update_note(target_note):
            print(f"Note {note_id} status updated to {new_status_str} in DB.")

            # Update the model if it's active
            if self._management_view_model:
                for i in range(self._management_view_model.rowCount()):
                    index = self._management_view_model.index(i, 0)
                    if self._management_view_model.data(index, NoteListModel.IdRole) == note_id:
                        # Corrected typo: NoteListModel.StatusRole
                        self._management_view_model.setData(index, new_status_str, NoteListModel.StatusRole)
                        break

            # If the toggled note is the current plasmoid's note, update its own state
            if self._note_id == note_id:
                self._status = new_status_str
                self.statusChanged.emit()
                if hasattr(self, 'setVisible'):
                    self.setVisible(new_is_shown) # Show/hide the current widget

            # This is where Plasma-specific logic would be needed to show/hide *other*
            # plasmoid instances if their status changed. This is complex and might involve:
            # - D-Bus communication with a central service or other plasmoid instances.
            # - The plasmoid manager being aware of note IDs and their corresponding widget instances.
            # For now, this action primarily updates the DB and the current widget if it's the one affected.
            # Other widgets would need to poll or be notified to reflect their new status.
            # A simple approach for other widgets is that they would re-check their status on some trigger,
            # or if the main DesktopNotesApplet class could somehow iterate over all its instances (not standard).
            print(f"Note {note_id} status toggled. Current widget ({self._note_id}) visibility updated if it was the target. Other widgets need a mechanism to reflect this change.")

        else:
            print(f"Failed to update status for note {note_id} in DB.")


    def onActionHide(self):
        print(f"Action: Hide triggered for note {self._note_id}")
        if self._note:
            self._note.status = "hidden"
            if update_note(self._note):
                self._status = "hidden"
                self.statusChanged.emit()
                if hasattr(self, 'setVisible'): # Applet's method
                    self.setVisible(False) # Attempt to make the plasmoid invisible
                print(f"Note {self._note_id} status set to hidden. Plasmoid setVisible(False) called.")
            else:
                print(f"Failed to update note {self._note_id} status to hidden in DB.")

    def onActionDelete(self):
        print(f"Action: Delete triggered for note {self._note_id}")
        if self._note_id:
            # Consider confirmation dialog in a real app
            if delete_note(self._note_id): # data_model.delete_note
                print(f"Note {self._note_id} deleted from DB.")
                if hasattr(self, 'remove'): # Applet's method
                    self.remove() # Request Plasma to remove this applet instance
                    print(f"Plasmoid instance for note {self._note_id} self.remove() called.")
            else:
                print(f"Failed to delete note {self._note_id} from DB.")

    # --- QML Invokable Methods ---
    @pyqtSlot(int, int)
    def showContextMenu(self, qml_x, qml_y):
        menu = QMenu(self.view()) # Parent the menu to the view

        menu.addAction("Select file").triggered.connect(self.onActionSelectFile)

        # Toggle text for Drag/Resize
        drag_resize_action_text = "Exit Drag/Resize" if self._drag_resize_mode else "Drag/Resize"
        menu.addAction(drag_resize_action_text).triggered.connect(self.onActionDragResize)

        menu.addAction("Styling").triggered.connect(self.onActionStyling)
        menu.addSeparator()
        menu.addAction("Add New Note").triggered.connect(self.onActionAddNewNote)
        menu.addAction("Open Notes").triggered.connect(self.onActionOpenNotes) # Manages all notes
        menu.addSeparator()
        menu.addAction("Hide").triggered.connect(self.onActionHide) # Hides this widget
        menu.addAction("Delete").triggered.connect(self.onActionDelete)

        view_widget = self.view()
        if view_widget:
            global_pos = view_widget.mapToGlobal(QPoint(qml_x, qml_y))
            menu.popup(global_pos)
            print(f"Context menu shown via popup at global {global_pos.x()},{global_pos.y()}")
        else:
            print(f"Context menu created, but self.view() is None. Cannot show correctly.")

    @pyqtSlot()
    def handleQuickLeftClick(self):
        print(f"handleQuickLeftClick called. Filepath: '{self._filepath}', Placeholder: {self._show_placeholder}")
        if self._show_placeholder or not self._filepath:
            self.selectFile()
        else:
            self.openFileInEditor()

    def selectFile(self):
        parent_widget = self.view() if self.view() else None
        dialog = QFileDialog(parent_widget, "Select or Create Note File")
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setNameFilters(["Text files (*.txt)", "Markdown files (*.md)", "All files (*)"])
        dialog.setAcceptMode(QFileDialog.AcceptOpen) # Allows selecting existing or typing new

        if dialog.exec_():
            selected_files = dialog.selectedFiles()
            if selected_files:
                filepath = selected_files[0]

                if not os.path.exists(filepath): # File must be created
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            pass # Create empty file
                        print(f"Created new empty file: {filepath}")
                    except Exception as e:
                        print(f"Error creating new file {filepath}: {e}")
                        self._note_content = f"Error creating file:\n{e}"
                        self.noteContentChanged.emit()
                        return

                self.filepath = filepath # Setter updates DB, QML, and loads content
                print(f"File selected/created: {self.filepath}")
        else:
            print("File selection cancelled.")

    def openFileInEditor(self):
        if self._filepath and os.path.exists(self._filepath):
            command = f"xdg-open \"{self._filepath}\"" # More DE-agnostic
            # Alternative: command = f"konsole -e nvim \"{self._filepath}\""
            print(f"Executing: {command} (Placeholder for subprocess.Popen)")
            # import subprocess
            # try:
            #     subprocess.Popen(command, shell=True, text=True)
            # except Exception as e:
            #     print(f"Error opening file in editor: {e}")
            #     self._note_content = f"Error opening editor: {e}"
            #     self.noteContentChanged.emit()
        else:
            print(f"Filepath is invalid or does not exist: {self._filepath}")
            self._note_content = f"Cannot open: File does not exist\n{self._filepath}"
            self.noteContentChanged.emit()

# Entry point for Plasma
def CreateApplet(parent, args=None):
    return DesktopNotesApplet(parent, args)

if __name__ == '__main__':
    # This section is not used by Plasma but can be for direct testing if framework is set up.
    print("This script is intended to be loaded by Plasma as a plasmoid.")
    # To run standalone for testing QML, you'd need QApplication, QQmlApplicationEngine, etc.
    # from PyQt5.QtWidgets import QApplication
    # import sys
    # app = QApplication(sys.argv)
    # # ... setup engine, load QML ...
    # # This is beyond the scope of "no execution".
    pass
