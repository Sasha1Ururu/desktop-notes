import sys
import os
from pathlib import Path

# --- Path adjustments to find the 'src' module ---
# This is for development. In a proper installation, the module path might be handled differently.
# Assuming 'package/contents/code/' is where this script runs from.
# We want to access 'src' which is one level up from 'package', then into 'src'.
# Path to the project root (assuming 'desktop-notes' is the root)
# This script is in desktop-notes/package/contents/code/
# Project root is desktop-notes/
# src is in desktop-notes/src/
current_script_path = Path(os.path.dirname(os.path.abspath(__file__)))
project_root = current_script_path.parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root)) # Add project root to allow 'from src import ...'

try:
    from PyQt6.QtWidgets import QGraphicsWidget, QVBoxLayout, QApplication
    from PyQt6.QtCore import QUrl, pyqtProperty, QSizeF

    # Attempt to import Plasma specific modules. These will fail if bindings are not present.
    # These are typical names from Plasma 5 (PyKDE5). Plasma 6 might differ.
    # For Plasma 6 with Qt6, it might be something like:
    # from KDE.Plasma import Applet
    # from KDE.Plasma.Core import Icon
    # For now, using placeholders or common Plasma 5 names for structure.
    HAS_PLASMA_BINDINGS = False
    try:
        from PyKDE5.Plasma import Applet # Plasma 5 style
        from PyKDE5.PlasmaCore import Icon as PlasmaIcon
        # Or for Plasma 6, one might expect something like:
        # from KPyPlasma.Plasma import Applet
        # from KPyPlasma.Core import Icon as PlasmaIcon
        # This part is highly speculative without actual Plasma 6 Python binding docs.
        # Let's assume a generic "PlasmaApplet" base class for now.
        # For this example, we'll define a dummy Applet if real bindings are not found.
        HAS_PLASMA_BINDINGS = True
        print("Actual Plasma bindings seem to be available (or an older version).")
    except ImportError:
        print("Plasma bindings not found. Using dummy Applet class for structure.")
        # Define dummy classes to allow the script to be parsed
        class Applet(QGraphicsWidget): # QGraphicsWidget is a common base for Plasmoids
            def __init__(self, parent, args=None):
                super().__init__(parent)
                print(f"Dummy Applet initialized with args: {args}")
                self.args = args # To store plasmoidId or other context

            def KAboutData(self): # Dummy method for aboutData
                return None

            # Common properties for plasmoids
            @pyqtProperty(str)
            def formFactor(self): return "planar" # e.g. planar, vertical, horizontal

            @pyqtProperty(str)
            def location(self): return "desktop" # e.g. desktop, panel, systray

            @pyqtProperty(QSizeF)
            def size(self): return super().size()

            @size.setter
            def size(self, new_size): super().resize(new_size)

            # Placeholder for configuration
            def readConfig(self): pass
            def writeConfig(self): pass

            # Method called by Plasma to indicate the applet has finished its setup
            def appletInitialized(self): pass

        class PlasmaIcon:
            def __init__(self, name):
                self.name = name
                print(f"Dummy PlasmaIcon created with name: {name}")


    from src.note_widget import NoteWidget
    from src.database import add_note, get_note, get_all_notes, update_note, delete_note
    from src.styling_dialog import StylingDialog
    from src.management_view import ManagementView
    from src.utils import get_editor_command # Import for editor command
    MODULE_IMPORT_SUCCESS = True
except ImportError as e:
    MODULE_IMPORT_SUCCESS = False
    # If imports fail, this plasmoid cannot run.
    # In a real scenario, Plasma would show an error.
    # We can write to a log or stderr for debugging.
    print(f"Error importing necessary modules for Desktop Notes Plasmoid: {e}", file=sys.stderr)
    # Create a dummy class so that Plasma can still try to load something if it requires a factory.
    class DesktopNotesPlasmoid:
        def __init__(self, parent, args=None):
            print("Failed to initialize DesktopNotesPlasmoid due to import errors.", file=sys.stderr)


