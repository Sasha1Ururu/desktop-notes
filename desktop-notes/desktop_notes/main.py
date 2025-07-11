# --- Standard library imports ---
import sys
import os

# --- PyQt6 imports ---
from PyQt6.QtWidgets import (
    QGraphicsWidget, QGraphicsLinearLayout, QGraphicsProxyWidget,
    QApplication, QMenu, QGraphicsScene, QGraphicsView # Added QMenu, QGraphicsScene, QGraphicsView for testing
)
from PyQt6.QtCore import Qt, QUrl, QSizeF, QPoint, QSize, QPointF # Added QPoint, QSize, QPointF
from PyQt6.QtGui import QAction # Added QAction

# --- Plasma framework imports (conceptual) ---
try:
    # This is where real Plasma bindings would be imported.
    # e.g. from plasma import Applet as PlasmaApplet
    # For this exercise, we'll ensure ImportError to use the dummy.
    raise ImportError("Using dummy Plasma bindings for development.")
except ImportError:
    # print("Warning: Actual Plasma bindings not found. Using dummy Applet class.", file=sys.stderr)
    class Applet(QGraphicsWidget): # Base class for Plasmoid
        def __init__(self, parent=None, args=None): # parent is usually the containment
            super().__init__(parent) # QGraphicsWidget parent
            self.args = args
            # Basic layout for QGraphicsProxyWidget if NoteWidget is QWidget based
            self._layout = QGraphicsLinearLayout(Qt.Orientation.Vertical, self)
            self.setLayout(self._layout)

            self._config = {} # Simulate KConfigGroup behavior with a simple dict
            self.appletInterface = self # In real Plasma, this is more complex. Here, applet is its own interface.
            self.failedToLaunch = False
            self.failureMessage = ""

        # Mock methods that a Plasmoid might have or that our code might call on self.appletInterface
        def config(self): return self._config

        def setPreferredSize(self, w, h=None):
            if isinstance(w, QSizeF): size = w
            elif isinstance(w, QSize): size = QSizeF(w)
            else: size = QSizeF(w, h if h is not None else 0) # Ensure h is not None
            super().setPreferredSize(size)

        def setFailedToLaunch(self, failed, message=""):
            self.failedToLaunch = failed
            self.failureMessage = message
            print(f"Applet Info: setFailedToLaunch({failed}, Message: '{message}')")

        def pos(self) -> QPointF: # QGraphicsItem returns QPointF
            return super().pos()

        def setPos(self, *args): # Accepts QPointF or x,y
            super().setPos(*args)

        def size(self) -> QSizeF: # QGraphicsWidget returns QSizeF
             return super().size()

        def setVisible(self, visible: bool):
            super().setVisible(visible)
            print(f"Applet Info: setVisible({visible})")

        def update(self): super().update()
        def updateGeometry(self): super().updateGeometry()
        # Add other minimal methods as needed by the applet logic
        # def dataEngine(self, name): return None # Mock if needed


# --- Local imports ---
from . import config
from .data_manager import DataManager
from .note_widget import NoteWidget
from .styling_dialog import StylingDialog
from .all_notes_view import AllNotesManagementView

# Global instance for AllNotesManagementView to make it a singleton-like dialog
_all_notes_view_instance = None

