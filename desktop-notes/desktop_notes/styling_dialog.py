import copy # For deepcopying style dict

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox, QPushButton,
    QColorDialog, QDialogButtonBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette

from . import config
# Assuming NoteWidget is needed for type hinting or direct interaction.
# from .note_widget import NoteWidget # Avoid circular import if NoteWidget creates this. Pass widget instance.

class StylingDialog(QDialog):
    def __init__(self, target_note_widget, data_manager, parent=None):
        super().__init__(parent)

        self.target_note_widget = target_note_widget
        self.data_manager = data_manager # For persisting on OK

        if not self.target_note_widget or not hasattr(self.target_note_widget, 'current_data'):
            raise ValueError("Valid target_note_widget with current_data is required.")

        self.original_style = copy.deepcopy(self.target_note_widget.current_data.get('style', {}))
        self.current_style_changes = copy.deepcopy(self.original_style) # Track changes made in this dialog session

        self.setWindowTitle(f"Style Note '{self.target_note_widget.note_id}'")
        self._init_ui()
        self._load_initial_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Transparency
        transparency_layout = QHBoxLayout()
        transparency_layout.addWidget(QLabel("Transparency:"))
        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setRange(0, 100) # 0% to 100%
        self.transparency_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        transparency_layout.addWidget(self.transparency_slider)
        self.transparency_value_label = QLabel("100%") # Initial display
        transparency_layout.addWidget(self.transparency_value_label)
        layout.addLayout(transparency_layout)

        # Background Color
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel("Background Color:"))
        self.bg_color_button = QPushButton("Choose Color")
        self.bg_color_preview = QLabel() # Shows selected color
        self.bg_color_preview.setFixedSize(50,20)
        self.bg_color_preview.setAutoFillBackground(True)
        bg_color_layout.addWidget(self.bg_color_button)
        bg_color_layout.addWidget(self.bg_color_preview)
        bg_color_layout.addStretch()
        layout.addLayout(bg_color_layout)

        # Margin
        margin_layout = QHBoxLayout()
        margin_layout.addWidget(QLabel("Margin (px):"))
        self.margin_slider = QSlider(Qt.Orientation.Horizontal)
        self.margin_slider.setRange(0, config.MAX_MARGIN) # e.g., 0 to 50px
        self.margin_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.margin_spinbox = QSpinBox()
        self.margin_spinbox.setRange(0, config.MAX_MARGIN)
        margin_layout.addWidget(self.margin_slider)
        margin_layout.addWidget(self.margin_spinbox)
        layout.addLayout(margin_layout)

        # Dialog Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.button_box)

        # Connections
        self.transparency_slider.valueChanged.connect(self._transparency_changed)
        self.bg_color_button.clicked.connect(self._choose_bg_color)
        self.margin_slider.valueChanged.connect(self.margin_spinbox.setValue)
        self.margin_spinbox.valueChanged.connect(self.margin_slider.setValue)
        self.margin_spinbox.valueChanged.connect(self._margin_changed) # Connect only one to avoid double signals

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _load_initial_style(self):
        # Transparency
        transparency = self.original_style.get('transparency', config.DEFAULT_NOTE_TRANSPARENCY)
        self.transparency_slider.setValue(int(transparency * 100))
        self.transparency_value_label.setText(f"{int(transparency * 100)}%")

        # Background Color
        bg_color_hex = self.original_style.get('backgroundColor', config.DEFAULT_NOTE_BG_COLOR)
        self._update_bg_color_preview(QColor(bg_color_hex))

        # Margin
        margin = self.original_style.get('margin', config.DEFAULT_NOTE_MARGIN)
        self.margin_slider.setValue(margin)
        self.margin_spinbox.setValue(margin) # This will also set slider due to connection

    def _transparency_changed(self, value):
        transparency_float = value / 100.0
        self.transparency_value_label.setText(f"{value}%")
        self.current_style_changes['transparency'] = transparency_float
        self._apply_preview()

    def _choose_bg_color(self):
        current_color_hex = self.current_style_changes.get('backgroundColor', config.DEFAULT_NOTE_BG_COLOR)
        color = QColorDialog.getColor(QColor(current_color_hex), self, "Select Background Color")
        if color.isValid():
            self.current_style_changes['backgroundColor'] = color.name() # Hex string #RRGGBB
            self._update_bg_color_preview(color)
            self._apply_preview()

    def _update_bg_color_preview(self, color: QColor):
        palette = self.bg_color_preview.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        self.bg_color_preview.setPalette(palette)

    def _margin_changed(self, value):
        self.current_style_changes['margin'] = value
        self._apply_preview()

    def _apply_preview(self):
        """Applies the current_style_changes to the target NoteWidget for real-time preview."""
        if self.target_note_widget:
            # Pass only the changed values for partial update if apply_style supports it,
            # or pass the full current_style_changes dict.
            # NoteWidget.apply_style should handle merging with its existing style.
            self.target_note_widget.apply_style(copy.deepcopy(self.current_style_changes), persist=False)

    def accept(self):
        """Ok button clicked: Persist changes."""
        if self.target_note_widget and self.data_manager:
            # Ensure the final style is applied and persisted
            # The target_note_widget's current_data.style should already reflect current_style_changes due to _apply_preview
            # So, we just need to trigger the persistence.
            self.data_manager.update_note(
                self.target_note_widget.note_id,
                {"style": self.current_style_changes}
            )
            # Optionally, call apply_style one last time with persist=True if DM update isn't enough
            # self.target_note_widget.apply_style(self.current_style_changes, persist=True)
            print(f"StylingDialog: Changes accepted and persisted for note {self.target_note_widget.note_id}.")
        super().accept()

    def reject(self):
        """Cancel button clicked: Revert to original style."""
        if self.target_note_widget:
            self.target_note_widget.apply_style(self.original_style, persist=False)
            # Persist might be needed if intermediate previews were saved by mistake,
            # but ideally apply_style(persist=False) doesn't save.
            # If we want to be absolutely sure, we could re-save original_style to DB.
            # self.data_manager.update_note(self.target_note_widget.note_id, {"style": self.original_style})
            print(f"StylingDialog: Changes cancelled for note {self.target_note_widget.note_id}. Reverted to original.")
        super().reject()