# --- Placement Logic ---
def get_new_widget_position(existing_widgets_data: list, screen_geometry=None) -> dict:
    """
    Calculates a position for a new widget.
    Tries to place it to the right of the last known widget, or cascades.
    `existing_widgets_data` is a list of dicts, each with 'position' and 'size'.
    `screen_geometry` could be a QRect of the available screen space.
    """
    offset = 20  # Offset from previous widget or screen edge
    default_x, default_y = 50, 50

    if not existing_widgets_data:
        return {"x": default_x, "y": default_y}

    # Try to place relative to the last modified/created widget if that info is available.
    # For now, let's use the widget with the largest x, then y.
    # A simpler approach: cascade from the last widget in the list (often the most recent).
    last_widget = existing_widgets_data[-1]
    last_pos = last_widget.get("position", {"x": default_x, "y": default_y})
    last_size = last_widget.get("size", {"width": 200, "height": 150}) # Default if not set

    new_x = last_pos["x"] + last_size["width"] + offset
    new_y = last_pos["y"]

    # Basic screen boundary check (if screen_geometry is provided)
    if screen_geometry:
        if new_x + last_size["width"] > screen_geometry.width(): # last_size.width as proxy for new widget width
            new_x = default_x # Reset to left
            new_y = last_pos["y"] + last_size["height"] + offset
        if new_y + last_size["height"] > screen_geometry.height():
            new_y = default_y # Reset to top, potentially overlapping if many resets occur

    # Simple cascade if no screen_geometry (can lead to going off-screen)
    # A more robust solution would involve knowing which widget triggered "Add New Note"
    # or checking actual screen boundaries via Plasma APIs.
    # For now, a simple cascade:
    if len(existing_widgets_data) % 3 == 0 : # Every 3rd widget, start a new "row"
         new_x = default_x
         new_y = last_pos.get("y", default_y) + last_size.get("height", 150) + offset
    else: # Place to the right
        new_x = last_pos.get("x", default_x) + last_size.get("width", 200) + offset
        new_y = last_pos.get("y", default_y)


    # Fallback if many widgets (very basic)
    if len(existing_widgets_data) > 5: # Simple cascade
        new_x = default_x + (len(existing_widgets_data) % 5) * offset * 2
        new_y = default_y + (len(existing_widgets_data) // 5) * (150 + offset) # Assuming avg height 150

    return {"x": int(new_x), "y": int(new_y)}


if MODULE_IMPORT_SUCCESS:
    class DesktopNotesPlasmoid(Applet):
        def __init__(self, parent=None, args=None):
            super().__init__(parent, args)
            self.parent = parent
            self.note_widgets = {}
            self.main_layout = None

            # Drag/Resize Mode state
            self.is_drag_resize_mode_active = False
            self._drag_resize_border_active = False # To track border state specifically
            self._drag_operation = None # "move", "resize_tl", "resize_t", etc.
            self._drag_start_mouse_pos = None # QPointF, relative to widget/scene
            self._drag_start_widget_pos = None # QPointF, widget's top-left
            self._drag_start_widget_size = None # QSizeF

            # Define resize margin (how close to edge/corner to trigger resize cursor)
            self._resize_margin = 8 # pixels

            # About data (example)
            # self.setAboutData(self.KAboutData(
            #     pluginName="Desktop Notes",
            #     authors=["AI Developer"],
            #     version="0.1",
            #     description="Display text/Markdown notes on your desktop."
            # ))
            # self.setHasConfigurationInterface(False) # No separate config dialog for the plasmoid itself yet

            # The plasmoid instance itself might represent ONE note, or be a manager.
            # Based on "Each addition creates a new Note Widget instance",
            # this DesktopNotesPlasmoid instance IS one Note Widget.
            # So, upon creation of this plasmoid, we create one note in the DB.

            print("DesktopNotesPlasmoid: __init__ called.")
            # args might contain 'plasmoidId' or other context from Plasma.
            # print(f"Plasmoid args: {self.args}")

            # Initialize the main UI for this plasmoid instance
            # In Plasma, QGraphicsWidget is often used, and content is added to its layout.
            # If this plasmoid IS a single note widget:
            self.main_widget_container = QGraphicsWidget(self) # self is the Applet
            self.main_layout = QVBoxLayout(self.main_widget_container) # Layout for the QGraphicsWidget
            self.main_layout.setContentsMargins(0,0,0,0)

            # This causes the QGraphicsWidget to be the central item of the Applet
            # For Plasma 6, this is often done by setting self.centralWidget or similar
            # or by this Applet itself being the main QML item.
            # If using QGraphicsLayout directly on Applet:
            # graphics_layout = QGraphicsLinearLayout(Qt.Orientation.Vertical, self)
            # graphics_layout.addItem(self.note_qwidget_proxy)
            # self.setLayout(graphics_layout)

            # For now, assuming this Applet instance IS one note.
            # It needs to create its corresponding DB entry and NoteWidget.
            self._create_new_note_instance()


        def _create_new_note_instance(self, source_widget_data=None):
            """
            Creates a new note in the database and its corresponding NoteWidget.
            `source_widget_data` can be the data of the widget that triggered this creation,
            used for placement.
            """
            print("DesktopNotesPlasmoid: _create_new_note_instance called.")
            all_current_notes = get_all_notes()

            # Determine position for the new note
            # If source_widget_data is provided (e.g. from "Add New Note" context menu),
            # we might use that as a reference.
            # For now, get_new_widget_position uses the list of all notes.
            # screen_geom = self.screenGeometry() if hasattr(self, 'screenGeometry') else None # Plasma specific
            new_pos = get_new_widget_position(all_current_notes, screen_geometry=None)

            # Default size and style for a new note (can be configured later)
            default_size = {"width": 250, "height": 180}
            default_style = {"transparency": 1.0, "backgroundColor": "#F0F0F0", "margin": 8}

            new_note_id = add_note(
                filepath=None, # New notes start with no file
                position=new_pos,
                size=default_size,
                style=default_style
            )

            if new_note_id is None:
                print("Error: Could not create new note in database.", file=sys.stderr)
                return

            print(f"DesktopNotesPlasmoid: New note created in DB with ID: {new_note_id}")
            self.note_id = new_note_id # This plasmoid instance is now associated with this note_id

            # Now, create the actual NoteWidget (our PyQt6 QWidget)
            # This NoteWidget needs to be embedded into this Plasmoid (QGraphicsWidget).
            # This is typically done by creating a QGraphicsProxyWidget.

            # The NoteWidget (QWidget) cannot be directly added to a QGraphicsScene/QGraphicsWidget layout.
            # It must be wrapped in a QGraphicsProxyWidget.

            # self.note_qwidget = NoteWidget(note_id=self.note_id)
            # self.note_qwidget_proxy = QGraphicsProxyWidget(self.main_widget_container) # Or self if main_widget_container is not used
            # self.note_qwidget_proxy.setWidget(self.note_qwidget)
            # self.main_layout.addWidget(self.note_qwidget_proxy)

            # However, the spec implies each "Note Widget" is an "individual, resizable, and movable widget instance".
            # This suggests that each Plasmoid instance created by Plasma *is* one Note Widget.
            # So, this DesktopNotesPlasmoid class itself should embody the NoteWidget's functionality.
            # This means DesktopNotesPlasmoid should visually be the NoteWidget.

            # Re-thinking: The Applet (DesktopNotesPlasmoid) IS the widget on the desktop.
            # It should directly manage its appearance and content, possibly by incorporating
            # logic from NoteWidget or by having NoteWidget as its primary component.

            # Let's try to make this Applet itself behave like a NoteWidget.
            self.note_data = get_note(self.note_id)
            if not self.note_data:
                print(f"Error: Failed to load note data for new ID {self.note_id}", file=sys.stderr)
                # TODO: Display an error state on the widget itself
                return

            # The Applet itself needs to display the content.
            # Plasma Applets often use QML for UI. If pure Python, we build UI using Qt Graphics View items.
            # For simplicity, if we were to use QTextEdit from NoteWidget, it needs to be adapted.
            # A QGraphicsTextItem could be used directly in the Applet's QGraphicsScene.

            # For now, let's assume NoteWidget is a QWidget that gets displayed.
            # The challenge is that Plasma Applets are QGraphicsWidget based.
            # One common pattern is for the Applet to load a QML file which then might embed or interact
            # with Python objects.

            # If we are *not* using QML for the Applet's UI:
            # We need to construct the UI using QGraphicsItems or proxy QWidgets.
            # Let's assume we can embed our existing NoteWidget (QWidget) via QGraphicsProxyWidget.

            self.note_qwidget_instance = NoteWidget(note_id=self.note_id) # This is a QWidget

            # Connect signals from the QWidget to methods in this Applet
            self.note_qwidget_instance.requestSelectFile.connect(self.handle_select_file_request)
            self.note_qwidget_instance.requestOpenFileInEditor.connect(self.handle_open_file_in_editor_request)

            # Connect new signals for context menu actions
            self.note_qwidget_instance.requestDragResizeMode.connect(self.handle_drag_resize_request)
            self.note_qwidget_instance.requestStylingDialog.connect(self.handle_styling_dialog_request)
            self.note_qwidget_instance.requestAddNewNote.connect(self.handle_add_new_note_request)
            self.note_qwidget_instance.requestOpenNotesManager.connect(self.handle_open_notes_manager_request)
            self.note_qwidget_instance.requestHideWidget.connect(self.handle_hide_widget_request)
            self.note_qwidget_instance.requestDeleteWidget.connect(self.handle_delete_widget_request)

            # self.note_qwidget_instance.widgetDeleted.connect(self.handle_widget_deleted_signal) # If NoteWidget can self-delete

            # Embed the QWidget (NoteWidget) into the QGraphicsWidget (Applet)
            # This requires the Applet to have a layout that can take a QGraphicsProxyWidget.
            # If self.main_layout is a QGraphicsLinearLayout added to self (the Applet):
            # proxy = self.scene().addWidget(self.note_qwidget_instance) # Adds to scene, not layout

            # If the Applet has a main QGraphicsWidget container whose layout is QVBoxLayout (QtWidget layout):
            # This is conceptually mixed. A QGraphicsWidget uses QGraphicsLayout, not QVBoxLayout.

            # Let's simplify: Assume the Applet itself will manage a QGraphicsProxyWidget for the NoteWidget.
            # Clear previous widget if any (e.g. if re-initializing)
            if hasattr(self, 'proxy_widget_item') and self.proxy_widget_item:
                self.main_layout.removeWidget(self.proxy_widget_item.widget()) # Remove QWidget from proxy
                self.proxy_widget_item.setWidget(None) # Clear proxy
                # self.scene().removeItem(self.proxy_widget_item) # If added directly to scene
                # self.proxy_widget_item.deleteLater() # Or just hide

            # The main_layout needs to be a QGraphicsLayout, not a QWidget layout, if self.main_widget_container is a QGraphicsWidget
            # If self.main_widget_container is a QWidget (which is not standard for an Applet's direct content):
            # proxy = QGraphicsProxyWidget() # No parent needed if adding to QGraphicsScene directly
            # proxy.setWidget(self.note_qwidget_instance)
            # self.scene().addItem(proxy) # This makes it part of the Applet's scene
            # self.proxy_widget_item = proxy

            # This is where the lack of a running Plasma environment makes it hard to verify the correct integration pattern.
            # For now, let's assume the NoteWidget (QWidget) can be made visible.
            # In a non-Plasma test, `self.note_qwidget_instance.show()` would work.
            # In Plasma, the Applet itself is shown, and its contents become visible.

            # The Applet (self) needs to be resized to match the NoteWidget's desired size.
            self.resize_applet_to_note_data()

            # The NoteWidget's content and appearance are handled by itself based on note_data.
            # We just need to make sure it's "active" or "visible" within the Applet.

            print(f"DesktopNotesPlasmoid: Instance for note {self.note_id} is conceptually set up.")

            # Call appletInitialized if it's a real Plasma method, to signal readiness
            if hasattr(super(), "appletInitialized"):
                 super().appletInitialized()


        def resize_applet_to_note_data(self):
            if hasattr(self, 'note_data') and self.note_data:
                size_info = self.note_data.get("size", {"width": 250, "height": 180})
                # For a QGraphicsWidget (Applet), you might set preferredSize or resize it.
                self.setPreferredSize(QSizeF(size_info["width"], size_info["height"]))
                # Or self.resize(size_info["width"], size_info["height"])
                # This will trigger a layout update if a layout is set on the Applet.
                if self.layout(): # Check if a QGraphicsLayout is set on the applet
                    self.layout().invalidate() # Force re-layout
                self.update()
                print(f"Applet for note {self.note_id} resized to {size_info}")

        # --- Handlers for signals from NoteWidget (QWidget) ---
        def handle_select_file_request(self, note_id):
            if self.note_id != note_id: return
            print(f"Plasmoid (Note ID {self.note_id}): Received request to select file.")

            # In a real Plasma environment, use KIO.JobUiDelegate, KIO. specjalized job
            # or QFileDialog via Plasma D-Bus service for native dialogs.
            # For now, simulate a file dialog and response.

            # Simulate opening a file dialog.
            # In a real app: dialog = QFileDialog(self.note_qwidget_instance) ...
            # For testing, let's define a dummy file path.
            # And also test creation of a new file.

            # Scenario 1: User selects an existing file
            # simulated_filepath = os.path.abspath("test_note.md") # Use one of the test files
            # if not Path(simulated_filepath).exists():
            #     with open(simulated_filepath, "w") as f: f.write("# Dummy File for Selection\nSelected.")

            # Scenario 2: User types a new filename (simulate creation)
            simulated_new_filepath = os.path.abspath("newly_created_by_dialog.txt")

            # Simulate user confirming dialog
            user_confirmed = True
            chosen_path = simulated_new_filepath # Change to simulated_filepath to test existing

            if user_confirmed and chosen_path:
                is_new_file = not Path(chosen_path).exists()
                if is_new_file:
                    try:
                        Path(chosen_path).touch() # Create empty file
                        print(f"Plasmoid: New empty file '{chosen_path}' created.")
                    except Exception as e:
                        print(f"Plasmoid: Error creating new file '{chosen_path}': {e}")
                        return # Don't proceed if file creation failed

                if update_note(self.note_id, {"filepath": str(chosen_path)}):
                    self.note_data = get_note(self.note_id) # Reload data
                    if self.note_qwidget_instance:
                        self.note_qwidget_instance.refresh_display() # Refresh the embedded QWidget
                    print(f"Plasmoid: Note {self.note_id} filepath updated to '{chosen_path}'. Widget refreshed.")
                else:
                    print(f"Plasmoid: Failed to update note {self.note_id} filepath in DB.")
            else:
                print(f"Plasmoid: File selection cancelled for note {self.note_id}.")


        def handle_open_file_in_editor_request(self, filepath):
            print(f"Plasmoid (Note ID {self.note_id}): Received request to open file '{filepath}' in editor.")
            # Configurable command in future. For now, `konsole -e nvim $filepath`
            # Use QProcess for better control than os.system
            try:
                from PyQt6.QtCore import QProcess
                process = QProcess()
                editor_cmd_template = get_editor_command() # Get command from settings

                # Replace {filepath} placeholder. Basic replacement.
                # A more robust solution might involve shlex for parsing if the command template is complex.
                if "{filepath}" not in editor_cmd_template:
                    print(f"  Warning: editor command template '{editor_cmd_template}' does not contain {{filepath}} placeholder. Appending filepath.")
                    full_command_parts = editor_cmd_template.split() + [filepath]
                else:
                    full_command_str = editor_cmd_template.replace("{filepath}", filepath)
                    # Basic split for command and args. This might not be robust for complex commands with quotes.
                    # For `konsole -e nvim $filepath`, `konsole` is cmd, rest are args.
                    # If cmd_template is `code --wait "$filepath"`, shlex would be better.
                    # For now, simple split:
                    full_command_parts = full_command_str.split()

                command = full_command_parts[0]
                args = full_command_parts[1:]

                print(f"  Executing editor: Command='{command}', Args={args}")
                process.startDetached(command, args)
            except ImportError:
                 print("  QProcess not available, falling back to os.system (less safe).")
                 editor_cmd_template = get_editor_command()
                 full_command_str = editor_cmd_template.replace("{filepath}", filepath)
                 # os.system needs a single string. Ensure filepath is quoted if it might contain spaces.
                 # However, the template itself should handle quoting if necessary (e.g., "gedit '{filepath}'")
                 os.system(full_command_str + " &")
            except Exception as e:
                print(f"  Error trying to open file in editor: {e}")

        # --- Handlers for new context menu signals ---

        def handle_drag_resize_request(self, note_id):
            if self.note_id != note_id: return
            print(f"Plasmoid (Note ID {self.note_id}): Drag/Resize mode requested.")
            self.toggle_drag_resize_mode()

        def toggle_drag_resize_mode(self):
            self.is_drag_resize_mode_active = not self.is_drag_resize_mode_active
            print(f"Plasmoid (Note ID {self.note_id}): Drag/Resize mode {'ACTIVATED' if self.is_drag_resize_mode_active else 'DEACTIVATED'}.")
            self._update_drag_resize_visuals()

            # For QGraphicsWidget, accept hover events to change cursor
            self.setAcceptHoverEvents(self.is_drag_resize_mode_active)
            if not self.is_drag_resize_mode_active:
                self.unsetCursor() # Reset cursor to normal

        def _update_drag_resize_visuals(self):
            # Visual indication: 3px yellow border
            # This is highly dependent on how the Applet is structured (QML, QGraphicsWidget direct paint, or QWidget proxy)
            # Assuming self.note_qwidget_instance is the main visible QWidget part:
            if hasattr(self, 'note_qwidget_instance') and self.note_qwidget_instance:
                current_stylesheet = self.note_qwidget_instance.styleSheet()
                border_style = "border: 3px solid yellow;"

                # Remove existing border style to avoid duplicates if re-applying
                # This is a simplistic way; a more robust stylesheet management might be needed
                current_stylesheet = "".join([line for line in current_stylesheet.split(';') if "border:" not in line])

                if self.is_drag_resize_mode_active:
                    if self._drag_resize_border_active: # Already active, do nothing
                        return
                    new_stylesheet = current_stylesheet + ";" + border_style if current_stylesheet else border_style
                    self.note_qwidget_instance.setStyleSheet(new_stylesheet)
                    self._drag_resize_border_active = True
                    print(f"  Applied yellow border. Stylesheet: {new_stylesheet}")
                else:
                    if not self._drag_resize_border_active: # Already inactive, do nothing
                        return
                    # Remove the border style
                    self.note_qwidget_instance.setStyleSheet(current_stylesheet)
                    self._drag_resize_border_active = False
                    print(f"  Removed yellow border. Stylesheet: {current_stylesheet}")
            else:
                # If directly painting on QGraphicsWidget or using QML, this would be different.
                print("  (Conceptual) Visual indication for drag/resize mode updated.")

            # Force update/repaint if necessary
            if hasattr(self, 'update'): self.update()


        # --- Mouse event handling for Drag/Resize ---
        # These events are for the Applet (QGraphicsWidget) itself.

        def hoverMoveEvent(self, event: 'QGraphicsSceneHoverEvent'):
            if self.is_drag_resize_mode_active:
                pos = event.pos() # Position relative to the QGraphicsWidget
                rect = self.boundingRect() # QRectF
                new_cursor = self._get_cursor_for_position(pos, rect)
                self.setCursor(new_cursor)
            else:
                super().hoverMoveEvent(event)

        def _get_cursor_for_position(self, pos: 'QPointF', rect: 'QRectF') -> 'QCursor':
            margin = self._resize_margin
            on_left_edge = abs(pos.x() - rect.left()) < margin
            on_right_edge = abs(pos.x() - rect.right()) < margin
            on_top_edge = abs(pos.y() - rect.top()) < margin
            on_bottom_edge = abs(pos.y() - rect.bottom()) < margin

            if on_top_edge and on_left_edge: return Qt.CursorShape.SizeFDiagCursor # Top-left
            if on_top_edge and on_right_edge: return Qt.CursorShape.SizeBDiagCursor # Top-right
            if on_bottom_edge and on_left_edge: return Qt.CursorShape.SizeBDiagCursor # Bottom-left
            if on_bottom_edge and on_right_edge: return Qt.CursorShape.SizeFDiagCursor # Bottom-right
            if on_top_edge: return Qt.CursorShape.SizeVerCursor # Top
            if on_bottom_edge: return Qt.CursorShape.SizeVerCursor # Bottom
            if on_left_edge: return Qt.CursorShape.SizeHorCursor # Left
            if on_right_edge: return Qt.CursorShape.SizeHorCursor # Right

            return Qt.CursorShape.OpenHandCursor # Default for moving

        def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
            if self.is_drag_resize_mode_active and event.button() == Qt.MouseButton.LeftButton:
                event.accept() # We are handling this event
                self._drag_start_mouse_pos = event.scenePos() # Use scenePos for consistent coordinates
                self._drag_start_widget_pos = self.scenePos() # Current top-left of widget in scene
                self._drag_start_widget_size = self.size() # QSizeF

                # Determine operation based on cursor/position (redundant if cursor is already set, but safer)
                # Using event.pos() (widget-local) for determining operation region
                op_cursor_shape = self._get_cursor_for_position(event.pos(), self.boundingRect())

                if op_cursor_shape == Qt.CursorShape.OpenHandCursor:
                    self._drag_operation = "move"
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                elif op_cursor_shape != self.cursor().shape(): # A resize cursor
                    self._drag_operation = "resize" # Store more specific resize type if needed
                    # The specific resize (e.g., top, bottom-left) is implicitly handled by how we adjust geometry
                else: # Should not happen if hover is working
                    self._drag_operation = None

                print(f"Drag/Resize: Mouse press, op: {self._drag_operation}, start widget pos: {self._drag_start_widget_pos}, start size: {self._drag_start_widget_size}")

            elif not self.is_drag_resize_mode_active:
                # Pass to NoteWidget's QWidget mousePress if it's proxied and should handle it
                # This is complex. If QGraphicsProxyWidget is used, it might handle forwarding.
                # For now, assuming the QWidget part handles its own clicks if mode is OFF.
                # This was covered by self.note_qwidget_instance.mousePressEvent
                # However, QGraphicsSceneMouseEvent is different from QMouseEvent.
                # The QGraphicsProxyWidget is supposed to bridge this.
                # For the left-click on NoteWidget functionality (open file/dialog):
                # This needs to be reconciled. If the Applet gets the click first,
                # it might need to manually forward or check if the click was on the proxied widget.

                # Simplification: If mode is off, let the default QGraphicsWidget behavior (or proxy) handle it.
                # The original NoteWidget's mousePressEvent (for QWidget) will only fire if it gets the event.
                super().mousePressEvent(event)
            else:
                # Other mouse buttons in drag/resize mode - ignore or pass through
                super().mousePressEvent(event)


        def mouseMoveEvent(self, event: 'QGraphicsSceneMouseEvent'):
            if self.is_drag_resize_mode_active and self._drag_operation and event.buttons() & Qt.MouseButton.LeftButton:
                event.accept()
                delta = event.scenePos() - self._drag_start_mouse_pos # Movement in scene coordinates

                if self._drag_operation == "move":
                    new_pos = self._drag_start_widget_pos + delta
                    self.setPos(new_pos) # QGraphicsWidget setPos
                    # print(f"  Moving to {new_pos.x()},{new_pos.y()}")
                elif self._drag_operation == "resize":
                    # This is simplified. A full resize needs to check which edge/corner was grabbed.
                    # For now, let's assume it's always resize from bottom-right for simplicity here.
                    # A proper implementation would use the _get_cursor_for_position logic
                    # or store the specific resize type (e.g., 'resize_br', 'resize_l')

                    # Example: resizing by changing width/height based on delta from bottom-right
                    # This requires knowing which corner/edge was initially grabbed.
                    # Let's use a simplified approach: just change size.
                    # More accurate: adjust rect based on which handle is dragged.

                    current_mouse_scene_pos = event.scenePos()
                    current_rect = QRectF(self._drag_start_widget_pos, self._drag_start_widget_size)

                    # This is where we need to know which edge/corner is being dragged
                    # We can get this from the cursor shape at mousePressEvent or re-evaluate
                    # For now, a very simple example: just add delta to size (like dragging bottom-right)
                    # This is NOT a complete resize logic for all edges/corners.
                    new_width = self._drag_start_widget_size.width() + delta.x()
                    new_height = self._drag_start_widget_size.height() + delta.y()

                    # Enforce minimum size
                    min_width, min_height = 50, 30
                    new_width = max(min_width, new_width)
                    new_height = max(min_height, new_height)

                    # For QGraphicsWidget, resizing is often done by preparing geometry change
                    # and then setting the new geometry, or by directly manipulating its transform.
                    # If using setPreferredSize and layout:
                    # self.setPreferredSize(QSizeF(new_width, new_height))
                    # Or, if direct manipulation of size is allowed (less common for layout-managed items):
                    # self.resize(new_width, new_height) -> QGraphicsLayoutItem method

                    # The most direct way for a QGraphicsObject is to manage its own bounding rect.
                    # This requires overriding boundingRect() and paint().
                    # If the Applet's size is controlled by Plasma or a layout, this is complex.
                    # Assuming direct resize for now:
                    # This is usually done by preparing geometry change.
                    self.prepareGeometryChange()
                    # Then update internal variables that boundingRect() and paint() use.
                    # For a QGraphicsWidget, its size property might be what we change.
                    # If this Applet *is* the item, and its size is not fixed by Plasma:
                    # Let's try using self.resize (from QGraphicsLayoutItem, base of QGraphicsWidget)
                    # This is still conceptual as actual behavior depends on Plasma's management.

                    # For now, we'll just store these and assume update_note will handle it
                    # This part is very tricky without running in Plasma.
                    # The Applet's size might be controlled by its containment.
                    # Let's print what would happen.
                    print(f"  Resizing to {new_width}x{new_height} (conceptual)")
                    # In a real scenario, we'd update self.note_data.size and then call
                    # a method that applies this size to the Applet (e.g. self.resize_applet_to_note_data)
                    # and then `update_note` to save.
                    # For now, let's defer DB update to mouseReleaseEvent.

                    # To visually show effect if this were a simple QGraphicsObject:
                    # self.m_currentSize = QSizeF(new_width, new_height) # imaginary internal var
                    # self.update() # repaint
                    # self.layout().invalidate() # if using layout

            else:
                super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent'):
            if self.is_drag_resize_mode_active and event.button() == Qt.MouseButton.LeftButton:
                event.accept()
                if self._drag_operation: # If a drag/resize was in progress
                    print(f"Drag/Resize: Mouse release. Operation: {self._drag_operation}")
                    if self._drag_operation == "move":
                        new_pos_qpointf = self.scenePos() # Get final position
                        new_pos_dict = {"x": int(new_pos_qpointf.x()), "y": int(new_pos_qpointf.y())}
                        if update_note(self.note_id, {"position": new_pos_dict}):
                            self.note_data["position"] = new_pos_dict
                            print(f"  Note {self.note_id} position updated to {new_pos_dict} in DB.")
                        else:
                            print(f"  Failed to update position for note {self.note_id} in DB.")

                    elif self._drag_operation == "resize":
                        # Get final size (this is where the actual resize logic from mouseMove matters)
                        # For now, let's assume mouseMove has updated some temporary size variables
                        # or we recalculate based on final delta.
                        # This is still using the simplified bottom-right resize logic:
                        delta = event.scenePos() - self._drag_start_mouse_pos
                        new_width = self._drag_start_widget_size.width() + delta.x()
                        new_height = self._drag_start_widget_size.height() + delta.y()
                        min_width, min_height = 50, 30
                        new_width = max(min_width, int(new_width))
                        new_height = max(min_height, int(new_height))
                        new_size_dict = {"width": new_width, "height": new_height}

                        if update_note(self.note_id, {"size": new_size_dict}):
                            self.note_data["size"] = new_size_dict
                            # Apply this size to the applet itself
                            self.resize_applet_to_note_data() # This should make Applet use the new size
                            print(f"  Note {self.note_id} size updated to {new_size_dict} in DB and Applet refreshed.")
                        else:
                            print(f"  Failed to update size for note {self.note_id} in DB.")

                    self._drag_operation = None
                    self._drag_start_mouse_pos = None
                    self._drag_start_widget_pos = None
                    self._drag_start_widget_size = None

                    # Change cursor back to hover-appropriate if still in mode
                    if self.is_drag_resize_mode_active:
                        self.setCursor(self._get_cursor_for_position(event.pos(), self.boundingRect()))
                    else:
                        self.unsetCursor()

            elif self.is_drag_resize_mode_active and event.button() != Qt.MouseButton.LeftButton:
                # Other mouse buttons released - potentially deactivate mode if it was a specific deactivation click
                # Spec: "Clicking anywhere outside the Note Widget deactivates"
                # This event is *inside*. How to handle outside click?
                # Plasma Applets have focusIn/focusOut events, or active/inactive states.
                # If this applet loses focus, it should deactivate drag/resize mode.
                # This is not directly testable here.
                # For now, let's assume deactivation is explicit via menu or a dedicated key for testing.
                pass
            else:
                super().mouseReleaseEvent(event)

        # Placeholder for focus out event to deactivate mode
        def focusOutEvent(self, event: 'QFocusEvent'):
            # This event is for QWidgets. QGraphicsWidget might have something similar
            # or rely on scene focus changes.
            if self.is_drag_resize_mode_active:
                print(f"Plasmoid (Note ID {self.note_id}): Focus lost, deactivating Drag/Resize mode.")
                # self.is_drag_resize_mode_active = False # Don't toggle, just set to false
                # self._update_drag_resize_visuals()
                # self.unsetCursor()
            super().focusOutEvent(event)

        # TODO: Deactivation by clicking outside:
        # This typically involves an event filter on the application or relying on Plasma's
        # focus management for applets. If the applet becomes inactive, mode should turn off.


        def handle_styling_dialog_request(self, note_id):
            if self.note_id != note_id: return
            if not hasattr(self, 'note_qwidget_instance') or not self.note_qwidget_instance:
                print("Error: NoteWidget instance not available for styling.")
                return

            print(f"Plasmoid (Note ID {self.note_id}): Styling dialog requested.")

            if self.is_drag_resize_mode_active:
                self.toggle_drag_resize_mode() # Deactivate drag/resize mode if active

            # Get initial style from the NoteWidget instance itself
            initial_style = self.note_qwidget_instance.get_current_style_for_dialog()
            if not initial_style: # Should not happen if note_data is valid
                print("Error: Could not retrieve initial style from NoteWidget.")
                # Fallback to a very basic default if absolutely necessary
                initial_style = {"transparency": 1.0, "backgroundColor": "#FFFFFF", "margin": 5}


            # The parent of the dialog could be self.note_qwidget_instance or self (the Applet)
            # If self.note_qwidget_instance is used, dialog might be modal to just that widget.
            # If self (Applet) is used, it's modal to the Applet.
            # If running in test mode with QGraphicsView, parent might be the view or None.
            dialog_parent = self.note_qwidget_instance # Or self if Applet is a QWidget
            if not HAS_PLASMA_BINDINGS and not isinstance(self.note_qwidget_instance, QWidget):
                 # In QGraphicsView test, self.note_qwidget_instance is a QWidget,
                 # but self (DesktopNotesPlasmoid) is a QGraphicsWidget.
                 # QDialog needs a QWidget parent or None.
                 dialog_parent = None # Or find the top-level window if possible


            dialog = StylingDialog(
                note_id=self.note_id,
                initial_style=initial_style,
                target_widget_interface=self.note_qwidget_instance, # Pass the NoteWidget instance
                parent=dialog_parent
            )

            # For non-Plasma test, ensure dialog is appropriately modal or standalone
            # dialog.setModal(True) # Already default for QDialog.exec()

            if dialog.exec(): # This will block until dialog is closed
                print(f"Plasmoid (Note ID {self.note_id}): Styling Dialog accepted (OK). Widget should be updated.")
            else:
                print(f"Plasmoid (Note ID {self.note_id}): Styling Dialog rejected (Cancel). Widget should be reverted.")

            # NoteWidget's save_style or revert_style should have handled DB updates and refresh.

        def handle_add_new_note_request(self, source_note_id):
            # This signal comes from a NoteWidget instance (self.note_qwidget_instance)
            # which belongs to this plasmoid (DesktopNotesPlasmoid instance).
            # So, self.note_id should be equal to source_note_id.
            if self.note_id != source_note_id:
                print(f"Warning: handle_add_new_note_request called for source_note_id {source_note_id} on plasmoid for note_id {self.note_id}")
                return

            print(f"Plasmoid (Note ID {self.note_id}): 'Add New Note' requested from this widget.")
            # This action should tell Plasma to create a *new instance* of DesktopNotesPlasmoid.
            # This is not done by this instance itself, but by requesting it from Plasma.
            # Conceptual: Call a Plasma Shell interface.
            print("  Conceptual: This would request Plasma Shell to add a new 'org.kde.desktopnotes' plasmoid.")
            if HAS_PLASMA_BINDINGS:
                # Example (highly speculative for Plasma 6):
                # try:
                #     # PlasmaCore.Plasmoid.plasmoid().createNew(pluginName="org.kde.desktopnotes")
                #     # or some D-Bus call to plasmashell
                #     print("  Attempting to use (speculative) Plasma API to create new widget.")
                # except Exception as e:
                #     print(f"  Error with speculative Plasma API: {e}")
                pass
            else:
                print("  (Running without real Plasma bindings, cannot actually create new plasmoid instance via Plasma)")

        def handle_open_notes_manager_request(self):
            print(f"Plasmoid (Note ID {self.note_id}): 'Open Notes Manager' view requested.")

            # Manage a single instance of the dialog to prevent multiple openings from one plasmoid
            # A more robust solution would be a global singleton manager for such dialogs.
            if not hasattr(self, '_management_dialog_instance') or not self._management_dialog_instance or not self._management_dialog_instance.isVisible():
                # Determine parent for the dialog
                dialog_parent = self.note_qwidget_instance if hasattr(self, 'note_qwidget_instance') else None
                if not HAS_PLASMA_BINDINGS and dialog_parent is None and hasattr(self, 'view') and self.view(): # QGraphicsView from test
                    dialog_parent = self.view()

                self._management_dialog_instance = ManagementView(parent=dialog_parent)
                self._management_dialog_instance.note_status_changed_externally.connect(
                    self._handle_external_note_status_change
                )
                # Show non-modally
                self._management_dialog_instance.show()
            else:
                # Dialog already open, just activate it
                self._management_dialog_instance.activateWindow()
                self._management_dialog_instance.raise_()

        def _handle_external_note_status_change(self, changed_note_id: int, new_status: str):
            """
            Handles the signal from ManagementView when a note's status is changed.
            This plasmoid instance will only react if its own note_id is affected.
            """
            print(f"Plasmoid (Note ID {self.note_id}): Received external status change for note {changed_note_id} to '{new_status}'.")
            if self.note_id == changed_note_id:
                self.note_data["status"] = new_status # Update local cache

                is_visible_in_plasma = False
                if HAS_PLASMA_BINDINGS and hasattr(self, 'isVisible'):
                    is_visible_in_plasma = self.isVisible()

                mock_is_visible = False
                if self.note_qwidget_instance and hasattr(self.note_qwidget_instance, 'isVisible'):
                    mock_is_visible = self.note_qwidget_instance.isVisible()


                if new_status == "shown":
                    if HAS_PLASMA_BINDINGS and hasattr(self, 'setVisible') and not is_visible_in_plasma:
                        self.setVisible(True)
                        print(f"  Plasmoid for note {self.note_id} is now SHOWN (setVisible(True)).")
                    elif not HAS_PLASMA_BINDINGS and self.note_qwidget_instance and not mock_is_visible:
                         if self.proxy_widget_item and hasattr(self.proxy_widget_item, 'show'): self.proxy_widget_item.show()
                         self.note_qwidget_instance.show() # Show QWidget in test
                         print(f"  Simulated SHOW for note {self.note_id} in test mode.")
                    # Refresh display in case other properties also changed or need redraw
                    if self.note_qwidget_instance: self.note_qwidget_instance.refresh_display()

                elif new_status == "hidden":
                    if HAS_PLASMA_BINDINGS and hasattr(self, 'setVisible') and is_visible_in_plasma:
                        self.setVisible(False)
                        print(f"  Plasmoid for note {self.note_id} is now HIDDEN (setVisible(False)).")
                    elif not HAS_PLASMA_BINDINGS and self.note_qwidget_instance and mock_is_visible:
                        if self.proxy_widget_item and hasattr(self.proxy_widget_item, 'hide'): self.proxy_widget_item.hide()
                        self.note_qwidget_instance.hide() # Hide QWidget in test
                        print(f"  Simulated HIDE for note {self.note_id} in test mode.")
            else:
                # This change is for a different note. This plasmoid instance does nothing.
                # A central manager would handle creating/showing/hiding other plasmoids.
                print(f"  Status change for note {changed_note_id} does not affect this plasmoid (ID {self.note_id}).")


        def handle_hide_widget_request(self, note_id):
            if self.note_id != note_id: return
            print(f"Plasmoid (Note ID {self.note_id}): Hide widget requested.")
            if update_note(self.note_id, {"status": "hidden"}):
                self.note_data["status"] = "hidden" # Update local cache
                print(f"  Note {self.note_id} status updated to 'hidden' in DB.")
                # In Plasma, making the Applet invisible:
                if HAS_PLASMA_BINDINGS and hasattr(self, 'setVisible'):
                    self.setVisible(False)
                    print("  Plasmoid instance set to invisible (conceptual).")
                elif self.note_qwidget_instance and not HAS_PLASMA_BINDINGS: # If running test GUI
                    self.note_qwidget_instance.hide() # Hide the QWidget if it's the main view in test
                    if self.proxy_widget_item and hasattr(self.proxy_widget_item, 'hide'): # Hide proxy in QGraphicsScene test
                        self.proxy_widget_item.hide()
                    print("  Simulated hide by hiding QWidget/Proxy in test mode.")
                # Further action: The plasmoid might need to inform Plasma it's hiding.
                # Or Plasma itself handles visibility based on a property of the Applet.
            else:
                print(f"  Failed to update status for note {self.note_id} in DB.")

        def handle_delete_widget_request(self, note_id):
            if self.note_id != note_id: return
            print(f"Plasmoid (Note ID {self.note_id}): Delete widget requested.")
            if delete_note(self.note_id):
                print(f"  Note {self.note_id} removed from database.")
                # In Plasma, the Applet needs to request its own removal.
                # This is a critical part that needs real Plasma bindings.
                if HAS_PLASMA_BINDINGS and hasattr(self, 'remove'):
                    # self.remove() # This is a common name for such a method in Plasmoids
                    print("  Conceptual: Plasmoid instance would call self.remove() to delete itself.")
                elif not HAS_PLASMA_BINDINGS: # If running test GUI
                     if self.note_qwidget_instance: self.note_qwidget_instance.close() # Close QWidget
                     if self.proxy_widget_item:
                         if self.scene(): self.scene().removeItem(self.proxy_widget_item)
                         self.proxy_widget_item.deleteLater()
                     if self.scene(): self.scene().removeItem(self) # Remove applet from scene
                     self.deleteLater() # Delete the QGraphicsWidget itself
                     print("  Simulated delete by closing QWidget/removing from scene in test mode.")
                # After this, this plasmoid instance should be gone.
                # Emit a signal that the main application (if any) can catch to clean up.
                # self.parent.plasmoidIsDeleted(self.note_id) ?
            else:
                print(f"  Failed to delete note {self.note_id} from DB.")

        # --- Original action_add_new_note (kept for reference, but superseded by signal handler) ---
        # def action_add_new_note(self):
        #     """Handles 'Add New Note' from context menu."""
        #     print(f"Plasmoid (note {self.note_id}): Action 'Add New Note' triggered.")
        #     # This action should tell Plasma to create a *new instance* of DesktopNotesPlasmoid.
        #     # This is not done by this instance itself, but by requesting it from Plasma.
        #     # The mechanism for this depends on Plasma internals.
        #     # E.g., could be via a D-Bus call to Plasma Shell or a specific API if available.
        #     # For now, this is a conceptual placeholder.
        #     # If running outside Plasma, we could simulate it by creating another widget locally.
        #     print("  Conceptual: This would request Plasma to add another DesktopNotesPlasmoid.")

            # As a local simulation if not in Plasma:
            # if not HAS_PLASMA_BINDINGS:
            #    print("  Simulating new widget creation locally...")
            #    # This is tricky as it means managing multiple top-level widgets if this
            #    # script is run directly. This factory is for Plasma.
            #    # For testing, a separate test runner would manage multiple plasmoid instances.
            #    pass


        # Plasma provides a factory to create instances of the applet.
        # This factory is registered with Plasma.
        # Example of how it might look (syntax from older PyKDE/plasmapy):
        # KPYPLASMAPY_EXPORT_PLASMA_APPLET(desktopnotes, DesktopNotesPlasmoid)
        # Or in newer systems, Plasma finds the class in the main script.

# This factory function is what Plasma will look for when using pythonscript API.
# It must be named KWin::Plasmoid::createApplet
# or match the X-Plasma-PythonScriptFactory (if that field exists, it's not standard)
# More commonly, Plasma expects a class named *Plasmoid (e.g. MyPlasmoid) in the main script.
# Or, a specific function like `def CreateApplet(parent):`

def CreateApplet(parent):
    """
    This function is expected by Plasma to create an instance of the plasmoid.
    The name might vary based on Plasma version and Python binding specifics.
    Sometimes it's just about having the class definition.
    """
    if not MODULE_IMPORT_SUCCESS:
        print("Cannot create applet, module imports failed.", file=sys.stderr)
        # Return a dummy or raise an error if appropriate
        # For robustness, return a minimal QGraphicsWidget with an error message if possible
        error_widget = QGraphicsWidget(parent)
        # Ideally, display error text on it.
        return error_widget

    print(f"CreateApplet factory called with parent: {parent}")
    return DesktopNotesPlasmoid(parent)


# --- Direct Test Execution (Conceptual) ---
# This part is for trying to run ONE instance of the "plasmoid" structure
# outside of Plasma, for very basic structural testing. It won't behave like in Plasma.
if __name__ == '__main__':
    if not MODULE_IMPORT_SUCCESS:
        print("Halting test run due to module import errors.", file=sys.stderr)
        sys.exit(1)

    print("Running main_plasmoid.py directly for basic structural test.")

    # We need a QApplication to host any QWidgets/QGraphicsWidgets
    app = QApplication(sys.argv)

    # Simulate the creation of one plasmoid instance.
    # In Plasma, 'parent' would be provided by Plasma. Here, it's None or a dummy.
    # We can't fully simulate the QGraphicsWidget lifecycle without a QGraphicsScene/View.

    # To test the QWidget part (NoteWidget) more directly via the plasmoid structure:
    # Create a dummy parent QWidget to host the Applet (if it were a QWidget itself)
    # or to host the NoteWidget created by the Applet.

    # Since our Applet is a QGraphicsWidget, it needs a QGraphicsView to be seen.
    from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    view.setWindowTitle("Test: DesktopNotesPlasmoid in QGraphicsView")

    # Create the plasmoid instance.
    # The `parent` for an Applet is typically the Plasma containment.
    # For this test, it can be None, or if it needs a QGraphicsItem parent, that's tricky.
    # Let's assume it can be parentless for QGraphicsObject creation, then added to scene.
    try:
        # This is the crucial part: how Plasma instantiates and uses the Applet.
        # If `CreateApplet` is the factory, Plasma calls that.
        # If the class itself is discovered, Plasma instantiates `DesktopNotesPlasmoid(parentPlasmaObject)`.

        # For this test, let's instantiate DesktopNotesPlasmoid directly.
        # It inherits QGraphicsWidget, so it's a QGraphicsItem.
        plasmoid_instance = DesktopNotesPlasmoid(parent=None) # Parent is a QGraphicsItem, not QWidget
        scene.addItem(plasmoid_instance) # Add the QGraphicsWidget-based plasmoid to the scene

        # The plasmoid_instance should internally create and manage its NoteWidget (QWidget)
        # and embed it using QGraphicsProxyWidget.
        # We need to ensure the NoteWidget part gets created and shown.

        # Check if the NoteWidget (QWidget) was created and proxied
        if hasattr(plasmoid_instance, 'note_qwidget_instance') and plasmoid_instance.note_qwidget_instance:
            # The NoteWidget (QWidget) itself should not be shown directly using .show()
            # if it's embedded in a QGraphicsProxyWidget within a QGraphicsScene.
            # The QGraphicsView (view.show()) will handle displaying the scene and its items.
            print("NoteWidget QWidget instance seems to be created by the Plasmoid.")

            # The Applet (plasmoid_instance) should have a size.
            # plasmoid_instance.resize_applet_to_note_data() is called in _create_new_note_instance.
            # The QGraphicsView needs a size too.
            view.resize(400, 300) # Example size for the view
            view.show()

            print(f"Plasmoid instance for note ID {plasmoid_instance.note_id} should be visible in the QGraphicsView.")
            print("  Note: This test doesn't fully replicate Plasma environment (theming, window management, etc.).")
            print("  It primarily checks if the plasmoid structure can instantiate and host the NoteWidget.")

        else:
            print("Error: Plasmoid did not seem to create/proxy its NoteWidget instance.")

    except Exception as e:
        print(f"Error during plasmoid test instantiation: {e}")
        import traceback
        traceback.print_exc()

    sys.exit(app.exec())

# Make sure to clean up the database or test files if any were created specifically for this test run.
# The NoteWidget test already does some cleanup; this script might add more notes.
# Consider a global test setup/teardown for the database if running multiple tests.
