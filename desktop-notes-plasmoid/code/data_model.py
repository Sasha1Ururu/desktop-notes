import os
import sqlite3
import json
import uuid

NOTES_DB_DIR = os.path.expanduser("~/.local/share/desktop-notes")
NOTES_DB_PATH = os.path.join(NOTES_DB_DIR, "notes.db")

def generate_unique_id():
    """Generates a unique ID for a note."""
    return str(uuid.uuid4())

class Note:
    def __init__(self, id=None, status="shown", filepath=None, position_x=100, position_y=100,
                 width=300, height=200, transparency=0.8, background_color="#333333", margin=10,
                 applet_instance_id=None): # applet_instance_id is the Plasma-given ID for the widget instance
        self.id = id if id else generate_unique_id() # This is the DB unique ID
        self.applet_instance_id = applet_instance_id # This is Plasma's ID for the widget instance
        self.status = status
        self.filepath = filepath
        self.position = {"x": position_x, "y": position_y}
        self.size = {"width": width, "height": height}
        self.style = {
            "transparency": transparency,
            "backgroundColor": background_color,
            "margin": margin
        }

    def to_dict(self):
        return {
            "id": self.id,
            "applet_instance_id": self.applet_instance_id,
            "status": self.status,
            "filepath": self.filepath,
            "position_x": self.position["x"],
            "position_y": self.position["y"],
            "width": self.size["width"],
            "height": self.size["height"],
            "style_transparency": self.style["transparency"],
            "style_backgroundColor": self.style["backgroundColor"],
            "style_margin": self.style["margin"]
        }

    @classmethod
    def from_dict(cls, data_dict):
        return cls(
            id=data_dict.get("id"),
            applet_instance_id=data_dict.get("applet_instance_id"),
            status=data_dict.get("status", "shown"),
            filepath=data_dict.get("filepath"),
            position_x=data_dict.get("position_x", 100),
            position_y=data_dict.get("position_y", 100),
            width=data_dict.get("width", 300),
            height=data_dict.get("height", 200),
            transparency=data_dict.get("style_transparency", 0.8),
            background_color=data_dict.get("style_backgroundColor", "#333333"),
            margin=data_dict.get("style_margin", 10)
        )

    def to_db_tuple(self):
        """Converts Note object to a tuple for database insertion/update, excluding applet_instance_id which is not stored in this table directly."""
        return (
            self.id,
            self.status,
            self.filepath,
            self.position["x"],
            self.position["y"],
            self.size["width"],
            self.size["height"],
            self.style["transparency"],
            self.style["backgroundColor"],
            self.style["margin"]
        )

    @classmethod
    def from_db_row(cls, row):
        """Creates a Note object from a database row tuple."""
        if not row:
            return None
        return cls(
            id=row[0],
            status=row[1],
            filepath=row[2],
            position_x=row[3],
            position_y=row[4],
            width=row[5],
            height=row[6],
            transparency=row[7],
            background_color=row[8],
            margin=row[9]
            # applet_instance_id is not in the main notes table row
        )

