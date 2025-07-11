# Desktop Notes - Specifications

## 1. Overview

Desktop Notes is a simple application for KDE Plasma 6 that allows users to display plain text (`.txt`) and Markdown (`.md`) files as read-only desktop widgets. Each widget, referred to as a "Note Widget," can display the content of one file.

## 2. Terminology

*   **Desktop Notes App:** The main application responsible for managing Note Widgets, their configurations, and overall application settings.
*   **Note Widget:** An individual, resizable, and movable widget instance on the desktop that displays the content of a single text or Markdown file.

## 3. Core Data Structure

Each Note Widget is represented by a data structure with the following properties. This data will be stored persistently.

```
note = {
  id: Integer, // Unique identifier for the note
  status: String, // "shown" or "hidden"
  filepath: String | null, // Absolute path to the .txt or .md file, or null if no file is selected
  position: { // Position of the top-left corner of the widget on the screen
    x: Integer, // x-coordinate
    y: Integer  // y-coordinate
  },
  size: { // Dimensions of the widget
    width: Integer,
    height: Integer
  },
  style: { // Visual styling of the widget
    transparency: Float, // 0.0 (fully transparent) to 1.0 (fully opaque)
    backgroundColor: String, // Hex color code (e.g., "#RRGGBB")
    margin: Integer // Uniform padding in pixels inside the widget, between the border and the text content
  }
}
```

## 4. Note Widget Creation

### 4.1. Initial Creation (Plasma System)

*   The primary way to create a new Note Widget is through Plasma's standard "Add Widgets" interface.
*   Users will find "Desktop Notes" (or the designated application name) in the widget list and add it to their desktop. Each addition creates a new Note Widget instance.

### 4.2. Alternative Creation (Context Menu)

*   Users can right-click on an existing Note Widget and select "Add New Note" from its context menu. This will also create a new Note Widget instance.

### 4.3. Placement of New Widgets

*   When a new Note Widget is created (especially via the "Add New Note" context menu option), it should be placed adjacent to the source/currently active widget (e.g., to the right or bottom if space allows) or in a cascading manner.
*   The goal is to avoid complete overlap with existing Note Widgets, ensuring the new widget is immediately visible and accessible. Exact placement logic can be refined, but it should not require manual repositioning for basic visibility.

### 4.4. Initial State of a New Widget

*   Upon creation, a new Note Widget:
    *   Has its `filepath` property set to `null`.
    *   Displays placeholder text, such as "Select File...", in a prominent font (e.g., 22pt).
    *   Does not automatically open any file selection dialog.
    *   Is ready for user interaction (e.g., right-click for context menu, or quick left-click to select a file).

## 5. Note Widget Interactions

### 5.1. Quick Left-click

*   **If `filepath` is `null` (widget is showing placeholder):** A single left-click anywhere on the Note Widget opens the standard Plasma "Select File" dialog.
*   **If `filepath` points to a file:** A single left-click executes a command to open the file in a text editor. Initially, this will be `konsole -e nvim $filepath` (or a similar default). This command should be configurable in the future.

### 5.2. Right-click Context Menu

Right-clicking on a Note Widget opens a context menu with the following items, in this order:

