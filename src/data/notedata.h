#ifndef NOTEDATA_H
#define NOTEDATA_H

#include <QString>
#include <QPoint>
#include <QSize>
#include <QColor> // For QColor representation of hex string

// Using a namespace to group data-related structures
namespace DesktopNotesData {

struct NoteStyle {
    double transparency = 1.0; // 0.0 (transparent) to 1.0 (opaque)
    QString backgroundColor = "#FFFFE0"; // Default: light yellow
    int margin = 10; // Default margin in pixels

    NoteStyle() = default;
};

struct Note {
    int id = -1; // -1 indicates an unsaved/invalid note
    QString status = "shown"; // "shown" or "hidden"
    QString filepath; // Absolute path, can be null/empty
    QPoint position = QPoint(50, 50); // Default position
    QSize size = QSize(200, 150); // Default size
    NoteStyle style;

    bool isValid() const { return id != -1; }

    Note() = default;
};

} // namespace DesktopNotesData

#endif // NOTEDATA_H
