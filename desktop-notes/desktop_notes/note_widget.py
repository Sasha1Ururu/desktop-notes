import subprocess
import os
from pathlib import Path # Ensure Path is imported

from PyQt6.QtWidgets import (QWidget, QTextEdit, QVBoxLayout, QApplication, QMenu, QFileDialog)
from PyQt6.QtGui import QColor, QPalette, QFont, QTextOption, QAction, QCursor, QMouseEvent, QFocusEvent # Added QMouseEvent, QFocusEvent
from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal, QPointF, QSizeF # Added QSizeF

from . import config
from .data_manager import DataManager
from .utils import render_markdown

class NoteWidget(QWidget):
    # Signals to communicate with the main applet or manager
    request_new_note = pyqtSignal(QPoint)
    request_open_all_notes = pyqtSignal()
    request_open_styling_dialog = pyqtSignal(int) # note_id
    widget_hidden = pyqtSignal(int) # note_id
    widget_deleted = pyqtSignal(int) # note_id
    size_changed_by_user = pyqtSignal(QSize) # To inform applet about size changes

    def __init__(self, note_id, data_manager, initial_data, parent_applet=None, parent=None):
        super().__init__(parent)
        self.note_id = note_id
        self.data_manager = data_manager
        self.current_data = initial_data
        self.parent_applet = parent_applet

        self._init_ui()
        self.apply_note_data(self.current_data, persist_initial_style=False)


    def _init_ui(self):
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.text_display = QTextEdit(self)
        self.text_display.setReadOnly(True)
        self.text_display.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.text_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.layout().addWidget(self.text_display)

        self._is_dragging = False
        self._drag_start_mouse_pos = QPoint() # For mouse delta calculation
        self._drag_start_widget_pos = QPointF() # For applet's initial QPointF position

        self._is_resizing = False
        # self._resize_start_position = QPoint() # Not needed if using _drag_start_mouse_pos
        self._resize_start_widget_size = QSize()
        self._resize_edge = None # Stores the Qt.CursorShape enum for the edge being resized

        self._drag_resize_mode_active = False

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setMouseTracking(False)

        self.border_color = QColor(config.DRAG_RESIZE_BORDER_COLOR)
        self.border_width = config.DRAG_RESIZE_BORDER_WIDTH
        # self.original_stylesheet = self.styleSheet() # Not strictly needed if _update_border_style is robust

    def apply_note_data(self, note_data, persist_initial_style=True):
        self.current_data = note_data
        if 'size' in note_data and 'width' in note_data['size'] and 'height' in note_data['size']:
            self.resize(QSize(note_data['size']['width'], note_data['size']['height']))

        if 'style' in note_data:
            self.apply_style(note_data['style'], persist=persist_initial_style)
        self.load_content()

    def load_content(self):
        if not self.current_data or self.current_data.get('filepath') is None:
            self.text_display.clear()
            font = self.text_display.font()
            font.setPointSize(config.PLACEHOLDER_FONT_SIZE_PT)
            self.text_display.setFont(font)
            self.text_display.setText(config.PLACEHOLDER_TEXT)
            self.text_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            filepath = self.current_data['filepath']
            self.text_display.setFont(QFont())
            self.text_display.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if filepath.lower().endswith('.md'):
                    self.text_display.setHtml(render_markdown(content))
                elif filepath.lower().endswith('.txt'):
                    self.text_display.setPlainText(content)
                else:
                    self.text_display.setPlainText(f"Unsupported file type: {filepath}")
            except FileNotFoundError:
                self.text_display.setPlainText(f"Error: File not found.\n{filepath}")
            except Exception as e:
                self.text_display.setPlainText(f"Error loading file: {e}")
        if 'style' in self.current_data: # Re-apply style for consistent padding/bg after content/font changes
             self.apply_style(self.current_data['style'], persist=False)

    def apply_style(self, style_data, persist=True):
        if not style_data: return
        self.current_data['style'].update(style_data) # Ensure internal state is updated

        bg_color_hex = self.current_data['style'].get('backgroundColor', config.DEFAULT_NOTE_BG_COLOR)
        transparency = self.current_data['style'].get('transparency', config.DEFAULT_NOTE_TRANSPARENCY)

        color = QColor(bg_color_hex)
        alpha_val = int(transparency * 255)
        color.setAlpha(alpha_val)

        self.setAutoFillBackground(True)
        base_palette = self.palette() # Get current palette
        base_palette.setColor(QPalette.ColorRole.Window, color) # Set main background color
        self.setPalette(base_palette)

        self._update_border_style() # This will also apply text_display padding

        if persist and self.data_manager and self.note_id is not None:
            self.data_manager.update_note(self.note_id, {"style": self.current_data['style']})

    def _update_border_style(self):
        margin = self.current_data['style'].get('margin', config.DEFAULT_NOTE_MARGIN)
        # Stylesheet for QTextEdit (always applied)
        text_edit_ss = f"QTextEdit {{ background-color: transparent; border: none; padding: {margin}px; }}"

        widget_border_ss = ""
        if self._drag_resize_mode_active:
            # Using object name for specific targeting of the border to this widget instance
            self.setObjectName("NoteWidgetFrameActive")
            widget_border_ss = f"""
                QWidget#NoteWidgetFrameActive {{
                    border: {config.DRAG_RESIZE_BORDER_WIDTH}px solid {config.DRAG_RESIZE_BORDER_COLOR};
                }}
            """
        else:
            # Reset object name or ensure border is none for the default state
            self.setObjectName("NoteWidgetFrameInactive") # Or simply ""
            widget_border_ss = "QWidget#NoteWidgetFrameInactive { border: none; }"
            # If objectName is cleared (""), then a general QWidget style might apply if not careful.
            # It's safer to ensure border: none for the inactive state specifically if an object name is used.

        self.setStyleSheet(widget_border_ss + text_edit_ss)


    def mousePressEvent(self, event: QMouseEvent):
        if self._drag_resize_mode_active and event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_mouse_pos = event.globalPosition().toPoint()

            if self.parent_applet and hasattr(self.parent_applet, 'pos') and callable(self.parent_applet.pos):
                self._drag_start_widget_pos = self.parent_applet.pos() # This is QPointF
            else: # Fallback for standalone testing
                self._drag_start_widget_pos = QPointF(self.pos())

            self._resize_edge = self._get_resize_edge(event.position().toPoint())
            if self._resize_edge is not None: # Resize action
                self._is_resizing = True
                self._resize_start_widget_size = self.size() # Current QSize
            else: # Drag action
                self._is_dragging = True
            event.accept() # Indicate event is handled
            return

        if not self._drag_resize_mode_active and event.button() == Qt.MouseButton.LeftButton:
            self._handle_left_click()
            event.accept()
            return

        super().mousePressEvent(event) # Pass on if not handled


    def _get_resize_edge(self, local_pos: QPoint):
        handle_margin = 8 # Sensitivity for resize handles
        w = self.width()
        h = self.height()

        on_top = 0 <= local_pos.y() < handle_margin
        on_bottom = h - handle_margin <= local_pos.y() < h
        on_left = 0 <= local_pos.x() < handle_margin
        on_right = w - handle_margin <= local_pos.x() < w

        if on_top and on_left: return Qt.CursorShape.SizeFDiagCursor
        if on_top and on_right: return Qt.CursorShape.SizeBDiagCursor
        if on_bottom and on_left: return Qt.CursorShape.SizeBDiagCursor
        if on_bottom and on_right: return Qt.CursorShape.SizeFDiagCursor
        if on_top: return Qt.CursorShape.SizeVerCursor
        if on_bottom: return Qt.CursorShape.SizeVerCursor
        if on_left: return Qt.CursorShape.SizeHorCursor
        if on_right: return Qt.CursorShape.SizeHorCursor
        return None


    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._drag_resize_mode_active:
            super().mouseMoveEvent(event)
            return

        current_mouse_global_pos = event.globalPosition().toPoint()
        delta = current_mouse_global_pos - self._drag_start_mouse_pos

        if self._is_dragging:
            if self.parent_applet and hasattr(self.parent_applet, 'setPos'):
                new_applet_pos = self._drag_start_widget_pos + QPointF(delta) # Add QPointF for precision
                self.parent_applet.setPos(new_applet_pos)
            else: # Standalone behavior
                self.move(self._drag_start_widget_pos.toPoint() + delta)
            event.accept()
            return

        if self._is_resizing:
            new_w, new_h = self._resize_start_widget_size.width(), self._resize_start_widget_size.height()

            # Simplified resize logic (assumes bottom-right like behavior for edges)
            # More precise logic would check self._resize_edge against specific L,R,T,B,Corners
            if self._resize_edge == Qt.CursorShape.SizeHorCursor or \
               self._resize_edge == Qt.CursorShape.SizeFDiagCursor or \
               self._resize_edge == Qt.CursorShape.SizeBDiagCursor:
                new_w += delta.x()

            if self._resize_edge == Qt.CursorShape.SizeVerCursor or \
               self._resize_edge == Qt.CursorShape.SizeFDiagCursor or \
               self._resize_edge == Qt.CursorShape.SizeBDiagCursor:
                new_h += delta.y()

            new_w = max(config.MIN_NOTE_WIDTH, new_w)
            new_h = max(config.MIN_NOTE_HEIGHT, new_h)

            self.resize(QSize(new_w, new_h))
            if self.parent_applet and hasattr(self.parent_applet, 'setPreferredSize'):
                self.parent_applet.setPreferredSize(QSizeF(self.size())) # QWidget.size() returns QSize
                if hasattr(self.parent_applet, 'updateGeometry'): self.parent_applet.updateGeometry()
                elif hasattr(self.parent_applet, 'update'): self.parent_applet.update()

            self.update() # Repaint this widget
            event.accept()
            return

        # If in drag/resize mode but not actively dragging/resizing, update cursor
        current_resize_handle = self._get_resize_edge(event.position().toPoint())
        if current_resize_handle is not None:
            self.setCursor(QCursor(current_resize_handle))
        else:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor)) # Move cursor
        event.accept()


    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_resize_mode_active and event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging or self._is_resizing:
                self._is_dragging = False
                self._is_resizing = False
                self._save_geometry_to_db() # Persist size

                # Update cursor based on current position if still inside, or reset if exited mode
                if self.rect().contains(event.position().toPoint()):
                    current_resize_handle = self._get_resize_edge(event.position().toPoint())
                    if current_resize_handle is not None:
                        self.setCursor(QCursor(current_resize_handle))
                    else:
                        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
                else: # Mouse released outside, but mode is still active until toggled or focus lost
                    self.setCursor(Qt.CursorShape.ArrowCursor) # Or SizeAllCursor if preferred when active
            event.accept()
            return
        super().mouseReleaseEvent(event)


    def _handle_left_click(self):
        if self.current_data.get('filepath') is None:
            self._handle_select_file()
        else:
            self._open_in_external_editor()

    def _open_in_external_editor(self):
        filepath = self.current_data.get('filepath')
        if not filepath or not os.path.exists(filepath):
            print(f"Filepath is invalid or file does not exist: {filepath}")
            return

        editor_cmd_template = config.DEFAULT_TEXT_EDITOR_CMD_PATTERN
        try:
            command_to_run = []
            if "{filepath}" in editor_cmd_template:
                parts = editor_cmd_template.split()
                for part in parts:
                    command_to_run.append(filepath if part == "{filepath}" else part)
            else:
                command_to_run = editor_cmd_template.split()
                command_to_run.append(filepath)

            print(f"Attempting to open '{filepath}' with command: {command_to_run}")
            subprocess.Popen(command_to_run)
        except Exception as e:
            print(f"Error opening file '{filepath}' in external editor: {e}")
            # In a real app: Show user-friendly error (e.g., Plasma notification)

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        action_select_file = menu.addAction("Select file")
        action_drag_resize = menu.addAction("Drag/Resize")
        if self._drag_resize_mode_active:
            action_drag_resize.setText("Exit Drag/Resize Mode")
        action_styling = menu.addAction("Styling")
        menu.addSeparator()
        action_add_new_note = menu.addAction("Add New Note")
        action_open_notes = menu.addAction("Open Notes")
        menu.addSeparator()
        action_hide = menu.addAction("Hide")
        action_delete = menu.addAction("Delete")

        action_select_file.triggered.connect(self._handle_select_file)
        action_drag_resize.triggered.connect(self._handle_toggle_drag_resize)
        action_styling.triggered.connect(self._handle_styling)
        action_add_new_note.triggered.connect(self._handle_add_new_note)
        action_open_notes.triggered.connect(self._handle_open_notes)
        action_hide.triggered.connect(self._handle_hide)
        action_delete.triggered.connect(self._handle_delete)
        menu.exec(self.mapToGlobal(pos))

    def _handle_select_file(self):
        current_filepath = self.current_data.get('filepath', '')
        start_dir = os.path.dirname(current_filepath) if current_filepath and os.path.isdir(os.path.dirname(current_filepath)) else str(Path.home())

        filepath, selected_filter = QFileDialog.getSaveFileName(
            self, "Select or Create Note File", start_dir, config.SUPPORTED_FILE_TYPES_FILTER
        )
        if filepath:
            if not os.path.exists(filepath):
                try:
                    with open(filepath, 'w', encoding='utf-8') as f: pass # Create empty file
                    print(f"Created new empty file: {filepath}")
                except Exception as e:
                    print(f"Error creating file {filepath}: {e}")
                    # In a real app: Show user-friendly error
                    return
            self.current_data['filepath'] = filepath
            if self.data_manager.update_note(self.note_id, {"filepath": filepath}):
                self.load_content()
                print(f"Note {self.note_id} filepath updated to: {filepath}")
            else:
                print(f"Error updating filepath in DB for note {self.note_id}")
        else:
            print(f"Note {self.note_id}: File selection cancelled.")

    def _handle_toggle_drag_resize(self):
        self._drag_resize_mode_active = not self._drag_resize_mode_active
        if self._drag_resize_mode_active:
            print(f"Note {self.note_id}: Entered Drag/Resize mode.")
            self.setMouseTracking(True)
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            print(f"Note {self.note_id}: Exited Drag/Resize mode.")
            self.setMouseTracking(False)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self._is_dragging or self._is_resizing: # Finalize if an action was in progress
                self._is_dragging = False
                self._is_resizing = False
                self._save_geometry_to_db()
        self._update_border_style()
        self.update()

    def _save_geometry_to_db(self):
        current_size_dict = {"width": self.width(), "height": self.height()}
        if self.data_manager.update_note(self.note_id, {"size": current_size_dict}):
            self.current_data['size'] = current_size_dict
            print(f"Note {self.note_id}: Size updated in DB to {self.current_data['size']}")
            self.size_changed_by_user.emit(self.size()) # QSize
            if self.parent_applet and hasattr(self.parent_applet, 'setPreferredSize'):
                 self.parent_applet.setPreferredSize(QSizeF(self.size()))
                 if hasattr(self.parent_applet, 'updateGeometry'): self.parent_applet.updateGeometry()
        else:
            print(f"Error updating size in DB for note {self.note_id}")

    def _handle_styling(self):
        print(f"Note {self.note_id}: Styling action triggered.")
        self.request_open_styling_dialog.emit(self.note_id)

    def _handle_add_new_note(self):
        print(f"Note {self.note_id}: Add New Note action triggered.")
        base_pos = QPoint(0,0)
        if self.parent_applet and hasattr(self.parent_applet, 'pos') and callable(self.parent_applet.pos):
            base_pos = self.parent_applet.pos().toPoint()
        else: # Fallback for standalone testing
            base_pos = self.mapToGlobal(QPoint(0,0)) # mapToGlobal needs self to be shown

        # Adjust offset based on spec: adjacent or cascading
        suggested_pos = base_pos + QPoint(self.width() + config.NEW_NOTE_OFFSET_X if self.isVisible() else config.NEW_NOTE_OFFSET_X,
                                          config.NEW_NOTE_OFFSET_Y)
        self.request_new_note.emit(suggested_pos)

    def _handle_open_notes(self):
        print(f"Note {self.note_id}: Open Notes action triggered.")
        self.request_open_all_notes.emit()

    def _handle_hide(self):
        print(f"Note {self.note_id}: Hide action triggered.")
        if self.data_manager.update_note(self.note_id, {"status": config.NOTE_STATUS_HIDDEN}):
            self.current_data["status"] = config.NOTE_STATUS_HIDDEN
            self.widget_hidden.emit(self.note_id)
        else:
            print(f"Error updating status to hidden in DB for note {self.note_id}")

    def _handle_delete(self):
        print(f"Note {self.note_id}: Delete action triggered.")
        if self.data_manager.delete_note(self.note_id):
            self.widget_deleted.emit(self.note_id)
        else:
            print(f"Error deleting note {self.note_id} from DB.")

    def focusOutEvent(self, event: QFocusEvent):
        if self._drag_resize_mode_active:
            print(f"Note {self.note_id}: Focus lost, exiting Drag/Resize mode.")
            self._drag_resize_mode_active = False # Set before calling other methods that check it
            self.setMouseTracking(False)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self._is_dragging or self._is_resizing:
                self._is_dragging = False
                self._is_resizing = False
                self._save_geometry_to_db()
            self._update_border_style()
            self.update()
        super().focusOutEvent(event)


