#include "desktopnotesapplet.h"
#include "config.h" // For PLASMOID_NAME and paths
#include "data/databasemanager.h" // For DatabaseManager
#include "data/notedata.h"      // For Note struct

#include <QStandardPaths>
#include <QDir>
#include <QPainter>
#include <QGraphicsSceneMouseEvent>
#include <QGraphicsProxyWidget> // To embed QWidgets like QTextEdit
#include <QApplication> // For QApplication::overrideCursor / restoreOverrideCursor
#include <QWindow> // For window()->setCursor()

#include <Plasma/Applet>
#include <Plasma/PackageStructure>
#include <Plasma/Svg>
#include <Plasma/Theme> // For colors, theming
#include <KWindowSystem> // For screen geometry if needed for placement
#include <KConfigGroup> // For applet config persistence
#include <KPluginFactory>
#include <KLocalizedString> // For i18n

// For UI elements
#include <QGraphicsLinearLayout>
#include <QTextEdit>

// For context menu
#include <QMenu>

// For file dialog
#include <KFileDialog>
#include <KIO/ спеціальні_файли> // For KUrl (KDE specific URL handling)
#include <QStandardPaths> // For creating empty file

// For running external command
#include <QProcess>
#include <QDebug>

#include "stylingdialog.h" // Added for Styling Dialog
#include "allnotesdialog.h"  // Added for All Notes Dialog


K_PLUGIN_FACTORY_WITH_JSON(DesktopNotesAppletFactory, "plasma-applet-org-kde-desktopnotes.json", registerPlugin<DesktopNotesApplet>();)

DesktopNotesApplet::DesktopNotesApplet(QObject *parent, const QVariantList &args)
    : Plasma::Applet(parent, args),
      m_layout(nullptr),
      m_contentView(nullptr),
      m_dbManager(DesktopNotesData::DatabaseManager::instance()) // Get DB Manager instance
{
    setAcceptedMouseButtons(Qt::LeftButton | Qt::RightButton); // Accept left and right clicks
    setHasConfigurationInterface(false); // We use context menu for all actions
    // setAcceptsHoverEvents(true); // Needed for cursor changes in drag/resize mode
}

DesktopNotesApplet::~DesktopNotesApplet()
{
    // m_dbManager is a singleton, not deleted here
}

void DesktopNotesApplet::init()
{
    // `readConfig()` will be called by Plasma to restore the noteId.
    // If m_note.id is still -1 after that, it's a new applet.
    if (!m_note.isValid()) {
        initializeNewNote();
    }

    // Ensure DB is open, though DatabaseManager::instance() tries this.
    if (!m_dbManager->openDb()) {
        qWarning() << "DesktopNotesApplet: Database could not be opened in init. Functionality may be limited.";
        // Display an error message on the widget itself?
    }

    loadNoteData(); // Load full note details from DB
    setupUi();      // Setup UI elements
    applyNoteStyle(); // Apply visual styles

    // If the note is meant to be hidden from a previous session, hide it now.
    if (m_note.status == QLatin1String("hidden")) {
        setVisible(false);
    }

    setAcceptsHoverEvents(true); // Enable hover events for cursor changes
}

// Plasma calls this to load saved configuration for the applet instance
void DesktopNotesApplet::readConfig()
{
    KConfigGroup cg = config(); // Get the KConfigGroup for this applet instance
    m_note.id = cg.readEntry("noteId", -1);
    // Position and size are typically handled by Plasma Shell and saved in its own config for the applet.
    // However, we store them in our DB to restore them if the applet is re-created or shown after being hidden.
    // Plasma::Applet::readConfig() might restore geometry if needed.
}

// Plasma calls this to save configuration for the applet instance
void DesktopNotesApplet::writeConfig()
{
    KConfigGroup cg = config();
    cg.writeEntry("noteId", m_note.id);
    // Plasma::Applet::writeConfig() handles geometry.
}


