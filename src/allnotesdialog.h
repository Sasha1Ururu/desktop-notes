#ifndef ALLNOTESDIALOG_H
#define ALLNOTESDIALOG_H

#include <QDialog>
#include <QAbstractTableModel>
#include <QList>
#include "data/notedata.h" // For Note struct

// Forward declarations
class QTableView;
class QPushButton;
class DesktopNotesData::DatabaseManager; // Forward declare for DB access

// --- NotesTableModel ---
class NotesTableModel : public QAbstractTableModel
{
    Q_OBJECT

public:
    explicit NotesTableModel(QObject *parent = nullptr);

    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    int columnCount(const QModelIndex &parent = QModelIndex()) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QVariant headerData(int section, Qt::Orientation orientation, int role = Qt::DisplayRole) const override;
    bool setData(const QModelIndex &index, const QVariant &value, int role = Qt::EditRole) override;
    Qt::ItemFlags flags(const QModelIndex &index) const override;

    void loadNotes(); // Reload notes from DB
    DesktopNotesData::Note getNoteAt(int row) const;


private:
    QList<DesktopNotesData::Note> m_notes;
    DesktopNotesData::DatabaseManager* m_dbManager;
};


// --- AllNotesDialog ---
class AllNotesDialog : public QDialog
{
    Q_OBJECT

public:
    explicit AllNotesDialog(QWidget *parent = nullptr);
    ~AllNotesDialog();

private slots:
    void onRefreshClicked();
    void onTableDoubleClicked(const QModelIndex &index); // For toggling status

private:
    void setupUi();

    QTableView *m_tableView;
    NotesTableModel *m_tableModel;
    QPushButton *m_refreshButton;
    QPushButton *m_closeButton;
    DesktopNotesData::DatabaseManager* m_dbManager;
};

#endif // ALLNOTESDIALOG_H
