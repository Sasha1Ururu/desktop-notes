#include "databasemanager.h"
#include "../config.h" // For getDatabaseFilePath()

#include <QSqlQuery>
#include <QSqlError>
#include <QFile>
#include <QStandardPaths>
#include <QDir>
#include <QDebug> // For logging errors

#include <QJsonDocument> // For storing style object as JSON string
#include <QJsonObject>   // For style object

namespace DesktopNotesData {

DatabaseManager* DatabaseManager::m_instance = nullptr;

DatabaseManager* DatabaseManager::instance()
{
    if (!m_instance) {
        m_instance = new DatabaseManager();
        // Attempt to open and initialize the database upon first instance creation.
        if (!m_instance->openDb()) {
            qWarning() << "DatabaseManager: Failed to open or initialize the database on instance creation.";
            // Caller might want to check if DB is valid after getting instance.
        }
    }
    return m_instance;
}

DatabaseManager::DatabaseManager()
{
    // Note: Actual DB opening is deferred to openDb(), called by instance() or explicitly.
}

DatabaseManager::~DatabaseManager()
{
    if (m_db.isOpen()) {
        m_db.close();
    }
    // m_instance is a static member, not deleted here.
    // It could be cleaned up at application exit if necessary,
    // but for a plasmoid, its lifecycle is tied to plasmashell.
}

bool DatabaseManager::openDb()
{
    if (m_db.isOpen()) {
        return true;
    }

    m_db = QSqlDatabase::addDatabase("QSQLITE", "desktopNotesConnection"); // Connection name
    QString dbPath = DesktopNotesConfig::getDatabaseFilePath();

    QDir dbDir = QFileInfo(dbPath).absoluteDir();
    if (!dbDir.exists()) {
        if (!dbDir.mkpath(".")) {
            qWarning() << "DatabaseManager: Could not create database directory:" << dbDir.path();
            return false;
        }
    }

    m_db.setDatabaseName(dbPath);

    if (!m_db.open()) {
        qWarning() << "DatabaseManager: Failed to open database:" << m_db.lastError().text() << "at path" << dbPath;
        return false;
    }

    qInfo() << "DatabaseManager: Database opened successfully at" << dbPath;
    return initializeDatabase();
}

bool DatabaseManager::initializeDatabase()
{
    if (!m_db.isOpen()) {
        qWarning() << "DatabaseManager: Database is not open for initialization.";
        return false;
    }

    QSqlQuery query(m_db);
    // Note: SQLite is case-insensitive for table/column names by default, but good practice to be consistent.
    // Using TEXT for style, which will store a JSON string representation of the style object.
    QString createTableQuery = R"(
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL DEFAULT 'shown',
            filepath TEXT,
            position_x INTEGER DEFAULT 50,
            position_y INTEGER DEFAULT 50,
            size_width INTEGER DEFAULT 200,
            size_height INTEGER DEFAULT 150,
            style TEXT
        );
    )";

    if (!query.exec(createTableQuery)) {
        qWarning() << "DatabaseManager: Failed to create 'notes' table:" << query.lastError().text();
        return false;
    }

    // qInfo() << "DatabaseManager: 'notes' table initialized/verified successfully.";

    // Potential future: Check for schema migrations if app version changes
    // For example, adding new columns with ALTER TABLE if they don't exist.
    // QSqlRecord record = m_db.record("notes");
    // if (!record.contains("new_column")) {
    //     query.exec("ALTER TABLE notes ADD COLUMN new_column TEXT;");
    // }

    return true;
}

QVariantMap DatabaseManager::styleToVariantMap(const NoteStyle& style) const
{
    QVariantMap map;
    map["transparency"] = style.transparency;
    map["backgroundColor"] = style.backgroundColor;
    map["margin"] = style.margin;
    return map;
}

NoteStyle DatabaseManager::styleFromVariantMap(const QVariantMap& map) const
{
    NoteStyle style;
    style.transparency = map.value("transparency", 1.0).toDouble();
    style.backgroundColor = map.value("backgroundColor", "#FFFFE0").toString();
    style.margin = map.value("margin", 10).toInt();
    return style;
}


int DatabaseManager::addNote(const Note& noteData)
{
    if (!m_db.isOpen() && !openDb()) { // Ensure DB is open
        qWarning() << "DatabaseManager::addNote: Database not open.";
        return -1;
    }

    QSqlQuery query(m_db);
    query.prepare(R"(
        INSERT INTO notes (status, filepath, position_x, position_y, size_width, size_height, style)
        VALUES (:status, :filepath, :position_x, :position_y, :size_width, :size_height, :style)
    )");

    query.bindValue(":status", noteData.status);
    query.bindValue(":filepath", noteData.filepath.isEmpty() ? QVariant(QVariant::String) : noteData.filepath); // Store NULL if empty
    query.bindValue(":position_x", noteData.position.x());
    query.bindValue(":position_y", noteData.position.y());
    query.bindValue(":size_width", noteData.size.width());
    query.bindValue(":size_height", noteData.size.height());

    QJsonDocument doc = QJsonDocument::fromVariant(styleToVariantMap(noteData.style));
    query.bindValue(":style", doc.toJson(QJsonDocument::Compact));

    if (!query.exec()) {
        qWarning() << "DatabaseManager::addNote: Failed to insert note:" << query.lastError().text();
        return -1;
    }

    int newId = query.lastInsertId().toInt();
    qInfo() << "DatabaseManager: Added note with ID:" << newId;
    return newId;
}