void DesktopNotesApplet::initializeNewNote()
{
    qInfo() << "Initializing a new note widget (applet instance created).";

    // Try to find a "pending_placement" note in the database
    QList<DesktopNotesData::Note> allNotes = m_dbManager->getAllNotes();
    DesktopNotesData::Note adoptableNote;
    bool foundPending = false;

    for (const auto& note : allNotes) {
        if (note.status == "pending_placement") {
            adoptableNote = note;
            foundPending = true;
            break; // Take the first one found (FIFO for pending notes)
        }
    }

    if (foundPending) {
        qInfo() << "Found 'pending_placement' note with ID:" << adoptableNote.id << ". Adopting it.";
        m_note = adoptableNote;
        m_note.status = "shown"; // Change status

        // Update the database with the new status and potentially adopted geometry
        if (m_dbManager->updateNote(m_note)) {
            qInfo() << "Adopted note ID" << m_note.id << "status updated to 'shown'.";
            // Apply its geometry
            setPreferredGeometry(QRect(m_note.position, m_note.size));
        } else {
            qWarning() << "Failed to update status for adopted note ID" << m_note.id << ". Proceeding with defaults.";
            // Fallback to creating a brand new note if update fails
            m_note = DesktopNotesData::Note(); // Reset
            int newId = m_dbManager->addNote(m_note);
            if (newId != -1) m_note.id = newId;
            else qWarning() << "Critical: Failed to create fallback new note in DB.";
        }
    } else {
        qInfo() << "No 'pending_placement' note found. Creating a brand new note entry.";
        m_note = DesktopNotesData::Note(); // Create a default note
        // Default position/size will be used. Plasma places it where user drops it.

        int newId = m_dbManager->addNote(m_note);
        if (newId != -1) {
            m_note.id = newId;
            // saveNoteData(); // m_note already has ID, addNote doesn't change its input object
        } else {
            qWarning() << "Failed to create new note in database for manually added widget.";
            if(m_contentView) m_contentView->setHtml("<div style='color: red;'>Error: Could not create note in database.</div>");
            // m_note remains invalid if DB fails
            return; // Early exit if note creation fails
        }
    }

    if (m_note.isValid()) {
        writeConfig();  // Persist the (adopted or new) noteId for this applet instance
        qInfo() << "Associated applet instance with note ID:" << m_note.id;
    } else {
        qWarning() << "initializeNewNote: m_note is invalid after initialization attempt.";
    }
}

void DesktopNotesApplet::loadNoteData()
{
    if (!m_note.isValid()) { // ID is -1 or invalid
        qWarning() << "loadNoteData: Invalid note ID, cannot load.";
        // This might happen if initialization failed. Show placeholder/error.
        if(m_contentView) updateContent(); // Show placeholder
        applyNoteStyle(); // Apply default style
        return;
    }

    DesktopNotesData::Note dbNote = m_dbManager->getNoteById(m_note.id);
    if (dbNote.isValid()) {
        m_note = dbNote; // Update our local copy with full data from DB
    } else {
        qWarning() << "loadNoteData: Note with ID" << m_note.id << "not found in DB. May have been deleted externally.";
        // This applet instance is now orphaned. It should probably be removed or reset.
        // For now, just show an error.
        if(m_contentView) m_contentView->setHtml(QString("<div style='color: red;'>Error: Note ID %1 not found.</div>").arg(m_note.id));
        m_note.filepath.clear(); // Clear filepath to prevent actions on a non-existent note
    }

    // Update UI based on loaded data
    if(m_contentView) updateContent();
    applyNoteStyle();

    // Restore geometry from m_note (position, size)
    // Plasma usually handles this, but we ensure our DB values are used, esp. for "Show" after "Hide".
    // This might conflict with Plasma's own geometry management if not careful.
    // A common pattern is to let Plasma manage active widgets, and we restore for newly shown ones.
    // setGeometry(QRect(m_note.position, m_note.size)); // This might be too aggressive.
    // Plasma::Applet::setPreferredGeometry(QRect(m_note.position, m_note.size));
}

void DesktopNotesApplet::saveNoteData()
{
    if (!m_note.isValid()) {
        qWarning() << "saveNoteData: Invalid note ID, cannot save.";
        return;
    }
    if (!m_dbManager->updateNote(m_note)) {
        qWarning() << "Failed to save note" << m_note.id << "to database.";
    }
}

