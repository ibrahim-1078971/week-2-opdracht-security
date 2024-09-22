import os
import sqlite3
import openai
import csv
from flask import Flask, redirect, url_for, render_template, request, session
from flask import Response
from werkzeug.security import generate_password_hash, check_password_hash  # Voeg deze regel toe
from lib.sqlite_queries import Testgtp
from lib.testgpt.testgpt import TestGPT
import re

app = Flask(__name__, static_url_path='/static')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_PERMANENT=False,
)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') 
openai.api_key = ""

DATABASE_FILE = "databases/testgpt.db"
sqlite_queries = Testgtp(DATABASE_FILE)


def connect_db():
    """ database connect"""
    return sqlite3.connect('databases/testgpt.db', check_same_thread=False)


def is_valid_email(email):
    """check if it has @"""
    return '@' in email

def sanitize_input(input_value):
    """Sanitize inputs to prevent injection attacks"""
    return re.sub(r'[^a-zA-Z0-9_/-]', '', input_value)

@app.route('/', methods=['GET', 'POST'])
def login():
    """ login pagina"""
    error_message = None
    if request.method == 'POST':
        try:
            connection = connect_db()
            cursor = connection.cursor()

            input_value = request.form["username"]
            password = request.form["password"]

            if is_valid_email(input_value):
                # Invoer is e-mailadres
                query = "SELECT teacher_id, is_admin, teacher_password FROM teachers WHERE email = ?"
            else:
                # Invoer is gebruikersnaam
                query = "SELECT teacher_id, is_admin, teacher_password FROM teachers WHERE username = ?"

            cursor.execute(query, (input_value,))
            result = cursor.fetchone()

            if result is None or not check_password_hash(result[2], password):
                error_message = "Inloggegevens incorrect. De combinatie van het opgegeven e-mailadres en wachtwoord klopt niet, of er bestaat geen account met dit e-mailadres."
            else:
                # Opslaan van teacher_id in sessie
                session['user_id'] = result[0]
                session['is_admin'] = result[1]
                return redirect(url_for('notities_lijst', user_id=sanitize_input(str(session['user_id']))))

        except sqlite3.Error as e:
            print("SQLite error:", e)
            error_message = "Er is een databasefout."

        finally:
            connection.close()

    return render_template('index.html', error_message=error_message)


@app.route('/notities-lijst', methods=['GET', 'POST'])
def notities_lijst():
    """This is the page where all public notes can be seen"""

    subject = request.form.get('subject')
    teacher = request.form.get('teachers')
    title = request.form.get('title')
    note_id = request.form.get('detail') or request.form.get('edit')
    page_number = request.form.get('page_number')

    if page_number is None:
        page_number = 0
    current_page = int(page_number)
    previous_page = current_page - 1
    next_page = current_page + 1

    show_notes_on_page = current_page * 20

    if subject is None:
        subject = ''
    if teacher is None:
        teacher = ''
    if title is None:
        title = ''

    notes = sqlite_queries.get_all_notes(
        subject, teacher, title, show_notes_on_page)
    categories = sqlite_queries.get_categories()
    teachers = sqlite_queries.get_teachers()

    notes_amount = sqlite_queries.get_note_id()
    notes_amount = len(notes_amount)
    page_amount = round(notes_amount / 20)

    hide_next_button = ''
    hide_previous_button = ''
    if current_page == 0:
        hide_previous_button = 'hidden'
    else:
        hide_previous_button = ''
    if current_page == page_amount:
        hide_next_button = 'hidden'
    else:
        hide_next_button = ''

    if note_id is not None:
        if 'detail' in request.form:
            return redirect(f"/details/{sanitize_input(note_id)}")
        elif 'edit' in request.form:
            return redirect(f"/edit/{sanitize_input(note_id)}")
    try:
        if session['user_id'] is not None:

            return render_template('notities.html',
                                   notes=notes,
                                   categories=categories,
                                   teachers=teachers,
                                   current_page=current_page,
                                   previous_page=previous_page,
                                   next_page=next_page,
                                   hide_next_button=hide_next_button,
                                   hide_previous_button=hide_previous_button,

                                   )
    except KeyError:
        return render_template('unauthorized.html')


