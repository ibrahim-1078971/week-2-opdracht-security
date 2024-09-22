import sqlite3
from pathlib import Path


class Testgtp:
    "This class executes SQLITE queries"

    def __init__(self, db):
        db_path = Path(db)
        if not db_path.exists():
            raise FileNotFoundError(f"database file {db} bestaat niet")
        self.db_path = db_path

    def get_cursor(self):
        "Connects to the database"
        connection = sqlite3.connect('databases/testgpt.db')
        cursor = connection.cursor()
        cursor.row_factory = sqlite3.Row
        return cursor
    
    def get_note_questions(self, note_id):
        """Returns all questions related to a note

        note_id = int
        """
        cursor = self.get_cursor()
        cursor.execute(
            f"SELECT exam_question FROM questions WHERE note_id = {note_id}")
        return cursor.fetchall()

    def get_all_notes(self, subject, teacher, title, page_number):
        """returns inforation of all public notes

        subject = str
        teacher = str
        title = str
        page_number = int"""

        if subject == 'alle categorien':
            subject = ''
        if teacher == 'alle docenten':
            teacher = ''

        cursor = self.get_cursor()
        cursor.execute(
            f'''SELECT note_id, title, teachers.display_name teacher_id,
            categories.omschrijving category_id ,notes.date_created, note  
            FROM notes 
            JOIN teachers ON notes.teacher_id = teachers.teacher_id 
            JOIN categories ON notes.category_id = categories.category_id 
            WHERE omschrijving LIKE "%{subject}%"
            AND display_name LIKE "%{teacher}%"
            AND title LIKE "%{title}%"
            AND is_public = 1 
            LIMIT 20 OFFSET {page_number};''')
        return cursor.fetchall()

    def get_my_notes(self, subject, title, page_number, current_user):
        """Returns information of personal notes

        subject = str
        title = str
        page_number = int
        current_user = int
        """

        if subject == 'alle categorien':
            subject = ''
        cursor = self.get_cursor()
        cursor.execute(
            f'''SELECT note_id, title, categories.omschrijving category_id,
            note, notes.date_created, is_public 
            FROM notes 
            JOIN categories ON notes.category_id = categories.category_id 
            WHERE omschrijving LIKE "%{subject}%"
            AND title LIKE "%{title}%"
            AND teacher_id = {current_user}
            LIMIT 20 OFFSET {page_number};''')
        return cursor.fetchall()

    def get_note_information(self, row, note_id):
        """Returns specific information about notes

        row = string ('teacher','category','question')
        note_id = int
        """

        cursor = self.get_cursor()
        if row == 'teacher':

            cursor.execute(
                f"SELECT teacher_id FROM notes WHERE note_id ={note_id}")
        elif row == 'category':
            cursor.execute(
                f"SELECT category_id FROM notes WHERE note_id = {note_id}")
        elif row == 'question':
            cursor.execute(
                f"""SELECT exam_question FROM questions
                JOIN notes ON questions.note_id = notes.note_id WHERE notes.note_id = {note_id}""")
        else:
            cursor.execute(
                f"SELECT {row} FROM notes WHERE note_id = {note_id}")

        return cursor.fetchall()

    def get_teacher_name(self, teacher_id):
        """Returns the name of a teacher

        teacher_id = int"""

        cursor = self.get_cursor()
        cursor.execute(
            f'SELECT display_name FROM teachers WHERE teacher_id = {teacher_id}')
        return cursor.fetchall()

    def get_category_name(self, category_id):
        """Returns name of a category

        category_id = int"""

        cursor = self.get_cursor()
        cursor.execute(
            f'SELECT omschrijving FROM categories WHERE category_id = {category_id}')
        return cursor.fetchall()

    def get_teachers(self):
        """Returns IDs and names of all teachers"""

        cursor = self.get_cursor()
        cursor.execute('SELECT teacher_id, display_name FROM teachers')
        return cursor.fetchall()

    def get_categories(self):
        """Returns IDs and names of all categories"""

        cursor = self.get_cursor()
        cursor.execute('SELECT DISTINCT omschrijving FROM categories')
        return cursor.fetchall()

    def get_teacher_id(self):
        """Returns everything from all teachers"""

        cursor = self.get_cursor()
        cursor.execute('SELECT * FROM teachers')
        return cursor.fetchall()

    def get_category_id(self):
        """Returns everything from all categories 
        where the category names are different"""

        cursor = self.get_cursor()
        cursor.execute('SELECT * FROM categories GROUP BY omschrijving')
        return cursor.fetchall()

    def create_note(self, title, note_source, teacher_id, category_id, note):
        """Creates a new note

        title = str
        note_source = str
        teacher_id = int
        category_id = int
        note = str
        """

        cursor = self.get_cursor()
        cursor.execute("INSERT INTO notes (title, note_source,teacher_id, category_id, note)"
                       " VALUES (?, ?, ?, ?, ?)",
                       (title, note_source, teacher_id, category_id, note,))
        cursor.connection.commit()
        return cursor.lastrowid

    def get_note_id(self):
        """Returns the IDs of all notes"""

        cursor = self.get_cursor()
        cursor.execute('SELECT note_id FROM notes')
        return cursor.fetchall()

    def delete_note(self, note_id):
        """deletes a note

        note_id = int
        """

        cursor = self.get_cursor()
        cursor.execute(f'DELETE FROM notes WHERE note_id = {note_id}')
        cursor.connection.commit()
        return cursor.lastrowid

    def get_note_publicity(self, note_id):
        """returns wether a note is public or not
        note_id = int"""

        cursor = self.get_cursor()
        cursor.execute(
            f'SELECT is_public FROM notes WHERE note_id = {note_id}')
        return cursor.fetchone()

    def change_publicity(self, note_id, is_public):
        """changes wether a note is public or not
        note_id = int
        is_public = boolean"""

        cursor = self.get_cursor()
        cursor.execute(
            f'UPDATE notes SET is_public = {not is_public} WHERE note_id = {note_id}')
        cursor.connection.commit()
        return cursor.lastrowid

    def insert_teacher(self, display_name, username, email, teacher_password, is_admin):
        """creates a new teacher

        display_name = str
        username = str
        email = str
        teacher_password = str"""

        cursor = self.get_cursor()
        cursor.execute("""INSERT INTO teachers
                        (display_name, username, email, teacher_password, is_admin)
                        VALUES (?, ?, ?, ?, ?)""",
                       (display_name, username, email, teacher_password, is_admin))
        cursor.connection.commit()

    def remove_teacher(self, teacher_id):
        """Removes a teacher

        teacher_id = int"""

        cursor = self.get_cursor()
        cursor.execute(
            "DELETE FROM teachers WHERE teacher_id = ?", (teacher_id,))
        cursor.connection.commit()

    
    def get_teachers(self):
        connection = sqlite3.connect('databases/testgpt.db')
        cursor = connection.cursor()
        cursor.execute("SELECT teacher_id, display_name FROM teachers")
        teachers = cursor.fetchall()
        connection.close()
        return teachers
    
    def get_teacher_information(self, teacher_id):
        cursor = self.get_cursor()
        cursor.execute('SELECT * FROM teachers WHERE teacher_id = ?', (teacher_id,))
        return cursor.fetchone()

    def update_teacher(self, teacher_id, new_display_name, new_username, new_email, new_password, is_admin):
        cursor = self.get_cursor()
        cursor.execute('''
            UPDATE teachers
            SET display_name = ?,
                username = ?,
                email = ?,
                teacher_password = ?,
                is_admin = ?
                
        WHERE teacher_id = ?
        ''', (new_display_name, new_username, new_email, new_password, is_admin, teacher_id))
        cursor.connection.commit()
        
    def create_question(self, note_id, exam_question):
        cursor = self.get_cursor()
        cursor.execute("INSERT INTO questions (note_id, exam_question)"
                    " VALUES (?, ?)",
                    (note_id, exam_question,))
        cursor.connection.commit()
        return cursor.lastrowid
