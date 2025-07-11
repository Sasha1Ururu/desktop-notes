import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import org.kde.plasma.core 2.0 as PlasmaCore

Dialog {
    id: stylingDialog
    title: "Style Note"
    modal: true
    width: Math.min( (plasmoid && plasmoid.width * 0.8) || 400, 400)
    height: Qt.binding(function() { return contentLayout.implicitHeight + titleBar.implicitHeight + footer.implicitHeight + 20; }) // Adjust height dynamically
    standardButtons: Dialog.Ok | Dialog.Cancel
    parent: Overlay.overlay // Ensure it's on top

    property QtObject plasmoid // Reference to the main plasmoid Python object
    property string noteId // ID of the note being styled

    // Properties to hold initial values when dialog opens, for 'Cancel' functionality
    property color initialBackgroundColor
    property double initialTransparency
    property int initialMargin

    // Properties to bind to controls and reflect current editing state
    // These are not strictly necessary if stylePropertyChanged directly updates the plasmoid
    // but can be useful for intermediate state if dialog logic becomes complex.
    property color currentBackgroundColor
    property double currentTransparency
    property int currentMargin

    // Signal to the main plasmoid to apply style changes in real-time
    // Python side will connect to this.
    signal stylePropertyChanged(string noteId, string propertyName, var value)

    // This function will be called from Python to initialize and show the dialog
    function showDialog(targetNoteId, currentBgColor, currentTrans, currentMarg) {
        noteId = targetNoteId;

        initialBackgroundColor = Qt.color(currentBgColor); // Ensure it's a color object
        initialTransparency = currentTrans;
        initialMargin = currentMarg;

        // Set control values directly, which will also set current properties if bound
        colorPickerRect.color = initialBackgroundColor;
        transparencySlider.value = initialTransparency;
        marginSpinBox.value = currentMarg;

        // Update current values for internal tracking if needed
        currentBackgroundColor = initialBackgroundColor;
        currentTransparency = initialTransparency;
        currentMargin = initialMargin;

        stylingDialog.open();
    }

    // Need a reference to the title bar and footer to calculate height
    Item { id: titleBar }
    Item { id: footer }

    contentItem: ColumnLayout {
        id: contentLayout
        spacing: 15
        anchors.fill: parent
        anchors.margins: 10


        // Background Color
        RowLayout {
            Label { text: "Background Color:"; Layout.alignment: Qt.AlignVCenter }
            Rectangle {
                id: colorPickerRect
                width: 100; height: 28
                color: plasmoid ? Qt.color(plasmoid.backgroundColor.name) : Qt.rgba(0.2,0.2,0.2,1) // Initial from plasmoid
                border.color: "gray"
                radius: 3
                Layout.alignment: Qt.AlignVCenter

                Text { anchors.centerIn: parent; text: "Change"; color: Qt. kontrast(colorPickerRect.color, PlasmaCore.Theme.textColor, PlasmaCore.Theme.backgroundColor) }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        // Placeholder: Cycle through test colors
                        var testColors = [Qt.rgba(0.2,0.2,0.2,1), Qt.rgba(1,0,0,0.7), Qt.rgba(0,1,0,0.7), Qt.rgba(0,0,1,0.7), Qt.rgba(0.9,0.9,0.2,0.8), Qt.rgba(1,1,1,0.9)];
                        var currentColorString = colorPickerRect.color.toString();
                        var currentIndex = -1;
                        for(var i=0; i<testColors.length; ++i) {
                            if(testColors[i].toString() === currentColorString) {
                                currentIndex = i;
                                break;
                            }
                        }
                        var nextColor = testColors[(currentIndex + 1) % testColors.length];

                        colorPickerRect.color = nextColor; // Update visual
                        currentBackgroundColor = nextColor; // Update dialog's current property
                        stylePropertyChanged(noteId, "backgroundColor", currentBackgroundColor.name); // Emit hex string
                    }
                }
            }
        }

        // Transparency
        GridLayout {
            columns: 3
            Label { text: "Opacity:"; Layout.alignment: Qt.AlignVCenter }
            Slider {
                id: transparencySlider
                from: 0.0
                to: 1.0
                value: plasmoid ? plasmoid.transparency : 0.8 // Initial from plasmoid
                stepSize: 0.01
                Layout.fillWidth: true
                onValueChanged: {
                    currentTransparency = value;
                    stylePropertyChanged(noteId, "transparency", value);
                }
            }
            Label { text: transparencySlider.value.toFixed(2); Layout.minimumWidth: 30 }
        }

        // Margin
        GridLayout {
            columns: 3
            Label { text: "Margin (px):"; Layout.alignment: Qt.AlignVCenter }
            SpinBox {
                id: marginSpinBox
                from: 0
                to: 100
                value: plasmoid ? plasmoid.margin : 10 // Initial from plasmoid
                stepSize: 1
                Layout.fillWidth: true
                editable: true
                onValueChanged: {
                    currentMargin = value;
                    stylePropertyChanged(noteId, "margin", value);
                }
            }
            Label { text: marginSpinBox.value; Layout.minimumWidth: 30 }
        }
    }

    onAccepted: {
        // Ok clicked: Python side has already received real-time updates via
        // stylePropertyChanged signal. The plasmoid's properties are the source of truth.
        // The note data in DB should have been updated by the plasmoid's property setters.
        console.log("StylingDialog: Ok clicked for note " + noteId);
    }

    onRejected: {
        // Cancel clicked: Revert changes by applying initial values back to the plasmoid
        stylePropertyChanged(noteId, "backgroundColor", initialBackgroundColor.name); // use .name for hex
        stylePropertyChanged(noteId, "transparency", initialTransparency);
        stylePropertyChanged(noteId, "margin", initialMargin);
        console.log("StylingDialog: Cancel clicked for note " + noteId + ", changes reverted.");
    }
}