bool DatabaseManager::updateNote(const Note& noteData)
{
    if (noteData.id == -1) {
        qWarning() << "DatabaseManager::updateNote: Invalid note ID (-1).";
        return false;
    }
    if (!m_db.isOpen() && !openDb()) {
        qWarning() << "DatabaseManager::updateNote: Database not open.";
        return false;
    }

    QSqlQuery query(m_db);
    query.prepare(R"(
        UPDATE notes SET
            status = :status,
            filepath = :filepath,
            position_x = :position_x,
            position_y = :position_y,
            size_width = :size_width,
            size_height = :size_height,
            style = :style
        WHERE id = :id
    )");

    query.bindValue(":id", noteData.id);
    query.bindValue(":status", noteData.status);
    query.bindValue(":filepath", noteData.filepath.isEmpty() ? QVariant(QVariant::String) : noteData.filepath);
    query.bindValue(":position_x", noteData.position.x());
    query.bindValue(":position_y", noteData.position.y());
    query.bindValue(":size_width", noteData.size.width());
    query.bindValue(":size_height", noteData.size.height());

    QJsonDocument doc = QJsonDocument::fromVariant(styleToVariantMap(noteData.style));
    query.bindValue(":style", doc.toJson(QJsonDocument::Compact));

    if (!query.exec()) {
        qWarning() << "DatabaseManager::updateNote: Failed to update note ID" << noteData.id << ":" << query.lastError().text();
        return false;
    }

    if (query.numRowsAffected() == 0) {
        qWarning() << "DatabaseManager::updateNote: Note with ID" << noteData.id << "not found for update.";
        // return false; // Or true if "not found" isn't a failure of the update *operation* itself
    }
    // qInfo() << "DatabaseManager: Updated note with ID:" << noteData.id;
    return true;
}

Note DatabaseManager::getNoteById(int id)
{
    Note note; // Default invalid note
    if (!m_db.isOpen() && !openDb()) {
        qWarning() << "DatabaseManager::getNoteById: Database not open.";
        return note;
    }

    QSqlQuery query(m_db);
    query.prepare("SELECT id, status, filepath, position_x, position_y, size_width, size_height, style FROM notes WHERE id = :id");
    query.bindValue(":id", id);

    if (!query.exec()) {
        qWarning() << "DatabaseManager::getNoteById: Failed to fetch note ID" << id << ":" << query.lastError().text();
        return note;
    }

    if (query.next()) {
        note.id = query.value("id").toInt();
        note.status = query.value("status").toString();
        note.filepath = query.value("filepath").isNull() ? QString() : query.value("filepath").toString();
        note.position = QPoint(query.value("position_x").toInt(), query.value("position_y").toInt());
        note.size = QSize(query.value("size_width").toInt(), query.value("size_height").toInt());

        QJsonDocument doc = QJsonDocument::fromJson(query.value("style").toByteArray());
        note.style = styleFromVariantMap(doc.object().toVariantMap());
    } else {
        // qWarning() << "DatabaseManager::getNoteById: Note with ID" << id << "not found.";
    }
    return note;
}

QList<Note> DatabaseManager::getAllNotes()
{
    QList<Note> notes;
    if (!m_db.isOpen() && !openDb()) {
        qWarning() << "DatabaseManager::getAllNotes: Database not open.";
        return notes;
    }

    QSqlQuery query("SELECT id, status, filepath, position_x, position_y, size_width, size_height, style FROM notes", m_db);

    if (!query.exec()) {
        qWarning() << "DatabaseManager::getAllNotes: Failed to fetch all notes:" << query.lastError().text();
        return notes;
    }

    while (query.next()) {
        Note note;
        note.id = query.value("id").toInt();
        note.status = query.value("status").toString();
        note.filepath = query.value("filepath").isNull() ? QString() : query.value("filepath").toString();
        note.position = QPoint(query.value("position_x").toInt(), query.value("position_y").toInt());
        note.size = QSize(query.value("size_width").toInt(), query.value("size_height").toInt());

        QJsonDocument doc = QJsonDocument::fromJson(query.value("style").toByteArray());
        note.style = styleFromVariantMap(doc.object().toVariantMap());
        notes.append(note);
    }
    return notes;
}

bool DatabaseManager::deleteNoteById(int id)
{
    if (!m_db.isOpen() && !openDb()) {
        qWarning() << "DatabaseManager::deleteNoteById: Database not open.";
        return false;
    }

    QSqlQuery query(m_db);
    query.prepare("DELETE FROM notes WHERE id = :id");
    query.bindValue(":id", id);

    if (!query.exec()) {
        qWarning() << "DatabaseManager::deleteNoteById: Failed to delete note ID" << id << ":" << query.lastError().text();
        return false;
    }

    if (query.numRowsAffected() == 0) {
        // qWarning() << "DatabaseManager::deleteNoteById: Note with ID" << id << "not found for deletion.";
    } else {
        qInfo() << "DatabaseManager: Deleted note with ID:" << id;
    }
    return true;
}

bool DatabaseManager::setNoteStatus(int id, const QString& status)
{
    if (!m_db.isOpen() && !openDb()) {
        qWarning() << "DatabaseManager::setNoteStatus: Database not open.";
        return false;
    }

    QSqlQuery query(m_db);
    query.prepare("UPDATE notes SET status = :status WHERE id = :id");
    query.bindValue(":status", status);
    query.bindValue(":id", id);

    if (!query.exec()) {
        qWarning() << "DatabaseManager::setNoteStatus: Failed to update status for note ID" << id << ":" << query.lastError().text();
        return false;
    }
    if (query.numRowsAffected() == 0) {
        qWarning() << "DatabaseManager::setNoteStatus: Note with ID" << id << "not found for status update.";
    }
    return true;
}


} // namespace DesktopNotesData