class DesktopNotesApplet(Applet):
    def __init__(self, parent, args=None): # parent is the Plasma containment
        super().__init__(parent, args)
        self.note_id = None
        self.note_widget_instance = None # The actual QWidget for the note
        self.proxy_widget = None         # The QGraphicsProxyWidget that hosts note_widget_instance

        self.data_manager = DataManager(config.DATABASE_FILE)
        # self.setHasConfigurationInterface(False) # If no specific config UI for applet itself
        self.setAspectRatioMode(Qt.AspectRatioMode.IgnoreAspectRatio) # Allow freeform resize by Plasma

    def init(self):
        """Called by Plasma to initialize the applet."""
        print(f"{config.APP_NAME}: Initializing Applet Instance (Note ID from config if exists)...")

        applet_config = self.appletInterface.config() # Get applet's persistent config store
        self.note_id = applet_config.get("noteId", None)

        if self.note_id is not None:
            note_data = self.data_manager.get_note(self.note_id)
            if note_data and note_data.get("status") == config.NOTE_STATUS_SHOWN:
                self._create_display_note_widget(note_data)
            elif note_data: # Exists but not in "shown" state
                print(f"Note {self.note_id} found but status is '{note_data.get('status')}'. Applet will be hidden.")
                self.appletInterface.setVisible(False)
                self.appletInterface.setPreferredSize(1,1) # Minimal size, effectively hidden
            else: # note_id in config but not found in DB (e.g., deleted externally)
                print(f"Note {self.note_id} (from config) not found in DB. Clearing applet config.")
                if "noteId" in applet_config: del applet_config["noteId"]
                self.appletInterface.setFailedToLaunch(True, f"Note {self.note_id} missing from database.")
                self.appletInterface.setVisible(False)
        else: # No noteId in config, this is a brand new applet placement
            self._create_new_note_for_applet()

        if self.note_widget_instance and self.note_widget_instance.isVisible():
            self.appletInterface.setPreferredSize(self.note_widget_instance.size())
            if self.proxy_widget: self.proxy_widget.resize(self.note_widget_instance.size())
        elif not self.appletInterface.failedToLaunch : # If no widget and not already failed
            # This case might occur if note is hidden from the start.
            # setVisible(False) should have been called if status was 'hidden'.
            # If it's truly an unexpected empty state:
            print(f"Applet {self.note_id or 'NEW'}: No note widget displayed, setting failedToLaunch.")
            self.appletInterface.setFailedToLaunch(True, "Note widget could not be initialized or is hidden.")
            self.appletInterface.setPreferredSize(1,1) # Minimal size

    def _create_new_note_for_applet(self):
        print(f"{config.APP_NAME}: Creating new note for this applet instance.")
        current_applet_pos = self.appletInterface.pos().toPoint() # Get current pos from QGraphicsWidget parent

        new_note_data = self.data_manager.create_note(
            filepath=None,
            position={"x": current_applet_pos.x(), "y": current_applet_pos.y()},
            size={"width": config.DEFAULT_NOTE_WIDTH, "height": config.DEFAULT_NOTE_HEIGHT},
            style=config.INITIAL_STYLE.copy(),
            status=config.NOTE_STATUS_SHOWN
        )
        if new_note_data:
            self.note_id = new_note_data['id']
            self.appletInterface.config()["noteId"] = self.note_id
            print(f"New note created (ID: {self.note_id}). Associated with this applet at pos {current_applet_pos}.")
            self._create_display_note_widget(new_note_data)
        else:
            print(f"Error: Failed to create new note in DB for applet.", file=sys.stderr)
            self.appletInterface.setFailedToLaunch(True, "Failed to create note data in DB.")

    def _create_display_note_widget(self, note_data):
        if self.note_widget_instance: # Cleanup if somehow called twice
            self._disconnect_note_widget_signals()
            if self.proxy_widget: self.layout.removeItem(self.proxy_widget)
            self.note_widget_instance.deleteLater()
            if self.proxy_widget: self.proxy_widget.deleteLater()

        self.note_widget_instance = NoteWidget(
            note_id=note_data['id'],
            data_manager=self.data_manager,
            initial_data=note_data,
            parent_applet=self.appletInterface # Pass applet for callbacks/context
        )
        self._connect_note_widget_signals()

        self.proxy_widget = QGraphicsProxyWidget(self.appletInterface) # Parent to applet QGraphicsItem
        self.proxy_widget.setWidget(self.note_widget_instance)
        self.layout.addItem(self.proxy_widget)

        self.appletInterface.setPreferredSize(self.note_widget_instance.size())
        self.appletInterface.updateGeometry()
        self.appletInterface.setVisible(note_data.get("status") == config.NOTE_STATUS_SHOWN)


    def _connect_note_widget_signals(self):
        if not self.note_widget_instance: return
        nw = self.note_widget_instance
        nw.request_open_styling_dialog.connect(self._handle_open_styling_dialog)
        nw.request_new_note.connect(self._handle_request_new_note)
        nw.request_open_all_notes.connect(self._handle_open_all_notes_view)
        nw.widget_hidden.connect(self._handle_widget_hidden_signal) # Renamed to avoid clash
        nw.widget_deleted.connect(self._handle_widget_deleted_signal) # Renamed
        nw.size_changed_by_user.connect(self._handle_note_size_changed)

    def _disconnect_note_widget_signals(self):
        if not self.note_widget_instance: return
        # Try to disconnect all, simple way for PyQt
        try:
            self.note_widget_instance.request_open_styling_dialog.disconnect()
            self.note_widget_instance.request_new_note.disconnect()
            self.note_widget_instance.request_open_all_notes.disconnect()
            self.note_widget_instance.widget_hidden.disconnect()
            self.note_widget_instance.widget_deleted.disconnect()
            self.note_widget_instance.size_changed_by_user.disconnect()
        except TypeError: # Thrown if a signal has no connections
            pass


    # --- Signal Handlers for NoteWidget events ---
    def _handle_open_styling_dialog(self, note_id):
        if note_id == self.note_id and self.note_widget_instance:
            # Determine parent for dialog. If applet is QGraphicsWidget, its window() might be the panel.
            # For standalone test, self.parentWidget() might be None if applet is top-level scene item.
            dialog_parent = self.window() if isinstance(self, QGraphicsWidget) else None
            dialog = StylingDialog(self.note_widget_instance, self.data_manager, parent=dialog_parent)
            dialog.exec()
            self.appletInterface.setPreferredSize(self.note_widget_instance.size())
            self.appletInterface.updateGeometry()

    def _handle_request_new_note(self, requested_pos: QPoint):
        print(f"Applet {self.note_id}: Received request for new note at {requested_pos}.")
        print("  Action: This should ideally trigger Plasma to add a new DesktopNotesApplet instance.")
        new_note_db_entry = self.data_manager.create_note(
            filepath=None, position={"x": requested_pos.x(), "y": requested_pos.y()},
            size={"width": config.DEFAULT_NOTE_WIDTH, "height": config.DEFAULT_NOTE_HEIGHT},
            style=config.INITIAL_STYLE.copy(), status=config.NOTE_STATUS_SHOWN )
        if new_note_db_entry:
            print(f"  New note entry created (ID: {new_note_db_entry['id']}). Manual applet addition by user needed.")

    def _handle_open_all_notes_view(self):
        global _all_notes_view_instance
        if _all_notes_view_instance is None or not _all_notes_view_instance.isVisible():
            dialog_parent = self.window() if isinstance(self, QGraphicsWidget) else None
            _all_notes_view_instance = AllNotesManagementView(self.data_manager, parent=dialog_parent)
            _all_notes_view_instance.request_note_visibility_change.connect(
                self._handle_global_note_visibility_request
            )
            _all_notes_view_instance.show()
        else:
            _all_notes_view_instance.activateWindow()
            _all_notes_view_instance.raise_()

    def _handle_widget_hidden_signal(self, note_id):
        if note_id == self.note_id:
            print(f"Applet for Note {note_id}: Hiding myself based on signal.")
            self.appletInterface.setVisible(False)
            self.appletInterface.config()["status"] = config.NOTE_STATUS_HIDDEN

    def _handle_widget_deleted_signal(self, note_id):
        if note_id == self.note_id:
            print(f"Applet for Note {note_id}: Deleting myself based on signal.")
            if "noteId" in self.appletInterface.config():
                del self.appletInterface.config()["noteId"]
            self.appletInterface.setFailedToLaunch(True, "Note deleted by user.")
            self.appletInterface.setVisible(False)
            self.appletInterface.setPreferredSize(0,0)
            self._disconnect_note_widget_signals()
            if self.proxy_widget: self.layout.removeItem(self.proxy_widget) # remove from layout
            if self.note_widget_instance: self.note_widget_instance.deleteLater()
            if self.proxy_widget: self.proxy_widget.deleteLater()
            self.note_widget_instance = None
            self.proxy_widget = None
            self.deleteLater() # Schedule applet itself for deletion

    def _handle_note_size_changed(self, new_size: QSize):
        if self.note_widget_instance and self.note_widget_instance.size() == new_size:
            print(f"Applet {self.note_id}: NoteWidget size changed to {new_size}. Updating preferredSize.")
            self.appletInterface.setPreferredSize(new_size)
            self.appletInterface.updateGeometry()

    def _handle_global_note_visibility_request(self, note_id_changed, show_widget):
        if note_id_changed == self.note_id:
            print(f"Applet {self.note_id}: Visibility request from AllNotesView: {'Show' if show_widget else 'Hide'}")
            if show_widget:
                note_data = self.data_manager.get_note(self.note_id)
                if not note_data or note_data['status'] != config.NOTE_STATUS_SHOWN:
                    print(f"  Error or status mismatch: Note {self.note_id} in DB not 'shown'. Cannot show.")
                    if note_data: self.data_manager.update_note(self.note_id, {"status": config.NOTE_STATUS_SHOWN}) # Force DB
                    return

                if not self.note_widget_instance : # If widget was deleted when hidden
                    self._create_display_note_widget(note_data) # This also sets visibility
                else: # Widget exists, just ensure it's visible and data is fresh
                    self.note_widget_instance.apply_note_data(note_data)
                    self.appletInterface.setVisible(True)

                self.appletInterface.setPreferredSize(self.note_widget_instance.size())
                self.appletInterface.updateGeometry()
                self.appletInterface.config()["status"] = config.NOTE_STATUS_SHOWN
            else: # Hide
                self._handle_widget_hidden_signal(note_id_changed)
        # else: This request is for another applet instance.

    def itemChange(self, change, value):
        # Called when QGraphicsItem's state changes, including position.
        if change == QGraphicsWidget.GraphicsItemChange.ItemPositionHasChanged and self.note_id is not None:
            new_pos = self.appletInterface.pos().toPoint() # Current position of the applet itself
            # Update the position in the database
            if self.data_manager.update_note(self.note_id, {"position": {"x": new_pos.x(), "y": new_pos.y()}}):
                print(f"Applet {self.note_id}: Position changed by Plasma to {new_pos}. Saved to DB.")
            else:
                print(f"Applet {self.note_id}: Failed to save new position {new_pos} to DB.")
        return super().itemChange(change, value)

    def constraintsEvent(self, constraints):
        # Called when Plasma changes constraints, e.g. resizes the applet externally.
        super().constraintsEvent(constraints) # Important to call base
        if self.note_widget_instance:
            new_applet_size = self.appletInterface.size().toSize() # QSize
            if new_applet_size.isValid() and new_applet_size != self.note_widget_instance.size():
                print(f"Applet {self.note_id}: External resize by Plasma to {new_applet_size}. Resizing NoteWidget.")
                self.note_widget_instance.resize(new_applet_size)
                # NoteWidget's own resize logic should handle internal layout.
                # We need to save this new size to DB.
                self.note_widget_instance._save_geometry_to_db() # This saves its own size.