void DesktopNotesApplet::applyNoteStyle()
{
    if (!m_contentView) return;

    // Background Color & Transparency
    QColor bgColor(m_note.style.backgroundColor);
    // For QGraphicsWidget, transparency is often handled by painting with alpha.
    // Or, if it's a window, setWindowOpacity. Plasma::Applet is a QGraphicsWidget.
    // We can set the background brush of the QTextEdit.
    QPalette p = m_contentView->palette();
    bgColor.setAlphaF(m_note.style.transparency);
    p.setColor(QPalette::Base, bgColor);
    m_contentView->setPalette(p);

    // To make the applet background itself transparent if QTextEdit doesn't fill it:
    // This requires painting. For now, assume QTextEdit fills.
    // Alternatively, if the applet has its own window:
    // if (nativeInterface() && nativeInterface()->window()) {
    //     nativeInterface()->window()->setOpacity(m_note.style.transparency);
    // }


    // Margin for QTextEdit
    m_contentView->document()->setDocumentMargin(m_note.style.margin);

    // Update the visual representation of the applet
    update(); // Schedules a repaint
}


void DesktopNotesApplet::setupUi()
{
    // Ensure layout exists
    if (!m_layout) {
        m_layout = new QGraphicsLinearLayout(Qt::Vertical, this);
        setLayout(m_layout);
    } else { // Clear if re-running (e.g. after some error)
        QGraphicsLayoutItem *item;
        while ((item = m_layout->takeAt(0)) != 0) {
            delete item->graphicsItem(); delete item;
        }
    }

    // Ensure content view exists
    if (!m_contentView) {
        m_contentView = new QTextEdit();
        m_contentView->setReadOnly(true);
        m_contentView->setFrameStyle(QFrame::NoFrame); // Cleaner look
        // Make QTextEdit background transparent initially so applet background shows,
        // or set its base color directly in applyNoteStyle.
        m_contentView->setStyleSheet("QTextEdit { background-color: transparent; border: none; }");


        QGraphicsProxyWidget *proxy = new QGraphicsProxyWidget(this);
        proxy->setWidget(m_contentView);
        m_layout->addItem(proxy);
    }

    updateContent(); // Display placeholder or file content
}

void DesktopNotesApplet::updateContent()
{
    if (!m_contentView) return;

    if (m_note.filepath.isEmpty()) {
        m_contentView->setHtml("<div style='font-size: 22pt; color: gray; text-align: center; vertical-align: middle;'>Select File...</div>");
    } else {
        QFile file(m_note.filepath);
        if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
            QTextStream in(&file);
            QString content = in.readAll();
            file.close();

            if (m_note.filepath.endsWith(".md", Qt::CaseInsensitive)) {
                m_contentView->setMarkdown(content);
            } else {
                m_contentView->setPlainText(content);
            }
        } else {
            m_contentView->setHtml(QString("<div style='color: red;'>Could not load file:<br>%1</div>").arg(m_note.filepath));
        }
    }
}

// --- Context Menu Actions ---
void DesktopNotesApplet::handleSelectFile()
{
    KUrl currentFileUrl;
    if (!m_note.filepath.isEmpty()) {
        currentFileUrl = KUrl::fromPath(m_note.filepath);
    } else {
        // Default to user's documents directory or home if no file is set
        currentFileUrl = KUrl::fromPath(QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation));
    }

    KFileDialog *dialog = new KFileDialog(currentFileUrl, i18n("Select Note File (.txt, .md) or Enter New Name"), nullptr);
    dialog->setMimeFilter({ "text/plain", "text/markdown" }, "text/plain"); // Default to .txt
    dialog->setOperationMode(KFileDialog::Saving); // Allows selecting existing or typing new
    dialog->setModal(true);


    if (dialog->exec() == QDialog::Accepted) {
        KUrl selectedUrl = dialog->selectedUrl();
        QString newFilepath = selectedUrl.toLocalFile();

        if (newFilepath.isEmpty()) {
            delete dialog;
            return;
        }

        // Ensure correct extension if user didn't provide one (optional, but good UX)
        if (!newFilepath.endsWith(".txt", Qt::CaseInsensitive) && !newFilepath.endsWith(".md", Qt::CaseInsensitive)) {
            if (dialog->selectedMimeType() == "text/markdown") {
                newFilepath += ".md";
            } else {
                newFilepath += ".txt";
            }
        }

        QFileInfo fileInfo(newFilepath);
        if (!fileInfo.exists()) {
            // File does not exist, create it (as per spec 6.1)
            QFile newFile(newFilepath);
            if (newFile.open(QIODevice::WriteOnly)) {
                newFile.close(); // Create empty file
                qInfo() << "Created new empty file:" << newFilepath;
            } else {
                qWarning() << "Could not create new file:" << newFilepath << newFile.errorString();
                // TODO: Show error to user
                delete dialog;
                return;
            }
        }

        m_note.filepath = newFilepath;
        updateContent();
        saveNoteData();
    }
    delete dialog;
}

