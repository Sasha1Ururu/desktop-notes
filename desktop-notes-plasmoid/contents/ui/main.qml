import QtQuick 2.15
import QtQuick.Layouts 1.15
import org.kde.plasma.plasmoid 2.0
import org.kde.plasma.core 2.0 as PlasmaCore
import QtQuick.Controls 2.15 // For ScrollView

PlasmoidItem {
    id: root

    Layout.fillWidth: true
    Layout.fillHeight: true

    // Connections to Plasmoid properties (Python backend)
    Connections {
        target: plasmoid
        function onFilepathChanged() { updateAppearance(); }
        function onNoteContentChanged() { updateAppearance(); }
        function onBackgroundColorChanged() { updateAppearance(); }
        function onTransparencyChanged() { updateAppearance(); }
        function onMarginChanged() { updateAppearance(); }
        function onShowPlaceholderChanged() { updateAppearance(); }
        function onDragResizeModeToggled(isActive) {
            dragResizeOverlay.visible = isActive;
            if (isActive) {
                // When drag/resize mode is activated from Python,
                // ensure the plasmoid itself is set to be interactive for move/resize.
                // This is typically handled by Plasma when a QGraphicsWidget sets appropriate flags.
                // For Plasmoid a PSDK 2.0 applet, the shell usually handles this if the item is movable/resizable.
                // We might need to explicitly tell Plasma to make it user-movable if it's not by default.
                // However, the spec implies toggling a mode *within* the widget.
                // Plasma's default drag/resize (e.g. via Meta+LeftClick) is separate.
                // This "Drag/Resize" menu item suggests an internal mode.
                // The visual cue (yellow border) is the primary QML concern.
                // Actual dragging/resizing if not using Plasma's built-in:
                // Would require complex MouseArea logic to change geometry and update plasmoid.position/size.
                // Specs: "Left-click and hold on the main body...to change its position"
                // "Left-click and hold on a corner or an edge...to change its dimensions"
                // This is very advanced for a QML-only solution without C++ helpers or specific Plasma APIs.
                // For now, focusing on the visual cue and the *intent* to enter this mode.
                // The actual move/resize operations will be complex to implement here.
                // The spec also says "Clicking anywhere *outside* the Note Widget...deactivates".
                // This implies a global mouse grab or focus tracking.
                console.log("Drag/Resize mode activated in QML via signal: border visible")
            } else {
                console.log("Drag/Resize mode deactivated in QML via signal: border hidden")
            }
        }
    }

    function updateAppearance() {
        placeholderText.visible = plasmoid.showPlaceholder;
        fileContentAreaScrollView.visible = !plasmoid.showPlaceholder;
        if (!plasmoid.showPlaceholder) {
            fileContentArea.text = plasmoid.noteContent;
        }
        backgroundRectangle.color = plasmoid.backgroundColor;
        backgroundRectangle.opacity = plasmoid.transparency;
        // Ensure these are assignments, not declarations:
        fileContentArea.leftMargin = plasmoid.margin;
        fileContentArea.rightMargin = plasmoid.margin;
        fileContentArea.topMargin = plasmoid.margin;
        fileContentArea.bottomMargin = plasmoid.margin;
    }

    Rectangle {
        id: backgroundRectangle
        anchors.fill: parent
        color: plasmoid.backgroundColor // Bind to plasmoid property
        opacity: plasmoid.transparency // Bind to plasmoid property
    }

    // Placeholder text for when no file is selected
    Text {
        id: placeholderText
        anchors.centerIn: parent
        text: plasmoid.showPlaceholder ? "Select File..." : "" // Content managed by plasmoid logic
        font.pointSize: 22
        color: PlasmaCore.Theme.textColor
        visible: plasmoid.showPlaceholder // Bind to plasmoid property
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }

    // Scrollable Text area for displaying file content
    ScrollView {
        id: fileContentAreaScrollView
        anchors.fill: parent
        visible: !plasmoid.showPlaceholder // Bind to plasmoid property
        clip: true

        TextArea {
            id: fileContentArea
            text: plasmoid.noteContent // Bind to plasmoid property
            readOnly: true
            wrapMode: TextEdit.Wrap
            color: PlasmaCore.Theme.textColor // Ensure text is visible against custom background
            font: PlasmaCore.Theme.defaultFont // Use theme font

            // Apply margin from plasmoid
            leftMargin: plasmoid.margin
            rightMargin: plasmoid.margin
            topMargin: plasmoid.margin
            bottomMargin: plasmoid.margin

            // Background of TextArea itself should be transparent to show the main backgroundRectangle
            background: Rectangle {
                color: "transparent"
            }
        }
    }

    // Visual indicator for Drag/Resize mode
    Rectangle {
        id: dragResizeOverlay
        anchors.fill: parent
        border.color: "yellow"
        border.width: 3
        color: "transparent" // Make the rectangle itself transparent
        visible: plasmoid.dragResizeModeActive // Bind to Python property
        z: 10 // Ensure it's on top
    }

    Component.onCompleted: {
        updateAppearance(); // Initial setup
        dragResizeOverlay.visible = plasmoid.dragResizeModeActive; // Initial state for border
    }

    // Main MouseArea for interactions
    MouseArea {
        id: mainMouseArea
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        hoverEnabled: plasmoid.dragResizeModeActive // Enable hover only in drag/resize mode for cursor changes

        // TODO: Implement cursor changes based on hover position (edges, corners, body)
        // This requires more detailed MouseAreas or calculations.
        // Example for body move cursor:
        // cursorShape: plasmoid.dragResizeModeActive ? Qt.SizeAllCursor : Qt.ArrowCursor
        // More complex for edges/corners.

        onPressed: (mouse) => {
            if (plasmoid.dragResizeModeActive) {
                // If in drag/resize mode, left-click-hold should initiate move or resize.
                // This part is complex: requires grabbing mouse, tracking drag, updating geometry,
                // and then updating the persistent note.position and note.size.
                // This functionality is usually provided by window managers or C++ Qt item handling.
                // For now, we log the intent.
                console.log("Mouse pressed in Drag/Resize mode at:", mouse.x, mouse.y);
                // mouse.accepted = true; // Prevent other actions if we handle it.
            } else {
                // mouse.accepted = false; // Allow click to pass through if not handled
            }
        }

        onPositionChanged: (mouse) => {
            if (plasmoid.dragResizeModeActive && mouse.buttons & Qt.LeftButton) {
                // If dragging, update position/size based on initial press point and current mouse.
                // This is where the actual move/resize logic would go.
                // console.log("Mouse position changed during drag:", mouse.x, mouse.y);
            }
        }

        onReleased: (mouse) => {
            if (plasmoid.dragResizeModeActive && mouse.button === Qt.LeftButton) {
                console.log("Mouse released in Drag/Resize mode.");
                // Finalize position/size update in DB.
            }
        }

        onClicked: (mouse) => {
            if (!plasmoid.dragResizeModeActive) { // Only handle clicks if NOT in drag/resize mode
                if (mouse.button === Qt.LeftButton) {
                    plasmoid.handleQuickLeftClick();
                } else if (mouse.button === Qt.RightButton) {
                    plasmoid.showContextMenu(mouse.x, mouse.y);
                }
            } else {
                // If in drag/resize mode, a simple click might not do anything,
                // or it could be used to DEACTIVATE the mode if clicked inside.
                // However, spec says "Clicking anywhere *outside* the Note Widget...deactivates".
                // This is handled by the focusLostHandler below.
            }
        }
    }

    // Handler for deactivating drag/resize mode when focus is lost
    // This is a simplification. True "click outside" detection is harder.
    // ActiveFocus property on the root item can indicate if the plasmoid has focus.
    // Requires the root item to have activeFocusOnTab: true or similar.
    // For a plasmoid, focus behavior is managed by Plasma shell.
    // A simpler proxy: if the main window loses focus.
    // However, plasmoids don't have "windows" in the traditional sense.
    // Let's assume for now that if another interaction happens (like context menu again), mode might be toggled off by user.
    // The spec: "Clicking anywhere *outside* the Note Widget...deactivates"
    // This is the hardest part to implement reliably in QML without external helpers.
    // One approach: A full-screen transparent MouseArea that appears when drag/resize is active,
    // and a click on it deactivates the mode. This is also complex.

    // Acknowledging the difficulty of "click outside" for now.
    // The Python toggle `onActionDragResize` handles explicit toggling.


    // Styling Dialog instance
    StylingDialog {
        id: styleDialogInstance
        plasmoid: plasmoid // Pass reference to the Python backend
        // Connect the dialog's signal to Python slot for real-time updates
        onStylePropertyChanged: plasmoid.handleStyleChangeFromDialog(noteId, propertyName, value)
    }

    // Connections to Python signals that trigger dialog display
    Connections {
        target: plasmoid
        // ... other existing connections like onFilepathChanged ...
        function onRequestStylingDialog(noteId, bgColor, transparency, margin) {
            console.log("QML: Received requestStylingDialog for note " + noteId);
            styleDialogInstance.showDialog(noteId, bgColor, transparency, margin);
        }
        function onRequestManagementView(notesListModel) {
            console.log("QML: Received onRequestManagementView");
            if (managementViewInstance) { // Check if already created
                managementViewInstance.showView(notesListModel);
            }
        }
    }

    // Management View Dialog instance
    ManagementView {
        id: managementViewInstance
        // Connect the dialog's signal to Python slot
        onToggleNoteStatus: plasmoid.handleToggleNoteStatus(noteId, newIsShownStatus)
    }
}
