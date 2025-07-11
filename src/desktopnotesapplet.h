#ifndef DESKTOPNOTESAPPLET_H
#define DESKTOPNOTESAPPLET_H

#include <Plasma/Applet>
#include <Plasma/Package>
#include <QObject>
#include <QString>

#include "data/notedata.h"
#include "data/databasemanager.h" // Include for direct use if needed, or rely on app logic

class QGraphicsLinearLayout;
class QTextEdit; // For displaying text/markdown
class QMenu;


class DesktopNotesApplet : public Plasma::Applet
{
    Q_OBJECT

public:
    DesktopNotesApplet(QObject *parent, const QVariantList &args);
    ~DesktopNotesApplet() override;

    void init() override;

    // Plasma::Applet overrides for persistence
    void readConfig() override; // Load state
    void writeConfig() override; // Save state

    // Method to get the note ID for this applet instance
    int noteId() const { return m_note.id; }


protected:
    // Optional: if you need to handle constraints changes
    // void constraintsEvent(Plasma::Constraints constraints) override;
    void mousePressEvent(QGraphicsSceneMouseEvent *event) override;
    void mouseMoveEvent(QGraphicsSceneMouseEvent *event) override;
    void mouseReleaseEvent(QGraphicsSceneMouseEvent *event) override;
    void hoverMoveEvent(QGraphicsSceneHoverEvent *event) override;

    // Context menu
    void createContextMenu(QMenu *menu) override;


private:
    DesktopNotesData::Note m_note; // Holds all data for this note instance

    QGraphicsLinearLayout *m_layout;
    QTextEdit *m_contentView; // To display file content or placeholder
    DesktopNotesData::DatabaseManager* m_dbManager; // Instance of the DB manager

    bool m_dragResizeMode = false; // Is the widget in drag/resize mode?
    QPointF m_dragStartPosition;   // For dragging the widget
    enum class ResizeHandle { None, TopLeft, Top, TopRight, Left, Right, BottomLeft, Bottom, BottomRight, Body };
    ResizeHandle m_currentResizeHandle = ResizeHandle::None;
    QRectF m_originalGeometryOnDragStart;


    void initializeNewNote(); // Sets up a new note in DB and gets ID
    void loadNoteData();      // Load m_note from DB using m_note.id
    void saveNoteData();      // Save m_note to DB
    void applyNoteStyle();    // Apply visual styling from m_note.style
    void setupUi();           // Setup initial UI elements (placeholder or file content)
    void updateContent();     // Update m_contentView based on m_note.filepath
    void updateCursors();     // Update cursor based on m_dragResizeMode and hover position
    ResizeHandle getResizeHandle(const QPointF& pos); // Determine which resize handle is at pos


public Q_SLOTS:
    // Slots for context menu actions, etc.
    void handleSelectFile();
    void handleDragResize();
    void handleStyling();
    void handleAddNewNote();
    void handleOpenNotes();
    void handleHide();
    void handleDelete();

    // Slot for quick left-click action
    void quickLeftClickAction();


private Q_SLOTS:
    // Internal slots if needed

};

// This macro is necessary to export the plugin.
// The name (desktopnotes) should match the KPluginMetaData file (or metadata.json)
// and what Plasma expects. For Plasma 6, this often uses reverse domain names.
// K_PLUGIN_FACTORY_WITH_JSON(DesktopNotesApplet, "plasma-applet-org-kde-desktopnotes.json", registerPlugin<DesktopNotesApplet>();)
// For Plasma 6, the metadata.json takes precedence and this macro might be simpler,
// or defined differently with K_PLUGIN_CLASS_WITH_JSON.
// Let's use the Plasma 6 recommended way if KPluginMetaData is involved.
// The actual JSON file needs to be created.

#endif // DESKTOPNOTESAPPLET_H