void DesktopNotesApplet::handleDragResize()
{
    m_dragResizeMode = !m_dragResizeMode;
    if (m_dragResizeMode) {
        // Enter mode: show border, enable custom cursors
        // The spec asks for a 3px yellow border. This needs custom painting.
        setProperty("dragResizeActive", true); // For styling via QSS if possible, or manual paint
        setAcceptsHoverEvents(true); // Ensure hover events for cursor changes
    } else {
        // Exit mode: hide border, normal cursors
        setProperty("dragResizeActive", false);
        // setAcceptsHoverEvents(false); // Potentially disable if not needed otherwise
        QApplication::restoreOverrideCursor(); // Restore cursor if it was changed
        setCursor(Qt::ArrowCursor); // Reset to default for the applet
    }
    update(); // Trigger repaint for border
    updateCursors(); // Update cursor immediately
}

void DesktopNotesApplet::handleStyling()
{
    // TODO: Step 4 - Implement Styling Dialog
    // StylingDialog dialog(m_note, this); // Pass current note data
    // if (dialog.exec() == QDialog::Accepted) {
    //     m_note.style = dialog.getAppliedStyle();
    //     applyNoteStyle();
    //     saveNoteData();
    // } else { // Cancelled
    //     m_note.style = dialog.getOriginalStyle(); // Revert to style when dialog opened
    //     applyNoteStyle();
    // }
    // if (m_contentView) m_contentView->setPlainText("Styling dialog to be implemented.");
    // qDebug() << "Styling action triggered for note ID:" << m_note.id;

    if (!m_note.isValid()) {
        qWarning() << "Styling attempted on invalid note.";
        return;
    }

    StylingDialog dialog(m_note.style, this, static_cast<QWidget*>(parent())); // Pass applet's parent widget

    // The dialog's constructor stores the original style.
    // Changes in the dialog directly modify m_note.style via reference for real-time preview.
    // DesktopNotesApplet::applyNoteStyle() is called by the dialog during preview.

    if (dialog.exec() == QDialog::Accepted) {
        // OK was clicked. m_note.style already has the accepted changes.
        // Apply style one last time (might be redundant if preview is perfect) and save.
        applyNoteStyle();
        saveNoteData();
        qInfo() << "Styling changes applied for note ID:" << m_note.id;
    } else {
        // Cancel was clicked. Dialog's rejectDialog() should have reverted m_note.style
        // to its original state and called applyNoteStyle() for visual update.
        // No need to save, as it's reverted to the state before dialog was shown.
        qInfo() << "Styling changes cancelled for note ID:" << m_note.id;
    }
}

