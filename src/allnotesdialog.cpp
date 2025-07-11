#include "allnotesdialog.h"
#include "data/databasemanager.h" // For direct DB access and Note struct
#include "desktopnotesapplet.h" // Potentially for signaling to show/hide

#include <QTableView>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QMessageBox> // For error messages or confirmations
#include <QDebug>
#include <KWindowSystem> // For notifying Plasma to show/hide specific applets (complex part)
#include <Plasma/Applet> // For context

// --- NotesTableModel Implementation ---

NotesTableModel::NotesTableModel(QObject *parent)
    : QAbstractTableModel(parent),
      m_dbManager(DesktopNotesData::DatabaseManager::instance())
{
    loadNotes();
}

int NotesTableModel::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid())
        return 0;
    return m_notes.count();
}

int NotesTableModel::columnCount(const QModelIndex &parent) const
{
    if (parent.isValid())
        return 0;
    return 2; // File Path, Status
}

QVariant NotesTableModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() >= m_notes.count())
        return QVariant();

    const DesktopNotesData::Note &note = m_notes.at(index.row());

    if (role == Qt::DisplayRole || role == Qt::EditRole) {
        switch (index.column()) {
            case 0: // File Path
                return note.filepath.isEmpty() ? i18n("<No file selected>") : note.filepath;
            case 1: // Status
                return note.status; // "shown" or "hidden"
            default:
                return QVariant();
        }
    }
    return QVariant();
}

QVariant NotesTableModel::headerData(int section, Qt::Orientation orientation, int role) const
{
    if (role != Qt::DisplayRole)
        return QVariant();

    if (orientation == Qt::Horizontal) {
        switch (section) {
            case 0: return i18n("File Path");
            case 1: return i18n("Status");
            default: return QVariant();
        }
    }
    return QVariant(); // Vertical header (row numbers)
}

bool NotesTableModel::setData(const QModelIndex &index, const QVariant &value, int role)
{
    if (!index.isValid() || role != Qt::EditRole || index.row() >= m_notes.count())
        return false;

    DesktopNotesData::Note &note = m_notes[index.row()]; // Get reference to modify
    bool changed = false;

    if (index.column() == 1) { // Status column
        QString newStatus = value.toString();
        if (note.status != newStatus && (newStatus == "shown" || newStatus == "hidden")) {
            note.status = newStatus;
            if (m_dbManager->setNoteStatus(note.id, newStatus)) {
                changed = true;
                // TODO: Critical part - Signal Plasma to show/hide the actual widget.
                // This is complex. It might involve DBus calls to plasmashell or
                // finding the specific Applet instance if this dialog is running in the same process
                // (unlikely if applets are separate).
                // For now, we just update DB and model.
                qDebug() << "Note ID" << note.id << "status changed to" << newStatus << "in DB. UI update for applet TBD.";

                // If we could find the applet instance:
                // DesktopNotesApplet* applet = findAppletById(note.id);
                // if (applet) {
                //    applet->setVisible(newStatus == "shown");
                //    if (newStatus == "shown") applet->loadNoteData(); // Ensure it's up-to-date
                // }
            } else {
                qWarning() << "Failed to update status in DB for note ID" << note.id;
                // Revert local change if DB update failed
                // note.status = (newStatus == "shown" ? "hidden" : "shown");
                return false;
            }
        }
    }

    if (changed) {
        emit dataChanged(index, index, {Qt::DisplayRole, Qt::EditRole});
        return true;
    }
    return false;
}

Qt::ItemFlags NotesTableModel::flags(const QModelIndex &index) const
{
    Qt::ItemFlags defaultFlags = QAbstractTableModel::flags(index);
    if (index.isValid() && index.column() == 1) { // Status column is editable (by toggle)
        return defaultFlags | Qt::ItemIsEditable;
    }
    return defaultFlags;
}

void NotesTableModel::loadNotes()
{
    beginResetModel();
    m_notes = m_dbManager->getAllNotes();
    endResetModel();
}