if __name__ == '__main__':
    import sys
    # from PyQt6.QtGui import QFocusEvent, QMouseEvent # Already imported
    # from PyQt6.QtCore import QSizeF # Already imported

    app = QApplication(sys.argv)

    class MockApplet:
        def __init__(self, widget_ref=None):
            self.widget_ref = widget_ref
            self._pos = QPointF(100.0, 100.0)
            self._size = QSizeF(config.DEFAULT_NOTE_WIDTH, config.DEFAULT_NOTE_HEIGHT)
            print("MockApplet Initialized")

        def handle_new_note_request(self, pos): print(f"MockApplet: Request for new note at {pos}")
        def handle_open_all_notes(self): print(f"MockApplet: Request to open all notes")
        def handle_open_styling_dialog(self, note_id): print(f"MockApplet: Request to open styling for note {note_id}")
        def handle_widget_hidden(self, note_id):
            print(f"MockApplet: Note {note_id} hidden.")
            if self.widget_ref and self.widget_ref.note_id == note_id: self.widget_ref.hide()
        def handle_widget_deleted(self, note_id):
            print(f"MockApplet: Note {note_id} deleted.")
            if self.widget_ref and self.widget_ref.note_id == note_id: self.widget_ref.close()

        def pos(self): return self._pos
        def setPos(self, new_pos: QPointF):
            print(f"MockApplet: setPos({new_pos}) called.")
            self._pos = new_pos
        def setPreferredSize(self, new_size: QSizeF):
            print(f"MockApplet: setPreferredSize({new_size}) called.")
            self._size = new_size
        def update(self): print("MockApplet: update() called.")
        def updateGeometry(self): print("MockApplet: updateGeometry() called.")


    class MockDataManager:
        def __init__(self): self.notes = {}
        def update_note(self, note_id, data):
            print(f"MockDM: Updating note {note_id} with {data}")
            if note_id not in self.notes: self.notes[note_id] = {}
            if "filepath" in data and data["filepath"] == "fail_db_update.txt": return False
            for key, value in data.items():
                if isinstance(value, dict) and key in self.notes[note_id] and isinstance(self.notes[note_id][key], dict):
                    self.notes[note_id][key].update(value)
                else: self.notes[note_id][key] = value
            return True
        def get_note(self, note_id):
            base_note = {"id": note_id, "status": "shown", "filepath": None,
                         "position": {"x": 50, "y": 50},
                         "size": {"width": config.DEFAULT_NOTE_WIDTH, "height": config.DEFAULT_NOTE_HEIGHT},
                         "style": config.INITIAL_STYLE.copy()}
            if note_id in self.notes:
                merged_note = base_note.copy(); merged_note.update(self.notes[note_id]) # Simple update for test
                return merged_note
            return base_note
        def delete_note(self, note_id):
            print(f"MockDM: Deleting note {note_id}")
            if note_id in self.notes: del self.notes[note_id]
            return True

    mock_dm = MockDataManager()
    initial_widget_data = {"id": 1, "status": "shown", "filepath": None,
                           "position": {"x": 150, "y": 150},
                           "size": {"width": 320, "height": 220},
                           "style": config.INITIAL_STYLE.copy()}
    mock_dm.notes[1] = initial_widget_data.copy()

    note_widget_instance = NoteWidget(note_id=1, data_manager=mock_dm,
                                      initial_data=initial_widget_data.copy(), parent_applet=None)
    mock_applet_for_widget = MockApplet(widget_ref=note_widget_instance)
    note_widget_instance.parent_applet = mock_applet_for_widget

    note_widget_instance.setWindowTitle("Note Widget - Final Review Test")
    note_widget_instance.request_new_note.connect(mock_applet_for_widget.handle_new_note_request)
    note_widget_instance.request_open_all_notes.connect(mock_applet_for_widget.handle_open_all_notes)
    note_widget_instance.request_open_styling_dialog.connect(mock_applet_for_widget.handle_open_styling_dialog)
    note_widget_instance.widget_hidden.connect(mock_applet_for_widget.handle_widget_hidden)
    note_widget_instance.widget_deleted.connect(mock_applet_for_widget.handle_widget_deleted)
    note_widget_instance.size_changed_by_user.connect(lambda sz: print(f"Test: size_changed_by_user: {sz}"))

    note_widget_instance.move(initial_widget_data["position"]["x"], initial_widget_data["position"]["y"])
    note_widget_instance.show()

    dummy_file = Path("./dummy_test_final.txt")
    if not dummy_file.exists():
        with open(dummy_file, "w", encoding='utf-8') as f: f.write("Final review test file.")
    print(f"Dummy file for testing: {dummy_file.resolve()}")
    print("Test interactions: Left/Right click, Drag/Resize, Focus Out.")

    exit_code = app.exec()
    if dummy_file.exists(): dummy_file.unlink()
    sys.exit(exit_code)