void DesktopNotesApplet::handleAddNewNote()
{
    // TODO: Step 6 - Main Application Logic / Service for creation
    // This is tricky for plasmoids. One way is to use KService to launch another instance.
    // Or, if running within a single process that manages multiple applets (less common for user-added applets):
    // Ask a central manager to create a new note (DB entry) and then somehow trigger Plasma
    // to add a new instance of this applet, configured with the new note's ID.
    // The `plasmapkg2 --add-widget org.kde.desktopnotes` command could be relevant if invokable.
    // For now, a placeholder:
    qInfo() << "Requesting 'Add New Note'. Source note ID:" << m_note.id;
    if (m_contentView) m_contentView->setPlainText("Add New Note to be implemented (requires inter-applet communication or service).");

    // Spec 4.3: "placed adjacent to the source/currently active widget"
    // This implies the current widget's geometry is known.
    // QRectF currentGeometry = geometry(); // This applet's geometry
    // DesktopNotesData::Note newNoteDefaults;
    // newNoteDefaults.position = QPoint(currentGeometry.right() + 10, currentGeometry.top()); // Example placement
    // int newNoteId = m_dbManager->addNote(newNoteDefaults);
    // Now, how to tell Plasma to create an applet for newNoteId at this position?
    // This usually involves the containment system or a scriptable interface to Plasma.

    DesktopNotesData::Note newNote; // Create a new default note object
    // Calculate adjacent position (Spec 4.3)
    QRectF currentGeometry = geometry(); // Geometry of this applet instance
    // Try to place to the right, then below, simple logic for now
    newNote.position.setX(currentGeometry.right() + 15); // 15px spacing
    newNote.position.setY(currentGeometry.top());

    // TODO: Check if this position is off-screen or overlaps too much with other screen elements.
    // Screen geometry:
    // QScreen *screen = KWindowSystem::currentScreen(nativeInterface() ? nativeInterface()->window() : nullptr);
    // if (screen) { QRect screenGeom = screen->geometry(); ... }


    int newNoteId = m_dbManager->addNote(newNote);
    if (newNoteId != -1) {
        qInfo() << "DesktopNotesApplet::handleAddNewNote: New note created in DB with ID:" << newNoteId
                << "at proposed position" << newNote.position;

        // THE CHALLENGE: How to make Plasma instantiate a new applet for this ID?
        // Option 1: User manually adds a new "Desktop Note" widget. The new widget's init()
        //           would need logic to pick up this newly created DB entry if it finds no ID in its own config.
        //           This could be done by finding a note in DB that isn't currently associated with an active noteId
        //           known to any existing applet instance (hard to coordinate without a central registry).
        //           Or, the newest note with default name/no filepath could be a candidate.

        // Option 2: Programmatic (requires Plasma scripting or specific DBus calls not always available/simple)
        // Example (conceptual, might not work directly or be ideal):
        // QProcess::startDetached("qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.loadPlasmoid \"org.kde.desktopnotes\"");
        // This would add a generic new one. We'd need it to then call readConfig(), find no noteId,
        // and then somehow identify itself as the one for `newNoteId`.
        // Perhaps the new applet could look for the most recent note in the DB that has a default state
        // and no corresponding entry in Plasma's config for any applet.

        // For now, we log and rely on the user adding a new widget, which will then initialize itself.
        // The `initializeNewNote()` in the new applet will create *another* new DB entry.
        // This isn't ideal for "Add New Note" which implies a specific new note.

        // A slightly better approach for the new applet's init:
        // If config() has no noteId, it could query DB for a note with a special status like "pending_instantiation",
        // claim it, update its status, and use its ID. `handleAddNewNote` would set this status.
        // Let's modify `initializeNewNote` and this method to reflect that.

        // So, `handleAddNewNote` will create a note with status "pending_placement"
        DesktopNotesData::Note pendingNote;
        pendingNote.position = newNote.position; // Use calculated position
        pendingNote.size = DesktopNotesData::Note().size; // Default size
        pendingNote.style = DesktopNotesData::NoteStyle(); // Default style
        pendingNote.status = "pending_placement"; // Special status

        int pendingNoteId = m_dbManager->addNote(pendingNote);
        if (pendingNoteId != -1) {
            qInfo() << "Created 'pending_placement' note in DB with ID:" << pendingNoteId
                    << "at position" << pendingNote.position;
            qInfo() << "User should now add a new 'Desktop Note' widget from Plasma's 'Add Widgets' menu.";
            qInfo() << "The new widget will look for a 'pending_placement' note and adopt it.";
            // Optionally, try to trigger "Add Widget" dialog:
            // QProcess::startDetached("plasma-add-widget org.kde.desktopnotes"); // Might not exist / work this way
        } else {
            qWarning() << "Failed to create 'pending_placement' note in DB.";
        }

    } else {
        qWarning() << "DesktopNotesApplet::handleAddNewNote: Failed to add new note to database initially.";
    }
}

void DesktopNotesApplet::handleOpenNotes()
{
    // TODO: Step 5 - Implement "Open Notes" Management View
    // AllNotesDialog dialog(this); // Parent to this applet or global window
    // dialog.exec();
    // if (m_contentView) m_contentView->setPlainText("Open Notes Management View to be implemented.");
    // qDebug() << "Open Notes action triggered.";

    // Ensure it's not creating multiple instances if one is already open (modeless case)
    // For a modal dialog (exec), this is less of an issue.
    // For now, assume one instance at a time is fine.
    AllNotesDialog *dialog = new AllNotesDialog(static_cast<QWidget*>(parent())); // Parent to applet's window context
    dialog->setAttribute(Qt::WA_DeleteOnClose); // Important for modeless, good for modal too
    dialog->exec(); // Modal execution
    // For modeless: dialog->show();
}

