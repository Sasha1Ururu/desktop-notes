# Future Considerations for Desktop Notes

This document lists potential features and improvements that could be explored for future versions of the Desktop Notes application.

*   **Configurable Editor Command:** Allow users to specify their preferred command for opening files (currently defaults to `konsole -e nvim $filepath`) via a setting in the application.
*   **Advanced Non-Overlapping Placement:** Develop more sophisticated algorithms for placing new Note Widgets to better avoid overlap and find optimal screen locations.
*   **Markdown Rendering Options:** Allow users to choose between:
    *   Plain text display (current default for `.md` files).
    *   Basic Markdown rendering.
    *   Potentially richer Markdown rendering (though complex features like scripts or embedded HTML would likely remain out of scope).
*   **Search/Filter in "Open Notes" View:** Add functionality to search or filter the list of notes in the "All Notes Management View," which would be particularly useful for users with many notes.
*   **Reordering Notes in "Open Notes" View:** Allow users to manually reorder notes in the "All Notes Management View" if they prefer a custom sort order over column-based sorting.
*   **Import/Export of Notes Data:** Provide a mechanism to import and export the `notes.db` (or its content in a common format like CSV or JSON) for backup or migration purposes.
*   **System Tray Icon for Main App:** Include a system tray icon for the Desktop Notes App for:
    *   Quick access to "Open Notes" management view.
    *   A global "Add New Note" option.
    *   Application status indication or quick exit.
*   **More Granular Styling:**
    *   Font selection (family, size, color) for note content.
    *   Border styling (color, thickness, type).
*   **File Watching:** Optionally monitor associated files for external changes and automatically refresh the Note Widget content.
*   **Basic Synchronization:** (Very advanced) Explore options for syncing notes data across devices, though this significantly increases complexity.
*   **Templates for New Notes:** Allow users to define templates for quickly creating new notes with pre-filled content or structure.
