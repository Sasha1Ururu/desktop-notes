import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import org.kde.plasma.core 2.0 as PlasmaCore

Dialog { // Using Dialog for a separate window behavior
    id: managementViewDialog
    title: "Manage All Notes"
    modal: false // Allow interaction with other windows/desktop
    width: 600
    height: 400
    standardButtons: Dialog.Close // Just a close button

    // Property to hold the list of all notes (will be a ListModel from Python)
    // Each item in model: { note_id_prop, filepath_prop, status_prop, last_modified_prop (optional) }
    property var notesModel: null

    // Signal to Python when a note's status needs to be toggled
    signal toggleNoteStatus(string noteId, bool newIsShownStatus)

    function showView(modelFromPython) {
        notesModel = modelFromPython;
        managementViewDialog.open();
    }

    contentItem: ColumnLayout {
        anchors.fill: parent
        spacing: 5

        Label {
            text: "All configured notes. Click status to toggle visibility."
            font.italic: true
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
        }

        TableView {
            id: notesTableView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            model: notesModel

            delegate: Rectangle { // Custom delegate for richer interaction if needed
                implicitWidth: notesTableView.columnWidthProvider(column)
                implicitHeight: 35
                color: model.status_prop === "shown" ? PlasmaCore.Theme.highlightColor : "transparent"
                border.color: PlasmaCore.Theme.borderColor
                border.width: 1

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 5
                    anchors.rightMargin: 5

                    Text {
                        text: display // Provided by model role
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                        color: PlasmaCore.Theme.textColor
                        Layout.fillWidth: true
                        Layout.preferredWidth: notesTableView.columnWidthProvider(column)

                        MouseArea { // To make the cell clickable, especially for status
                            anchors.fill: parent
                            onClicked: {
                                if (column === 1) { // Assuming 'Status' is the second column (index 1)
                                    var newStatus = model.status_prop === "shown" ? false : true;
                                    toggleNoteStatus(model.note_id_prop, newStatus);
                                }
                            }
                        }
                    }
                }
            }

            VerticalHeaderView { Sync Delegate { sectionSize: 35 } } // Fixed row height

            TableViewColumn {
                role: "filepath_prop" // Role name from the ListModel
                title: "File Path / Name"
                width: 300
                resizable: true
            }
            TableViewColumn {
                role: "status_prop" // Role name from the ListModel
                title: "Status (Click to toggle)"
                width: 150
                resizable: true
                // Delegate item here could be a CheckBox or a more explicit toggle button
                // For now, using the RowLayout's MouseArea on the text.
            }
            TableViewColumn {
                role: "last_modified_prop"
                title: "Last Modified"
                width: 150
                resizable: true
                // visible: notesModel && notesModel.rowCount > 0 && notesModel.get(0).last_modified_prop !== undefined
            }
        }
    }

    onRejected: { // Handles Dialog.Close button
        console.log("ManagementView: Closed");
    }

    Component.onCompleted: {
        // Example: how Python might set the model
        // var exampleData = [
        //     { note_id_prop: "id1", filepath_prop: "/path/to/file1.txt", status_prop: "shown", last_modified_prop: "2023-01-01" },
        //     { note_id_prop: "id2", filepath_prop: "Another Note (no file)", status_prop: "hidden", last_modified_prop: "2023-01-02" }
        // ];
        // var listModel = Qt.createQmlObject("import QtQuick 2.0; ListModel {}", notesTableView);
        // exampleData.forEach(item => listModel.append(item));
        // notesModel = listModel;
        // console.log("ManagementView: Example model applied if no external model given.");
    }
}