void DesktopNotesApplet::handleHide()
{
    if (!m_note.isValid()) return;
    m_note.status = "hidden";
    saveNoteData();
    setVisible(false); // Hide the plasmoid
    qInfo() << "Note ID" << m_note.id << "hidden.";
}

void DesktopNotesApplet::handleDelete()
{
    if (!m_note.isValid()) return;

    // Ask for confirmation? (Good UX, but not in spec explicitly for this menu item)
    // QMessageBox::StandardButton reply;
    // reply = QMessageBox::question(nullptr, i18n("Delete Note"),
    //                               i18n("Are you sure you want to delete this note widget?\n(The file '%1' will not be deleted.)", m_note.filepath),
    //                               QMessageBox::Yes|QMessageBox::No);
    // if (reply == QMessageBox::No) {
    //     return;
    // }

    int noteIdToDelete = m_note.id;
    m_dbManager->deleteNoteById(noteIdToDelete);

    // Make the applet remove itself.
    // This typically involves telling its containment.
    // Plasma::Applet has a remove() slot/method.
    // Calling remove() should make Plasma delete this applet instance and its config.
    remove();
    qInfo() << "Note ID" << noteIdToDelete << "deleted from DB and applet removal requested.";
}

// --- Quick Left-click Action ---
void DesktopNotesApplet::quickLeftClickAction()
{
    if (m_dragResizeMode) {
        // If in drag/resize mode, a click outside (on desktop) should deactivate it.
        // A click *inside* might be part of a drag/resize op, handled by mouseMove.
        // For now, assume any left click inside while in mode doesn't trigger file ops.
        return;
    }

    if (m_note.filepath.isEmpty()) {
        handleSelectFile(); // Open file selection dialog
    } else {
        // Open file in editor (Spec 5.1)
        // TODO: Make command configurable (future, from settings.ini)
        QString editorCommand = QString("konsole -e nvim %1").arg(m_note.filepath); // Default
        // KConfigGroup globalSettings(KSharedConfig::openConfig("desktop-notesrc"), "General");
        // editorCommand = globalSettings.readEntry("EditorCommand", editorCommand);
        // editorCommand = editorCommand.replace("%f", m_note.filepath);

        qInfo() << "Executing editor command:" << editorCommand;
        bool success = QProcess::startDetached(editorCommand);
        if (!success) {
            qWarning() << "Failed to start editor process for command:" << editorCommand;
            // TODO: Show error to user? (e.g. small popup or notification)
        }
    }
}


// --- Mouse Events for Drag/Resize Mode ---
void DesktopNotesApplet::mousePressEvent(QGraphicsSceneMouseEvent *event)
{
    if (m_dragResizeMode && event->button() == Qt::LeftButton) {
        m_currentResizeHandle = getResizeHandle(event->pos());
        if (m_currentResizeHandle != ResizeHandle::None) {
            m_dragStartPosition = event->screenPos(); // Use screenPos for global movement
            m_originalGeometryOnDragStart = geometry(); // Current geometry of the applet
            event->accept();
            return;
        }
    } else if (event->button() == Qt::LeftButton) {
        // Not in drag/resize mode, or clicked outside handles.
        // This is for the quick left-click action.
        quickLeftClickAction();
        event->accept();
        return;
    }
    // For other buttons (e.g., RightButton for context menu), pass to base class.
    Plasma::Applet::mousePressEvent(event);
}