@app.route('/mijn-notities', methods=['GET', 'POST'])
def my_notes():
    """This is the page where notes of the logged on teacher can be seen"""

    try:
        subject = request.form.get('subject')
        title = request.form.get('title')
        page_number = request.form.get('page_number')
        remove_note_id = request.form.get('remove_note')
        detail_id = request.form.get('detail')
        edit_id = request.form.get('edit')
        change_note_publicity_id = request.form.get('change_public')
        redirect_to_all_notes = request.form.get('redirect_all_notes')

        if subject is None:
            subject = ''
        if title is None:
            title = ''
        categories = sqlite_queries.get_categories()

        if page_number is None:
            page_number = 0
        current_page = int(page_number)
        previous_page = current_page - 1
        next_page = current_page + 1
        show_notes_on_page = current_page * 20
        notes = sqlite_queries.get_my_notes(
            subject, title, show_notes_on_page, session['user_id'])
        note_ids = sqlite_queries.get_note_id()
        notes_amount = len(note_ids)
        page_amount = round(notes_amount / 20)

        hide_next_button = ''
        hide_previous_button = ''
        if current_page == 0:
            hide_previous_button = 'hidden'
        else:
            hide_previous_button = ''
        if current_page == page_amount:
            hide_next_button = 'hidden'
        else:
            hide_next_button = ''

        if redirect_to_all_notes is not None:
            print(redirect_to_all_notes)
            redirect_to_all_notes = None
            return redirect('/notities-lijst')

        if change_note_publicity_id is not None:
            is_public = sqlite_queries.get_note_publicity(
                change_note_publicity_id)
            sqlite_queries.change_publicity(
                change_note_publicity_id, is_public[0])
            return redirect('/mijn-notities')

        if remove_note_id is not None:
            sqlite_queries.delete_note(remove_note_id)
            return redirect('/mijn-notities')

        if edit_id is not None:
            return redirect(f"/edit/{sanitize_input(edit_id)}")

        if detail_id is not None:
            return redirect(f"/details/{sanitize_input(detail_id)}")

        hide_notes = ['hidden', 'public']

        if session['user_id'] is not None:
            return render_template('my_note_list.html', notes=notes,
                                   categories=categories,
                                   current_page=current_page,
                                   previous_page=previous_page,
                                   next_page=next_page,
                                   hide_next_button=hide_next_button,
                                   hide_previous_button=hide_previous_button,
                                   hide_notes=hide_notes
                                   )
    except KeyError:
        return render_template('unauthorized.html')


@app.route('/edit/<note_id>')
def edit_note(note_id):
    """This is the page where notes can be edited

    note_id = int"""

    try:
        title = sqlite_queries.get_note_information('title', note_id)
        content = sqlite_queries.get_note_information('note', note_id)
        source = sqlite_queries.get_note_information('note_source', note_id)

        teacher_id = sqlite_queries.get_note_information('teacher', note_id)
        teacher_id = teacher_id[0]
        teacher = sqlite_queries.get_teacher_name(teacher_id[0])

        category_id = sqlite_queries.get_note_information('category', note_id)
        category_id = category_id[0]
        category = sqlite_queries.get_category_name(category_id[0])

        date_created = sqlite_queries.get_note_information(
            'date_created', note_id)
        questions = sqlite_queries.get_note_information('question', note_id)
        all_categories = sqlite_queries.get_categories()

        # antwoorden tabel moet nog worden aangemaakt

        title = title[0]
        content = content[0]
        source = source[0]
        category = category[0]
        date_created = date_created[0]
        if session['user_id'] == teacher_id[0]:
            return render_template("edit_note.html", title=title,
                                   content=content,
                                   source=source,
                                   teacher=teacher[0],
                                   category=category,
                                   all_categories=all_categories,
                                   date_created=date_created,
                                   questions=questions,
                                   answers=questions)
        else:
            return render_template('unauthorized.html')
    except KeyError:
        return render_template('unauthorized.html')