def CreateApplet(parent):
    """Plasma entry point for creating an instance of the applet."""
    return DesktopNotesApplet(parent)

if __name__ == '__main__':
    print("Running DesktopNotesApplet in standalone test mode (refined).")
    app = QApplication.instance() or QApplication(sys.argv)

    # Clean up previous DB if any for fresh test
    if os.path.exists(config.DATABASE_FILE):
        os.remove(config.DATABASE_FILE)

    # Test 1: New applet (should create a new note)
    print("\n--- Test 1: New Applet Instance ---")
    host1_view = QGraphicsView()
    scene1 = QGraphicsScene()
    applet1 = DesktopNotesApplet(parent=None) # parent=None for top-level QGraphicsItem in scene
    scene1.addItem(applet1) # Add applet to its scene
    applet1.init() # Initialize applet logic

    host1_view.setScene(scene1)
    host1_view.setWindowTitle("Test1: New Applet (ID: {})".format(applet1.note_id or "N/A"))
    if applet1.note_widget_instance:
         host1_view.resize(applet1.note_widget_instance.width() + 40, applet1.note_widget_instance.height() + 40)
    else:
         host1_view.resize(config.DEFAULT_NOTE_WIDTH + 40, config.DEFAULT_NOTE_HEIGHT + 40)
    host1_view.show()

    created_note_id = applet1.note_id

    # Test 2: Applet loading an existing note
    if created_note_id is not None:
        print(f"\n--- Test 2: Existing Applet Instance (loading note ID: {created_note_id}) ---")
        host2_view = QGraphicsView()
        scene2 = QGraphicsScene()
        applet2 = DesktopNotesApplet(parent=None)
        applet2.config()["noteId"] = created_note_id # Simulate Plasma loading config for this instance
        scene2.addItem(applet2)
        applet2.init()

        host2_view.setScene(scene2)
        host2_view.setWindowTitle(f"Test2: Load Note {created_note_id}")
        if applet2.note_widget_instance:
            host2_view.resize(applet2.note_widget_instance.width() + 40, applet2.note_widget_instance.height() + 40)
        else:
            host2_view.resize(config.DEFAULT_NOTE_WIDTH + 40, config.DEFAULT_NOTE_HEIGHT + 40)
        host2_view.show()
        host2_view.move(host1_view.x() + host1_view.width() + 20, host1_view.y()) # Position for visibility
    else:
        print("Skipping Test 2 as Test 1 did not yield a note_id.")

    # Test 3: Open AllNotesView from an applet and interact
    if applet1 and applet1.note_widget_instance:
        print("\n--- Test 3: Open AllNotesView from Applet 1 ---")
        applet1._handle_open_all_notes_view()
        # Manual interaction: Try hiding/showing the note of applet1 from AllNotesView.
        # Check console logs for signal handling.

    print("\nExecuting QApplication. Close windows to exit.")
    sys.exit(app.exec())