void DesktopNotesApplet::mouseMoveEvent(QGraphicsSceneMouseEvent *event)
{
    if (m_dragResizeMode && (event->buttons() & Qt::LeftButton)) {
        if (m_currentResizeHandle == ResizeHandle::None) {
            Plasma::Applet::mouseMoveEvent(event);
            return;
        }

        QPointF delta = event->screenPos() - m_dragStartPosition;
        QRectF newGeometry = m_originalGeometryOnDragStart;

        if (m_currentResizeHandle == ResizeHandle::Body) {
            newGeometry.translate(delta);
        } else {
            // Resizing logic (simplified, more robust logic needed for aspect ratio, min/max size)
            if (m_currentResizeHandle == ResizeHandle::TopLeft || m_currentResizeHandle == ResizeHandle::Left || m_currentResizeHandle == ResizeHandle::BottomLeft) {
                newGeometry.setLeft(m_originalGeometryOnDragStart.left() + delta.x());
            }
            if (m_currentResizeHandle == ResizeHandle::TopLeft || m_currentResizeHandle == ResizeHandle::Top || m_currentResizeHandle == ResizeHandle::TopRight) {
                newGeometry.setTop(m_originalGeometryOnDragStart.top() + delta.y());
            }
            if (m_currentResizeHandle == ResizeHandle::TopRight || m_currentResizeHandle == ResizeHandle::Right || m_currentResizeHandle == ResizeHandle::BottomRight) {
                newGeometry.setRight(m_originalGeometryOnDragStart.right() + delta.x());
            }
            if (m_currentResizeHandle == ResizeHandle::BottomLeft || m_currentResizeHandle == ResizeHandle::Bottom || m_currentResizeHandle == ResizeHandle::BottomRight) {
                newGeometry.setBottom(m_originalGeometryOnDragStart.bottom() + delta.y());
            }

            // Ensure minimum size
            if (newGeometry.width() < 50) newGeometry.setWidth(50);
            if (newGeometry.height() < 30) newGeometry.setHeight(30);
        }

        // Request Plasma to set the new geometry.
        // This interacts with Plasma's own window management for applets.
        // For freely placed desktop widgets (like notes often are), this should work.
        setPreferredGeometry(newGeometry);
        event->accept();
        return;

    } else if (m_dragResizeMode) { // Hovering in drag/resize mode
        updateCursors(event->pos());
    }
    Plasma::Applet::mouseMoveEvent(event);
}

void DesktopNotesApplet::mouseReleaseEvent(QGraphicsSceneMouseEvent *event)
{
    if (m_dragResizeMode && event->button() == Qt::LeftButton && m_currentResizeHandle != ResizeHandle::None) {
        // Update m_note with new position and size from geometry()
        m_note.position = geometry().topLeft().toPoint(); // QRectF to QPoint
        m_note.size = geometry().size().toSize();     // QSizeF to QSize
        saveNoteData();

        m_currentResizeHandle = ResizeHandle::None;
        updateCursors(event->pos()); // Update cursor based on new state
        event->accept();
        return;
    }
    // Spec 6.2: Clicking *outside* deactivates. Plasma handles this by focus change.
    // We might need to connect to focusOutEvent if this isn't automatic enough.
    Plasma::Applet::mouseReleaseEvent(event);
}

void DesktopNotesApplet::hoverMoveEvent(QGraphicsSceneHoverEvent *event)
{
    if (m_dragResizeMode) {
        updateCursors(event->pos());
        event->accept();
        return;
    }
    Plasma::Applet::hoverMoveEvent(event);
}

DesktopNotesApplet::ResizeHandle DesktopNotesApplet::getResizeHandle(const QPointF& pos) {
    if (!m_dragResizeMode) return ResizeHandle::None;

    const int margin = 10; // Sensitivity margin for resize handles
    QRectF currentGeom = rect(); // Applet's local coordinate rect

    // Check corners
    if (QRectF(currentGeom.topLeft(), QSizeF(margin, margin)).contains(pos)) return ResizeHandle::TopLeft;
    if (QRectF(currentGeom.topRight() - QPointF(margin, 0), QSizeF(margin, margin)).contains(pos)) return ResizeHandle::TopRight;
    if (QRectF(currentGeom.bottomLeft() - QPointF(0, margin), QSizeF(margin, margin)).contains(pos)) return ResizeHandle::BottomLeft;
    if (QRectF(currentGeom.bottomRight() - QPointF(margin, margin), QSizeF(margin, margin)).contains(pos)) return ResizeHandle::BottomRight;

    // Check edges
    if (QRectF(currentGeom.left(), currentGeom.top() + margin, margin, currentGeom.height() - 2 * margin).contains(pos)) return ResizeHandle::Left;
    if (QRectF(currentGeom.right() - margin, currentGeom.top() + margin, margin, currentGeom.height() - 2 * margin).contains(pos)) return ResizeHandle::Right;
    if (QRectF(currentGeom.left() + margin, currentGeom.top(), currentGeom.width() - 2 * margin, margin).contains(pos)) return ResizeHandle::Top;
    if (QRectF(currentGeom.left() + margin, currentGeom.bottom() - margin, currentGeom.width() - 2 * margin, margin).contains(pos)) return ResizeHandle::Bottom;

    // If not on border/corner, it's the body for moving
    if (currentGeom.adjusted(margin, margin, -margin, -margin).contains(pos)) return ResizeHandle::Body; // Check body last

    return ResizeHandle::None;
}