1.  `Select file`
2.  `Drag/Resize`
3.  `Styling`
4.  --- (Separator)
5.  `Add New Note`
6.  `Open Notes` (manages all notes)
7.  --- (Separator)
8.  `Hide` (hides this widget)
9.  `Delete` (deletes this widget's entry from the app)

## 6. Detailed Behavior of Context Menu Items

### 6.1. `Select file`

*   Opens the standard Plasma file selection dialog.
*   Users can:
    *   Navigate to and select an existing `.txt` or `.md` file.
    *   Type a new filename (and path) and confirm, which should create a new, empty file at that location.
*   If the user confirms a selection/creation ("Ok"):
    *   The Note Widget's `filepath` property is updated.
    *   The widget's content updates to display the (read-only) content of the selected/newly created file.
    *   If a new file was created, it will initially be empty.
*   If the user cancels the dialog: No changes are made to the Note Widget or its `filepath`.

### 6.2. `Drag/Resize` Mode

*   This menu item toggles a special mode for manipulating the widget's position and size.
*   **Activation:**
    *   Selecting "Drag/Resize" from the context menu enables the mode.
    *   A visual indication, such as a 3px yellow border, appears around the Note Widget.
    *   The mouse cursor changes when hovering over the widget:
        *   Over the main body: Changes to a "move" or "grab" cursor.
        *   Over corners and edges: Changes to appropriate resize cursors (e.g., diagonal arrows for corners, N-S/E-W arrows for edges).
*   **Performing Actions (in Drag/Resize mode):**
    *   **Dragging:** Left-click and hold on the main body (not corners/edges) of the widget and move the mouse to change its position. The `position` (x, y) data is updated.
    *   **Resizing:** Left-click and hold on a corner or an edge and move the mouse to change the widget's dimensions. The `size` (width, height) data is updated.
*   **Deactivation (Exiting Mode):**
    *   Clicking anywhere *outside* the Note Widget (e.g., on the desktop or another window) deactivates "Drag/Resize" mode.
    *   The visual indication (yellow border) disappears, and cursors return to normal.
    *   The "Drag/Resize" menu item does not need to be clicked again to exit.

### 6.3. `Styling`

*   Opens the "Styling Dialog" for the current Note Widget (see Section 7).

### 6.4. `Add New Note`

*   Creates a new Note Widget instance on the desktop, as described in Section 4.
*   The new widget will appear with the default initial state (placeholder text, no file selected).

### 6.5. `Open Notes`

*   Opens the "All Notes Management View" (see Section 8), which provides an overview and allows management of all notes (both shown and hidden).

### 6.6. `Hide`

*   Sets the `status` of the current Note Widget to "hidden".
*   The widget becomes invisible on the desktop.
*   Its data (filepath, style, etc.) is retained and can be managed via the "All Notes Management View".

### 6.7. `Delete`

*   Removes the record for the current Note Widget from the application's database (see Section 10).
*   The widget is removed from the desktop.
*   **Important:** This action *does not* delete the actual `.txt` or `.md` file from the filesystem if one was associated. It only removes the application's reference to it as a Note Widget.

## 7. Styling Dialog

The "Styling" dialog allows users to customize the appearance of an individual Note Widget.

*   **Controls:**
    *   **Transparency:** A slider to control the opacity of the widget's background (from fully transparent to fully opaque).
    *   **Background Color:** A color picker to choose the background color of the widget.
    *   **Margin:** A slider and a single numerical input field (for pixels) to set a uniform padding space between the widget's border and its text content.
*   **Real-time Preview:** Changes made to any styling control are applied *instantly* to the target Note Widget on the desktop, allowing the user to see the effect immediately without needing to click "Apply".
*   **Buttons:**
    *   **Ok:** Applies all current settings (which are already visually applied) and closes the dialog.
    *   **Cancel:** Reverts all styling changes made *during the current session of the dialog being open* back to what they were when the dialog was first opened. Then closes the dialog.

## 8. "Open Notes" Management View

This view provides a way to manage all Note Widgets, whether they are currently shown or hidden.

*   **Interface:** A separate window or dialog.
*   **Display:** Lists all notes known to the application in a table or list format.
*   **Columns:**
    *   `File Path`: Displays the `filepath` of the note (or a user-friendly name/placeholder if no file is set).
    *   `Status`: Displays "Shown" or "Hidden".
    *   (Optional) `Last Modified`: Displays the last modification date of the associated file.
*   **Sortable Columns:** Users can click on column headers to sort the list.
*   **Interaction:**
    *   Clicking on the "Status" cell (or a dedicated toggle) for a note flips its status between "Shown" and "Hidden".
        *   If changed to "Shown", the corresponding Note Widget appears on the desktop in its last known position/size/style.
        *   If changed to "Hidden", the corresponding Note Widget is removed from the desktop.

## 9. File Handling

*   The application supports displaying `.txt` (plain text) and `.md` (Markdown) files.
*   The display of content within the Note Widget is **read-only**. Editing is done via the external editor (see Section 5.1).
*   For Markdown files, basic rendering (e.g., bold, italics, headings, lists) is desirable, but complex features (scripts, embedded HTML) are not required initially.

## 10. Configuration and Data Storage

*   **Application Settings (Global):**
    *   Stored at: `~/.config/desktop-notes/settings.ini` (or equivalent standard location for Plasma app settings).
    *   This could store future global settings, like the default editor command.
*   **Note Widget Data (Database):**
    *   Stored at: `~/.local/share/desktop-notes/notes.db` (e.g., an SQLite database).
    *   This database will store a table of notes, with each row corresponding to a Note Widget and containing its `id`, `status`, `filepath`, `position`, `size`, and `style` information.
```