# Example Usage:
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    # Need a mock NoteWidget and DataManager for testing
    # Assuming config.py and note_widget.py are in paths visible to Python

    # --- Mock NoteWidget ---
    class MockNoteWidget:
        def __init__(self, note_id, initial_style):
            self.note_id = note_id
            self.current_data = {
                "id": note_id,
                "style": copy.deepcopy(initial_style),
                # other fields...
            }
            self.applied_styles = [] # To track calls to apply_style

        def apply_style(self, style_data, persist=True):
            print(f"MockNoteWidget '{self.note_id}': apply_style({style_data}, persist={persist}) called.")
            self.current_data['style'].update(style_data) # Simulate style update
            self.applied_styles.append({'style': copy.deepcopy(style_data), 'persist': persist})

        def update(self): # Mock QWidget.update()
            print(f"MockNoteWidget '{self.note_id}': update() called (simulating repaint).")

    # --- Mock DataManager ---
    class MockDataManager:
        def update_note(self, note_id, data):
            print(f"MockDataManager: update_note(note_id={note_id}, data={data}) called.")
            # Simulate successful update
            return True

    app = QApplication(sys.argv)

    # Create mock objects
    initial_style_for_widget = {
        "transparency": 0.8,
        "backgroundColor": "#abcdef",
        "margin": 10
    }
    mock_widget = MockNoteWidget(note_id="test01", initial_style=initial_style_for_widget)
    mock_dm = MockDataManager()

    # Create and show the dialog
    dialog = StylingDialog(target_note_widget=mock_widget, data_manager=mock_dm)
    dialog.show()

    # Simulate interaction (normally done by user)
    # dialog.transparency_slider.setValue(50) # Change transparency
    # dialog.margin_spinbox.setValue(20)    # Change margin
    # Test with a color change (would require user interaction for QColorDialog)
    # dialog._update_bg_color_preview(QColor("#ff0000"))
    # dialog.current_style_changes['backgroundColor'] = "#ff0000"
    # dialog._apply_preview()


    result = dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        print("\nDialog accepted.")
        print(f"Final style in widget's current_data: {mock_widget.current_data['style']}")
        # Check if DM was called to persist
    else:
        print("\nDialog cancelled or closed.")
        print(f"Style in widget's current_data (should be original): {mock_widget.current_data['style']}")
        assert mock_widget.current_data['style'] == initial_style_for_widget, "Style did not revert correctly on cancel."

    print("\nApplied styles log on mock_widget:")
    for entry in mock_widget.applied_styles:
        print(entry)

    # sys.exit(app.exec()) # Not needed if dialog.exec() is used for modal
    sys.exit(0)