def init_db():
    """Initializes the database and the notes table if they don't exist."""
    os.makedirs(NOTES_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(NOTES_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'shown',
            filepath TEXT,
            position_x INTEGER DEFAULT 100,
            position_y INTEGER DEFAULT 100,
            width INTEGER DEFAULT 300,
            height INTEGER DEFAULT 200,
            style_transparency REAL DEFAULT 0.8,
            style_backgroundColor TEXT DEFAULT '#333333',
            style_margin INTEGER DEFAULT 10
        )
    """)
    # Potentially another table to map applet_instance_id to note_id if needed,
    # or store applet_instance_id in the plasmoid's own config if it's persistent.
    # For now, we'll assume applet_instance_id is primarily for runtime mapping.
    # Plasma provides instance-specific configuration via KConfigXT.
    # We might store the note 'id' (our UUID) in the plasmoid's instance config.

    conn.commit()
    conn.close()

# Initialize DB on module load
init_db()

def add_note(note):
    """Adds a new note to the database."""
    conn = sqlite3.connect(NOTES_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO notes (id, status, filepath, position_x, position_y, width, height, style_transparency, style_backgroundColor, style_margin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, note.to_db_tuple())
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Error: Note with ID {note.id} already exists.")
        return False
    finally:
        conn.close()
    return True

def get_note_by_id(note_id):
    """Retrieves a note by its ID."""
    conn = sqlite3.connect(NOTES_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    row = cursor.fetchone()
    conn.close()
    return Note.from_db_row(row) if row else None

def get_all_notes():
    """Retrieves all notes from the database."""
    conn = sqlite3.connect(NOTES_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes")
    rows = cursor.fetchall()
    conn.close()
    return [Note.from_db_row(row) for row in rows]

def update_note(note):
    """Updates an existing note in the database."""
    conn = sqlite3.connect(NOTES_DB_PATH)
    cursor = conn.cursor()
    db_tuple = note.to_db_tuple()
    # Reorder tuple for UPDATE: status, filepath, ..., id
    update_tuple = db_tuple[1:] + (db_tuple[0],)
    try:
        cursor.execute("""
            UPDATE notes SET
                status = ?, filepath = ?, position_x = ?, position_y = ?,
                width = ?, height = ?, style_transparency = ?,
                style_backgroundColor = ?, style_margin = ?
            WHERE id = ?
        """, update_tuple)
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Warning: Note with ID {note.id} not found for update.")
            return False
    except Exception as e:
        print(f"Error updating note {note.id}: {e}")
        return False
    finally:
        conn.close()
    return True

def delete_note(note_id):
    """Deletes a note from the database by its ID."""
    conn = sqlite3.connect(NOTES_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Warning: Note with ID {note_id} not found for deletion.")
            return False
    except Exception as e:
        print(f"Error deleting note {note_id}: {e}")
        return False
    finally:
        conn.close()
    return True

if __name__ == '__main__':
    # Example Usage (not run by Plasma)
    print("Running data_model.py example usage...")
    init_db() # Ensure DB is ready

    # Clean up existing test notes if any
    for existing_note in get_all_notes():
        if "test-note-" in existing_note.id:
            delete_note(existing_note.id)

    print(f"Database path: {NOTES_DB_PATH}")

    # Create a new note
    new_note_id = "test-note-" + generate_unique_id()
    note1 = Note(id=new_note_id, filepath="/tmp/test.txt", position_x=50, position_y=50)
    if add_note(note1):
        print(f"Added note with ID: {note1.id}")
    else:
        print(f"Failed to add note with ID: {note1.id}")


    # Retrieve the note
    retrieved_note = get_note_by_id(note1.id)
    if retrieved_note:
        print(f"Retrieved note: {retrieved_note.to_dict()}")
        assert retrieved_note.filepath == "/tmp/test.txt"

    # Update the note
    if retrieved_note:
        retrieved_note.filepath = "/tmp/updated_test.txt"
        retrieved_note.status = "hidden"
        retrieved_note.style["backgroundColor"] = "#FF0000"
        if update_note(retrieved_note):
            print(f"Updated note with ID: {retrieved_note.id}")
        else:
            print(f"Failed to update note with ID: {retrieved_note.id}")


        # Verify update
        updated_note_check = get_note_by_id(retrieved_note.id)
        if updated_note_check:
            print(f"Verified updated note: {updated_note_check.to_dict()}")
            assert updated_note_check.filepath == "/tmp/updated_test.txt"
            assert updated_note_check.status == "hidden"
            assert updated_note_check.style["backgroundColor"] == "#FF0000"

    # Get all notes
    all_notes = get_all_notes()
    print(f"All notes ({len(all_notes)}):")
    for n in all_notes:
        print(n.to_dict())

    # Delete the note
    if delete_note(note1.id):
        print(f"Deleted note with ID: {note1.id}")
    else:
        print(f"Failed to delete note with ID: {note1.id}")

    # Verify deletion
    deleted_note_check = get_note_by_id(note1.id)
    assert deleted_note_check is None
    print("Example usage finished.")
