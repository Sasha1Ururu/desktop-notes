import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QColorDialog, QSpinBox, QDialogButtonBox, QApplication, QWidget
)
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import Qt

# For testing, we need a way to simulate the main widget that this dialog controls
class MockNoteWidgetForStyling:
    def __init__(self, note_id, initial_style):
        self.note_id = note_id
        self.current_style = initial_style.copy() # Simulate current style of the widget
        self.widget_ref = QWidget() # A dummy QWidget to show color changes for testing dialog
        self.widget_ref.setAutoFillBackground(True)
        self.widget_ref.setMinimumSize(200,100)
        self.apply_style_to_mock(self.current_style)

    def update_style_preview(self, style_attribute, value):
        print(f"MockNoteWidget (ID {self.note_id}): Previewing style {style_attribute} = {value}")
        # In a real app, this would directly manipulate the NoteWidget's appearance
        temp_style = self.current_style.copy()
        temp_style[style_attribute] = value
        self.apply_style_to_mock(temp_style) # Apply to the internal mock for visual feedback

    def apply_style_to_mock(self, style_data):
        # This method is just for the dummy widget in the test.
        # Real widget would have its own styling update mechanism.
        bg_color = QColor(style_data.get("backgroundColor", "#FFFFFF"))
        transparency = style_data.get("transparency", 1.0)
        bg_color.setAlphaF(transparency)

        palette = self.widget_ref.palette()
        palette.setColor(QPalette.ColorRole.Window, bg_color)
        self.widget_ref.setPalette(palette)

        # Margin is harder to show on a simple QWidget without content.
        # We'd print it or have a nested widget.
        print(f"  Mock style applied: BG {bg_color.name()}, Alpha {transparency}, Margin {style_data.get('margin',0)}")


    def get_current_style_for_dialog(self) -> dict:
        # Returns the style in the format the dialog expects
        return self.current_style

    def save_style(self, style_data: dict):
        # This is where the real NoteWidget would persist the style (e.g., update DB)
        print(f"MockNoteWidget (ID {self.note_id}): 'Save' called with style: {style_data}")
        self.current_style = style_data.copy()
        self.apply_style_to_mock(self.current_style) # Ensure mock reflects saved state
        # In real app: update_note(self.note_id, {"style": self.current_style})
        #              self.note_qwidget_instance.refresh_display()

    def revert_style(self, style_data: dict):
        print(f"MockNoteWidget (ID {self.note_id}): 'Revert' called with style: {style_data}")
        self.current_style = style_data.copy()
        self.apply_style_to_mock(self.current_style)
        # In real app: update_note(self.note_id, {"style": self.current_style})
        #              self.note_qwidget_instance.refresh_display()