@app.route('/details/<note_id>')
def note_details(note_id):
    """This is the page where details of a note can be seen"""
    try:
        title = sqlite_queries.get_note_information('title', note_id)
        content = sqlite_queries.get_note_information('note', note_id)
        source = sqlite_queries.get_note_information('note_source', note_id)
        note_publicity = sqlite_queries.get_note_publicity(note_id)
        teacher_id = sqlite_queries.get_note_information('teacher', note_id)
        teacher_id = teacher_id[0]
        teacher = sqlite_queries.get_teacher_name(teacher_id[0])

        category_id = sqlite_queries.get_note_information('category', note_id)
        category_id = category_id[0]
        category = sqlite_queries.get_category_name(category_id[0])

        date_created = sqlite_queries.get_note_information(
            'date_created', note_id)
        questions = sqlite_queries.get_note_information('question', note_id)
        # antwoorden tabel moet nog worden aangemaakt

        title = title[0]
        content = content[0]
        source = source[0]
        category = category[0]
        date_created = date_created[0]
        if session['user_id'] == teacher_id[0] or note_publicity[0] is True:
            return render_template("details.html", title=title,
                                   content=content,
                                   source=source,
                                   teacher=teacher[0],
                                   category=category,
                                   date_created=date_created,
                                   questions=questions,
                                   answers=questions,
                                   note_id=note_id)
        else:
            return render_template('unauthorized.html')
    except KeyError:
        return render_template('unauthorized.html')


@app.route("/vraag-genereren/<note_id>")
def vraag_genereren(note_id):
    """ vragen genereren"""
    test_gpt = TestGPT(openai.api_key)
    content = sqlite_queries.get_note_information('note', note_id)
    content = content[0][0]
    question = test_gpt.generate_open_question(content)
    sqlite_queries.create_question(note_id, question)

    return note_details(note_id)


@app.route("/notitie-maken", methods=['GET', 'POST'])
def notitie_maken():
    """notitie maken route"""
    teachers = sqlite_queries.get_teacher_id()
    categories = sqlite_queries.get_category_id()

    title = request.form.get('title')

    return render_template('notitiemaken.html', categories=categories, teachers=teachers)


@app.route("/notitie-maken/opslaan", methods=['GET', 'POST'])
def notitie_opslaan():
    """notitie opslaan"""
    title = request.form['title']
    note_source = request.form['source']
    # is_public = request.form ['is_public']
    teacher_id = request.form['teachers']
    category_id = request.form['subject']
    note = request.form['note']

    sqlite_queries.create_note(
        title, note_source, teacher_id, category_id, note)

    return redirect(url_for("notities_lijst"))


def mijn_notities():
    return "Notities"


def haal_gebruikersgegevens_op():
    """haalt de benodigde gegevens op"""
    if 'user_id' in session:
        user_id = session['user_id']

        connection = sqlite3.connect('databases/testgpt.db')
        cursor = connection.cursor()

        cursor.execute('''
            SELECT teachers.display_name, teachers.username, teachers.email, categories.omschrijving
            FROM teachers
            LEFT JOIN categories ON teachers.teacher_id = categories.category_id
            WHERE teachers.teacher_id = ?
        ''', (user_id,))

        gebruikersgegevens = dict(
            zip([column[0] for column in cursor.description], cursor.fetchone()))

        connection.close()

        return gebruikersgegevens

    return None


@app.route("/mijn-account")
def instellingen():
    """rederict naar mijn account"""
    gebruikersgegevens = haal_gebruikersgegevens_op()
    return render_template('mijnaccount.html', **gebruikersgegevens)


@app.route('/logout')
def logout():
    """user logt uit functie"""
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/update_user', methods=['POST'])
def update_user():
    if 'user_id' in session:
        user_id = session['user_id']

        connection = sqlite3.connect('databases/testgpt.db')
        cursor = connection.cursor()

        new_email = request.form['new_email']

        # Update de e-mail van de teacher
        cursor.execute('''
            UPDATE teachers
            SET email = ?
            WHERE teacher_id = ?
        ''', (new_email, user_id))

        connection.commit()
        connection.close()

    return redirect(url_for('instellingen'))


@app.route('/categorie')
def categorie():
    """ redirect naar categories"""
    categories = sqlite_queries.get_categories()
    return render_template('categorie.html', categories=categories)


