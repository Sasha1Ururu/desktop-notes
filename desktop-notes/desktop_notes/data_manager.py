import sqlite3
import json
from . import config

class DataManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.DATABASE_FILE
        self._conn = None
        self._cursor = None
        self._connect()
        self._create_table()

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row # Access columns by name
        self._cursor = self._conn.cursor()

    def _create_table(self):
        """Creates the notes table if it doesn't already exist."""
        try:
            self._cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {config.DB_TABLE_NOTES} (
                    {config.DB_COL_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                    {config.DB_COL_STATUS} TEXT NOT NULL,
                    {config.DB_COL_FILEPATH} TEXT,
                    {config.DB_COL_POS_X} INTEGER NOT NULL,
                    {config.DB_COL_POS_Y} INTEGER NOT NULL,
                    {config.DB_COL_SIZE_W} INTEGER NOT NULL,
                    {config.DB_COL_SIZE_H} INTEGER NOT NULL,
                    {config.DB_COL_STYLE_TRANSPARENCY} REAL NOT NULL,
                    {config.DB_COL_STYLE_BG_COLOR} TEXT NOT NULL,
                    {config.DB_COL_STYLE_MARGIN} INTEGER NOT NULL
                )
            """)
            self._conn.commit()
        except sqlite3.Error as e:
            print(f"Database error during table creation: {e}")
            # In a real app, might raise this or handle more gracefully

    def _note_from_row(self, row):
        """Converts a database row (sqlite3.Row) to a note dictionary."""
        if not row:
            return None
        return {
            "id": row[config.DB_COL_ID],
            "status": row[config.DB_COL_STATUS],
            "filepath": row[config.DB_COL_FILEPATH],
            "position": {
                "x": row[config.DB_COL_POS_X],
                "y": row[config.DB_COL_POS_Y]
            },
            "size": {
                "width": row[config.DB_COL_SIZE_W],
                "height": row[config.DB_COL_SIZE_H]
            },
            "style": {
                "transparency": row[config.DB_COL_STYLE_TRANSPARENCY],
                "backgroundColor": row[config.DB_COL_STYLE_BG_COLOR],
                "margin": row[config.DB_COL_STYLE_MARGIN]
            }
        }

    def create_note(self, filepath=None, position=None, size=None, style=None, status=None):
        """
        Adds a new note to the database with specified or default values.
        Returns the new note's data as a dictionary, including its ID.
        """
        pos = position or {"x": config.INITIAL_POS_X, "y": config.INITIAL_POS_Y}
        sz = size or {"width": config.INITIAL_SIZE_W, "height": config.INITIAL_SIZE_H}
        stl = style or config.INITIAL_STYLE.copy()
        stat = status or config.NOTE_STATUS_SHOWN

        try:
            self._cursor.execute(f"""
                INSERT INTO {config.DB_TABLE_NOTES} (
                    {config.DB_COL_STATUS}, {config.DB_COL_FILEPATH},
                    {config.DB_COL_POS_X}, {config.DB_COL_POS_Y},
                    {config.DB_COL_SIZE_W}, {config.DB_COL_SIZE_H},
                    {config.DB_COL_STYLE_TRANSPARENCY}, {config.DB_COL_STYLE_BG_COLOR}, {config.DB_COL_STYLE_MARGIN}
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stat, filepath,
                pos['x'], pos['y'],
                sz['width'], sz['height'],
                stl['transparency'], stl['backgroundColor'], stl['margin']
            ))
            self._conn.commit()
            new_id = self._cursor.lastrowid
            return self.get_note(new_id)
        except sqlite3.Error as e:
            print(f"Database error during note creation: {e}")
            return None

    def get_note(self, note_id):
        """Retrieves a specific note by its ID."""
        try:
            self._cursor.execute(f"SELECT * FROM {config.DB_TABLE_NOTES} WHERE {config.DB_COL_ID} = ?", (note_id,))
            row = self._cursor.fetchone()
            return self._note_from_row(row)
        except sqlite3.Error as e:
            print(f"Database error while getting note {note_id}: {e}")
            return None

    def get_all_notes(self):
        """Retrieves all notes from the database."""
        try:
            self._cursor.execute(f"SELECT * FROM {config.DB_TABLE_NOTES}")
            rows = self._cursor.fetchall()
            return [self._note_from_row(row) for row in rows]
        except sqlite3.Error as e:
            print(f"Database error while getting all notes: {e}")
            return []

    def update_note(self, note_id, data):
        """
        Updates specified fields for a note.
        'data' is a dictionary where keys are 'status', 'filepath', 'position', 'size', 'style'.
        Partial updates are allowed (e.g., only update 'filepath').
        """
        if not data:
            return False

        fields_to_update = []
        values = []

        if "status" in data:
            fields_to_update.append(f"{config.DB_COL_STATUS} = ?")
            values.append(data["status"])
        if "filepath" in data:
            fields_to_update.append(f"{config.DB_COL_FILEPATH} = ?")
            values.append(data["filepath"])
        if "position" in data and isinstance(data["position"], dict):
            fields_to_update.append(f"{config.DB_COL_POS_X} = ?")
            values.append(data["position"]["x"])
            fields_to_update.append(f"{config.DB_COL_POS_Y} = ?")
            values.append(data["position"]["y"])
        if "size" in data and isinstance(data["size"], dict):
            fields_to_update.append(f"{config.DB_COL_SIZE_W} = ?")
            values.append(data["size"]["width"])
            fields_to_update.append(f"{config.DB_COL_SIZE_H} = ?")
            values.append(data["size"]["height"])
        if "style" in data and isinstance(data["style"], dict):
            style_data = data["style"]
            if "transparency" in style_data:
                fields_to_update.append(f"{config.DB_COL_STYLE_TRANSPARENCY} = ?")
                values.append(style_data["transparency"])
            if "backgroundColor" in style_data:
                fields_to_update.append(f"{config.DB_COL_STYLE_BG_COLOR} = ?")
                values.append(style_data["backgroundColor"])
            if "margin" in style_data:
                fields_to_update.append(f"{config.DB_COL_STYLE_MARGIN} = ?")
                values.append(style_data["margin"])

        if not fields_to_update:
            return False # No valid fields to update

        values.append(note_id)
        sql = f"UPDATE {config.DB_TABLE_NOTES} SET {', '.join(fields_to_update)} WHERE {config.DB_COL_ID} = ?"

        try:
            self._cursor.execute(sql, tuple(values))
            self._conn.commit()
            return self._cursor.rowcount > 0 # Returns True if update was successful
        except sqlite3.Error as e:
            print(f"Database error during note update for ID {note_id}: {e}")
            return False

    def delete_note(self, note_id):
        """Deletes a note by its ID."""
        try:
            self._cursor.execute(f"DELETE FROM {config.DB_TABLE_NOTES} WHERE {config.DB_COL_ID} = ?", (note_id,))
            self._conn.commit()
            return self._cursor.rowcount > 0 # Returns True if deletion was successful
        except sqlite3.Error as e:
            print(f"Database error during note deletion for ID {note_id}: {e}")
            return False

    def close(self):
        """Closes the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._cursor = None

    def __del__(self):
        """Ensure connection is closed when DataManager instance is deleted."""
        self.close()

if __name__ == '__main__':
    # Example Usage (for testing purposes, not part of app logic)
    # Ensure config.py is in the same directory or PYTHONPATH is set up
    print("Testing DataManager...")
    # Use a temporary in-memory database for testing
    dm = DataManager(db_path=":memory:")

    print("\n1. Creating initial table (if not exists)...")
    # (Implicitly done in __init__)

    print("\n2. Creating a new note...")
    new_note_data = dm.create_note(
        filepath="/tmp/test1.txt",
        position={"x": 10, "y": 20},
        size={"width": 200, "height": 100},
        style={"transparency": 0.9, "backgroundColor": "#ABCDEF", "margin": 5},
        status=config.NOTE_STATUS_SHOWN
    )
    if new_note_data:
        print(f"Created note: {new_note_data}")
        note_id_1 = new_note_data['id']
    else:
        print("Failed to create note.")
        exit()

    print("\n3. Creating another note with defaults...")
    default_note_data = dm.create_note(filepath="/tmp/default.md")
    if default_note_data:
        print(f"Created note with defaults: {default_note_data}")
        note_id_2 = default_note_data['id']
    else:
        print("Failed to create note with defaults.")

    print("\n4. Getting a specific note (ID 1)...")
    retrieved_note = dm.get_note(note_id_1)
    print(f"Retrieved note ID {note_id_1}: {retrieved_note}")

    print("\n5. Getting all notes...")
    all_notes = dm.get_all_notes()
    print(f"All notes ({len(all_notes)}):")
    for note in all_notes:
        print(note)

    print(f"\n6. Updating note ID {note_id_1}...")
    update_success = dm.update_note(note_id_1, {
        "filepath": "/tmp/updated_test1.txt",
        "status": config.NOTE_STATUS_HIDDEN,
        "position": {"x": 15, "y": 25},
        "style": {"backgroundColor": "#112233"} # Partial style update
    })
    if update_success:
        print(f"Update successful. Updated note: {dm.get_note(note_id_1)}")
    else:
        print("Update failed.")

    print(f"\n7. Deleting note ID {note_id_2}...")
    delete_success = dm.delete_note(note_id_2)
    if delete_success:
        print(f"Deletion successful. Note {note_id_2} should be gone.")
    else:
        print("Deletion failed.")

    print("\n8. Getting all notes after deletion...")
    all_notes_after_delete = dm.get_all_notes()
    print(f"All notes ({len(all_notes_after_delete)}):")
    for note in all_notes_after_delete:
        print(note)

    print("\n9. Attempting to get deleted note (ID 2)...")
    deleted_note_check = dm.get_note(note_id_2)
    print(f"Retrieved deleted note ID {note_id_2}: {deleted_note_check}")


    print("\n10. Closing database connection...")
    dm.close()
    print("DataManager test complete.")