DesktopNotesData::Note NotesTableModel::getNoteAt(int row) const
{
    if (row >= 0 && row < m_notes.count()) {
        return m_notes.at(row);
    }
    return DesktopNotesData::Note(); // Invalid note
}


// --- AllNotesDialog Implementation ---

AllNotesDialog::AllNotesDialog(QWidget *parent)
    : QDialog(parent),
      m_dbManager(DesktopNotesData::DatabaseManager::instance())
{
    setWindowTitle(i18n("Manage All Notes"));
    setMinimumSize(600, 400);
    setupUi();

    connect(m_refreshButton, &QPushButton::clicked, this, &AllNotesDialog::onRefreshClicked);
    connect(m_closeButton, &QPushButton::clicked, this, &AllNotesDialog::accept); // accept() closes dialog
    connect(m_tableView, &QAbstractItemView::doubleClicked, this, &AllNotesDialog::onTableDoubleClicked);

    m_tableModel->loadNotes(); // Initial load
}

AllNotesDialog::~AllNotesDialog()
{
    // Qt handles child widget deletion (m_tableModel if parented, etc.)
}

void AllNotesDialog::setupUi()
{
    QVBoxLayout *mainLayout = new QVBoxLayout(this);

    m_tableView = new QTableView();
    m_tableModel = new NotesTableModel(this); // Parented to dialog
    m_tableView->setModel(m_tableModel);
    m_tableView->setSelectionBehavior(QAbstractItemView::SelectRows);
    m_tableView->setSelectionMode(QAbstractItemView::SingleSelection);
    m_tableView->setAlternatingRowColors(true);
    m_tableView->horizontalHeader()->setStretchLastSection(true);
    m_tableView->setSortingEnabled(true); // Enable column sorting
    // m_tableView->sortByColumn(0, Qt::AscendingOrder); // Default sort

    // Resize columns to content or set fixed sizes
    m_tableView->horizontalHeader()->setSectionResizeMode(0, QHeaderView::Stretch);
    m_tableView->horizontalHeader()->setSectionResizeMode(1, QHeaderView::ResizeToContents);


    mainLayout->addWidget(m_tableView);

    QHBoxLayout *buttonLayout = new QHBoxLayout();
    m_refreshButton = new QPushButton(i18n("Refresh List"));
    m_closeButton = new QPushButton(i18n("Close"));
    buttonLayout->addWidget(m_refreshButton);
    buttonLayout->addStretch();
    buttonLayout->addWidget(m_closeButton);

    mainLayout->addLayout(buttonLayout);
    setLayout(mainLayout);
}

void AllNotesDialog::onRefreshClicked()
{
    m_tableModel->loadNotes();
}

void AllNotesDialog::onTableDoubleClicked(const QModelIndex &index)
{
    if (!index.isValid() || index.column() != 1) // Only on status column
        return;

    DesktopNotesData::Note note = m_tableModel->getNoteAt(index.row());
    if (!note.isValid()) return;

    QString currentStatus = note.status;
    QString newStatus = (currentStatus == "shown" ? "hidden" : "shown");

    // Attempt to set data in model, which handles DB update and should signal Plasma (TBD)
    if (m_tableModel->setData(index, newStatus, Qt::EditRole)) {
        qDebug() << "Toggled status for note ID" << note.id << "to" << newStatus;
        // The setData implementation needs to trigger the actual show/hide of the plasmoid.
        // This is the most complex part of this dialog.
        // For now, it only updates the DB and the table view.
        // Actual plasmoid visibility change is NOT yet implemented here.
        // A possible mechanism:
        // KWindowSystem:: μέσω D-Bus send a signal or call a method on a known service
        // provided by the plasmoid or a manager, passing note.id and newStatus.
        // Example placeholder:
        // SomePlasmaInterface::setNoteVisibility(note.id, (newStatus == "shown"));
    } else {
        QMessageBox::warning(this, i18n("Error"), i18n("Could not update status for note %1.", note.filepath));
    }
}