class StylingDialog(QDialog):
    def __init__(self, note_id: int, initial_style: dict, target_widget_interface, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Style Note ID: {note_id}")
        self.note_id = note_id
        self.target_widget = target_widget_interface # Interface to update the actual NoteWidget

        self.initial_style = initial_style.copy() # Store style at dialog opening for Cancel
        self.current_preview_style = initial_style.copy() # For real-time updates

        self._init_ui()
        self._load_initial_style()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)

        # Transparency
        self.layout.addWidget(QLabel("Transparency (0% = Opaque, 100% = Invisible):"))
        self.transparency_slider = QSlider(Qt.Orientation.Horizontal)
        self.transparency_slider.setRange(0, 100) # Representing 0.0 to 1.0 (inverted: 0 is opaque)
        self.transparency_slider.setToolTip("0% is fully opaque, 100% is fully transparent (invisible).")
        self.transparency_slider.valueChanged.connect(self._preview_transparency)
        self.layout.addWidget(self.transparency_slider)

        # Background Color
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("Background Color:"))
        self.bg_color_button = QPushButton("Choose Color")
        self.bg_color_button.clicked.connect(self._choose_bg_color)
        bg_layout.addWidget(self.bg_color_button)
        self.bg_color_preview = QLabel() # Shows the chosen color
        self.bg_color_preview.setFixedSize(50, 20)
        self.bg_color_preview.setAutoFillBackground(True)
        bg_layout.addWidget(self.bg_color_preview)
        self.layout.addLayout(bg_layout)

        # Margin
        margin_layout = QHBoxLayout()
        margin_layout.addWidget(QLabel("Margin (pixels):"))
        self.margin_spinbox = QSpinBox()
        self.margin_spinbox.setRange(0, 100) # Max margin 100px
        self.margin_spinbox.valueChanged.connect(self._preview_margin)
        # TODO: Add slider for margin as per spec? For now, spinbox is more precise.
        # self.margin_slider = QSlider(Qt.Orientation.Horizontal)
        # self.margin_slider.setRange(0,100)
        # self.margin_slider.valueChanged.connect(self.margin_spinbox.setValue)
        # self.margin_spinbox.valueChanged.connect(self.margin_slider.setValue)
        margin_layout.addWidget(self.margin_spinbox)
        self.layout.addLayout(margin_layout)

        # For testing the dialog standalone: show the mock widget
        if isinstance(self.target_widget, MockNoteWidgetForStyling):
            self.layout.addWidget(QLabel("Live Preview (Mock Widget):"))
            self.layout.addWidget(self.target_widget.widget_ref)


        # Ok and Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

    def _load_initial_style(self):
        # Transparency: Slider is 0 (opaque) to 100 (transparent). Style is 1.0 (opaque) to 0.0 (transparent)
        transparency_value = self.initial_style.get("transparency", 1.0)
        slider_value = int((1.0 - transparency_value) * 100)
        self.transparency_slider.setValue(slider_value)

        # Background Color
        bg_color_hex = self.initial_style.get("backgroundColor", "#FFFFFF")
        self._update_color_button_preview(QColor(bg_color_hex))

        # Margin
        margin_value = self.initial_style.get("margin", 5)
        self.margin_spinbox.setValue(margin_value)

    def _preview_transparency(self, slider_value: int):
        # Slider: 0 = opaque (1.0), 100 = transparent (0.0)
        transparency = 1.0 - (slider_value / 100.0)
        self.current_preview_style["transparency"] = transparency
        self.target_widget.update_style_preview("transparency", transparency)

    def _choose_bg_color(self):
        current_color = QColor(self.current_preview_style.get("backgroundColor", "#FFFFFF"))
        color = QColorDialog.getColor(current_color, self, "Select Background Color")
        if color.isValid():
            self.current_preview_style["backgroundColor"] = color.name() # #RRGGBB format
            self._update_color_button_preview(color)
            self.target_widget.update_style_preview("backgroundColor", color.name())

    def _update_color_button_preview(self, color: QColor):
        palette = self.bg_color_preview.palette()
        palette.setColor(QPalette.ColorRole.Window, color)
        self.bg_color_preview.setPalette(palette)

    def _preview_margin(self, value: int):
        self.current_preview_style["margin"] = value
        self.target_widget.update_style_preview("margin", value)

    def accept(self): # OK pressed
        # "Changes made ... are applied instantly ... Ok: Applies all current settings"
        # This implies the target_widget already reflects the previewed state.
        # So, we just need to ensure the database/final state is set to current_preview_style.
        self.target_widget.save_style(self.current_preview_style)
        super().accept()

    def reject(self): # Cancel pressed
        # Revert all styling changes made *during the current session*
        # back to what they were when the dialog was first opened.
        self.target_widget.revert_style(self.initial_style)
        super().reject()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Initial style for the mock widget
    mock_initial_style = {
        "transparency": 0.8, # 80% opaque
        "backgroundColor": "#E0FFFF", # Light cyan
        "margin": 10
    }

    # Create the mock widget that the dialog will control
    mock_widget_controller = MockNoteWidgetForStyling(note_id=1, initial_style=mock_initial_style)

    dialog = StylingDialog(
        note_id=1,
        initial_style=mock_widget_controller.get_current_style_for_dialog(),
        target_widget_interface=mock_widget_controller
    )

    # Show the mock widget itself (not part of dialog, but dialog updates it)
    # In real app, this would be the actual NoteWidget on desktop
    # For test, let's put it in a simple window
    test_host_window = QWidget()
    test_layout = QVBoxLayout(test_host_window)
    test_layout.addWidget(QLabel("This is the 'actual' Note Widget (Mocked for Test):"))
    test_layout.addWidget(mock_widget_controller.widget_ref) # Add the QWidget part of the mock
    test_host_window.setWindowTitle("Mock Note Widget Host")
    test_host_window.show()

    if dialog.exec(): # Show the dialog modally
        print("Styling Dialog accepted (OK).")
        print("Final style on mock widget:", mock_widget_controller.current_style)
    else:
        print("Styling Dialog rejected (Cancel).")
        print("Style on mock widget after cancel:", mock_widget_controller.current_style)
        # Verify it reverted to initial_style
        assert mock_widget_controller.current_style == mock_initial_style
        print("Style successfully reverted to initial state.")

    sys.exit(app.exec())