@app.route('/add_category', methods=['POST'])
def add_category():
    """category toevoegen"""
    if request.method == 'POST':
        new_description = request.form.get('new_omschrijving')

        if new_description:
            connection = connect_db()
            cursor = connection.cursor()

            try:
                # nieuwe categorie
                cursor.execute(
                    "INSERT INTO categories (omschrijving) VALUES (?)", (new_description,))
                connection.commit()
            except sqlite3.Error as e:
                print("SQLite error:", e)

                session['error_message'] = "Er is een fout opgetreden bij\
                      het toevoegen van de nieuwe omschrijving."
            finally:
                connection.close()

    return redirect(url_for('categorie'))


@app.route('/admin')
def admin():
    try:
        if 'is_admin' in session and session['is_admin']:
            sqlite_queries = Testgtp(DATABASE_FILE)
            teachers = sqlite_queries.get_teachers()
            return render_template('admin.html', teachers=teachers)
        else:
            return render_template('unathorized.html')
    except KeyError:
        return render_template('unathorized.html')


@app.route('/admin/add_teacher', methods=['POST'])
def add_teacher():
    if request.method == 'POST':
        display_name = request.form.get('display_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = generate_password_hash(request.form.get('password'))  # Hash het wachtwoord
        is_admin = int(request.form.get('is_admin', 0))
        sqlite_queries = Testgtp(DATABASE_FILE)
        sqlite_queries.insert_teacher(display_name, username, email, password, is_admin)

    return redirect(url_for('admin'))


@app.route('/admin/remove_teacher/<int:teacher_id>')
def remove_teacher(teacher_id):
    teacher_id = int(teacher_id)
    sqlite_queries = Testgtp(DATABASE_FILE)
    sqlite_queries.remove_teacher(teacher_id)
    return redirect(url_for('admin'))


@app.route('/edit_teacher/<int:teacher_id>', methods=['GET', 'POST'])
def edit_teacher(teacher_id):
    sqlite_queries = Testgtp(DATABASE_FILE)
    teacher_info = sqlite_queries.get_teacher_information(teacher_id)
    if request.method == 'POST':
        new_display_name = request.form['new_display_name']
        new_username = request.form['new_username']
        new_email = request.form['new_email']
        new_password = generate_password_hash(request.form['new_password'])  # Hash het nieuwe wachtwoord
        is_admin = 'is_admin' in request.form

        sqlite_queries.update_teacher(teacher_id, new_display_name, new_username, new_email, new_password, is_admin)

        return redirect(url_for('admin'))

    return render_template('edit_teacher.html', teacher_info=teacher_info)


@app.route('/generate')
def generate():

    return render_template('generate.html')


@app.route('/export_csv/<note_id>')
def export_csv(note_id):
    """exporteren naar csv"""
    title = sqlite_queries.get_note_information('title', note_id)
    teacher_id = sqlite_queries.get_note_information('teacher', note_id)[0][0]
    source = sqlite_queries.get_note_information('note_source', note_id)
    date_created = sqlite_queries.get_note_information('date_created', note_id)
    content = sqlite_queries.get_note_information('note', note_id)
    
    # Haal alle vragen op die bij de notitie horen
    questions = sqlite_queries.get_note_questions(note_id)

    # Haal de display_name op
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("SELECT display_name FROM teachers WHERE teacher_id = ?", (teacher_id,))
    teacher_display_name = cursor.fetchone()[0]
    connection.close()

    # Creëer je bestandje
    csv_data = [['Title', 'Teacher', 'Source', 'Date Created', 'Content', 'Question']]
    # Voeg alle vragen toe aan de CSV
    for question in questions:
        csv_data.append([title[0][0], teacher_display_name, source[0][0],\
                          date_created[0][0], content[0][0], question[0]])
    
    response = Response()
    response.headers["Content-Disposition"] = f"attachment; filename={title[0][0]}.csv"
    response.headers["Content-Type"] = "text/csv"

    # Schrijf de gegevens naar je bestandje
    csv_writer = csv.writer(response.stream)
    csv_writer.writerows(csv_data)

    return response


if __name__ == "__main__":
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1'])
