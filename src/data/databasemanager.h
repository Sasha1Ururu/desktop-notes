#ifndef DATABASEMANAGER_H
#define DATABASEMANAGER_H

#include "notedata.h" // Includes Note and NoteStyle
#include <QString>
#include <QList>
#include <QSqlDatabase>
#include <QVariant> // For QVariantMap for style

// Using the same namespace
namespace DesktopNotesData {

class DatabaseManager
{
public:
    // Singleton access
    static DatabaseManager* instance();

    // Prevent copying and assignment
    DatabaseManager(const DatabaseManager&) = delete;
    DatabaseManager& operator=(const DatabaseManager&) = delete;

    // Database operations
    bool openDb(); // Opens (and initializes if necessary) the database

    // CRUD for Notes
    // Returns new note ID on success, -1 on failure
    int addNote(const Note& noteData);
    bool updateNote(const Note& noteData);
    Note getNoteById(int id);
    QList<Note> getAllNotes();
    bool deleteNoteById(int id);
    bool setNoteStatus(int id, const QString& status);

    // Helper to get a new unique ID if needed before full insertion,
    // though addNote should handle ID generation.
    // int getNextNoteId();


private:
    DatabaseManager(); // Private constructor for singleton
    ~DatabaseManager();

    bool initializeDatabase(); // Creates tables if they don't exist

    QSqlDatabase m_db;
    static DatabaseManager* m_instance;

    // Helper to convert NoteStyle to QVariantMap for JSON storage in DB
    // and vice-versa. SQLite doesn't have a native JSON type, so store as TEXT.
    QVariantMap styleToVariantMap(const NoteStyle& style) const;
    NoteStyle styleFromVariantMap(const QVariantMap& map) const;
};

} // namespace DesktopNotesData

#endif // DATABASEMANAGER_H