void DesktopNotesApplet::updateCursors(const QPointF& mousePos) {
    if (!m_dragResizeMode) {
        if (QApplication::overrideCursor()) { // Check if we set an override
             QApplication::restoreOverrideCursor();
        }
        setCursor(Qt::ArrowCursor); // Default cursor when not in mode
        return;
    }

    ResizeHandle handle = getResizeHandle(mousePos);
    Qt::CursorShape shape = Qt::ArrowCursor; // Default to arrow

    switch (handle) {
        case ResizeHandle::Body:        shape = Qt::SizeAllCursor; break; // Or OpenHandCursor -> ClosedHandCursor on press
        case ResizeHandle::TopLeft:     shape = Qt::SizeFDiagCursor; break;
        case ResizeHandle::TopRight:    shape = Qt::SizeBDiagCursor; break;
        case ResizeHandle::BottomLeft:  shape = Qt::SizeBDiagCursor; break;
        case ResizeHandle::BottomRight: shape = Qt::SizeFDiagCursor; break;
        case ResizeHandle::Top:         shape = Qt::SizeVerCursor; break;
        case ResizeHandle::Bottom:      shape = Qt::SizeVerCursor; break;
        case ResizeHandle::Left:        shape = Qt::SizeHorCursor; break;
        case ResizeHandle::Right:       shape = Qt::SizeHorCursor; break;
        case ResizeHandle::None:        shape = Qt::ArrowCursor; break; // Cursor if outside active area but still in mode
    }

    // Using QApplication::setOverrideCursor might be too global.
    // For QGraphicsWidget, setting its own cursor property is usually better.
    setCursor(shape);
}


// --- Paint event for custom border in Drag/Resize mode ---
void DesktopNotesApplet::paint(QPainter *painter, const QStyleOptionGraphicsItem *option, QWidget *widget)
{
    Plasma::Applet::paint(painter, option, widget); // Call base class paint

    if (m_dragResizeMode) {
        painter->save();
        QPen pen(Qt::yellow, 3, Qt::SolidLine);
        painter->setPen(pen);
        // Draw border slightly inside to not be clipped, or ensure clipping is off for this
        painter->drawRect(rect().adjusted(1.5, 1.5, -1.5, -1.5)); // Adjust by half pen width
        painter->restore();
    }
}


// --- Context Menu Creation ---
void DesktopNotesApplet::createContextMenu(QMenu *menu)
{
    menu->clear(); // Clear any default actions Plasma might add if we want full control here

    menu->addAction(i18n("Select file..."), this, &DesktopNotesApplet::handleSelectFile);

    QAction* dragResizeAction = menu->addAction(m_dragResizeMode ? i18n("Exit Drag/Resize Mode") : i18n("Drag/Resize"), this, &DesktopNotesApplet::handleDragResize);
    dragResizeAction->setCheckable(true);
    dragResizeAction->setChecked(m_dragResizeMode);

    menu->addAction(i18n("Styling..."), this, &DesktopNotesApplet::handleStyling);
    menu->addSeparator();
    menu->addAction(i18n("Add New Note"), this, &DesktopNotesApplet::handleAddNewNote);
    menu->addAction(i18n("Open Notes..."), this, &DesktopNotesApplet::handleOpenNotes);
    menu->addSeparator();
    menu->addAction(i18n("Hide"), this, &DesktopNotesApplet::handleHide);
    menu->addAction(i18n("Delete"), this, &DesktopNotesApplet::handleDelete);

    // Add Plasma's default actions if desired (e.g., "Configure", "Remove")
    // Plasma::Applet::createContextMenu(menu); // This might add its own "Remove" etc.
    // For full control as per spec, we define all. Plasma might still add its own "Remove"
    // if this applet is part of a panel. For desktop widgets, it's usually less.
}
