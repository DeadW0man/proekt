from flask import Flask, g, request, jsonify
from os import getenv
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

#####################

solaris_app = Flask('solaris')  # Создаём экземпляр приложения
db_path = getenv('SOLARIS_SQLITE_PATH', 'dev.db')  # Где лежит база данных

#####################

def get_db():
    """Возвращает подключение к БД (одно на запрос) и закрывает его после ответа."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row      # обращение к колонкам по имени: row['id']
        db.execute("PRAGMA foreign_keys = ON;")  # реально включаем внешние ключи
    return db


@solaris_app.teardown_appcontext
def close_db(exception):
    """Гарантированно закрываем подключение после обработки запроса."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

#####################

def prepare_tables() -> None:
    # Важно: books создаётся ДО shares, потому что shares ссылается на books
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(128) NOT NULL,
            email VARCHAR(128) NOT NULL UNIQUE,
            password VARCHAR(128) NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            user_id INTEGER NOT NULL,
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(128) NOT NULL,
            author VARCHAR(128) NOT NULL,
            release_year INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            giver_id INTEGER NOT NULL,
            taker_id INTEGER NOT NULL,
            final_date VARCHAR(32),
            FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
            FOREIGN KEY (giver_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (taker_id) REFERENCES users (id) ON DELETE CASCADE
        );
    """)


def run_app() -> None:
    solaris_app.run(
        host=getenv('SOLARIS_HOST', '0.0.0.0'),
        port=int(getenv('SOLARIS_PORT', '5000')),
        debug=getenv('SOLARIS_DEBUG', '1') == '1'  # в проде выставить 0
    )

#####################

# Все запросы — параметризованные (знак ?): пользовательский ввод никогда
# не подставляется в строку SQL, поэтому SQL-инъекции невозможны.

def get_user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()


def get_user_by_email(email):
    return get_db().execute("SELECT * FROM users WHERE email = ?;", (email,)).fetchone()


def get_user_by_session_id(session_id):
    row = get_db().execute(
        "SELECT user_id FROM sessions WHERE session_id = ?;", (session_id,)
    ).fetchone()
    if row is None:
        return None
    return get_user_by_id(row['user_id'])


def validate_session_id(session_id):
    return get_user_by_session_id(session_id) is not None


####################

def is_auth_valid():
    session_id = request.headers.get('SessionID')
    if session_id:
        return validate_session_id(session_id)
    return False


def get_current_user():
    """Возвращает пользователя по заголовку SessionID (или None)."""
    session_id = request.headers.get('SessionID')
    if not session_id:
        return None
    return get_user_by_session_id(session_id)

####################

def get_book_by_id(book_id):
    return get_db().execute("SELECT * FROM books WHERE id = ?;", (book_id,)).fetchone()


def get_share_by_id(share_id):
    return get_db().execute("SELECT * FROM shares WHERE id = ?;", (share_id,)).fetchone()


####################

def user_row_to_dict(user_row):
    return {
        'id': user_row['id'],
        'name': user_row['name'],
        'email': user_row['email'],
    }


def book_row_to_dict(book_row):
    return {
        'id': book_row['id'],
        'title': book_row['title'],
        'author': book_row['author'],
        'release_year': book_row['release_year'],  # было: 'release_year:' (опечатка)
        'owner_id': book_row['owner_id'],
    }


def share_row_to_dict(share_row):
    return {
        'id': share_row['id'],
        'book_id': share_row['book_id'],
        'giver_id': share_row['giver_id'],
        'taker_id': share_row['taker_id'],  # было: 'taker_id:' (опечатка)
        'final_date': share_row['final_date'],
    }

#####################

@solaris_app.route('/', methods=['GET'])
def index():
    return 'Hello from Solaris app'


@solaris_app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    name = data.get('name')
    password = data.get('password')
    if not email or not name or not password:
        return 'email, name and password are required', 400

    if get_user_by_email(email) is not None:
        return 'User already exists', 400

    db = get_db()
    with db:  # commit после успешного INSERT
        db.execute(
            "INSERT INTO users (email, name, password) VALUES (?, ?, ?);",
            (email, name, generate_password_hash(password)),  # пароль храним в виде хэша
        )
    return 'Created', 201


@solaris_app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return 'email and password are required', 400

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user['password'], password):
        return 'Доступ запрещен', 403

    db = get_db()
    with db:
        cursor = db.execute("INSERT INTO sessions (user_id) VALUES (?);", (user['id'],))
        session_id = cursor.lastrowid  # читаем ДО закрытия курсора/коммита

    return jsonify({'user_id': user['id'], 'session_id': session_id}), 200


@solaris_app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    user = get_user_by_id(user_id)
    if user is None:
        return 'User not found', 404
    return jsonify(user_row_to_dict(user)), 200


@solaris_app.route('/users', methods=['GET'])
def get_users():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    users = get_db().execute("SELECT * FROM users;").fetchall()
    return jsonify({'users': [user_row_to_dict(u) for u in users]}), 200


@solaris_app.route('/book', methods=['POST'])
def add_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    owner = get_current_user()

    data = request.get_json(silent=True) or {}
    title = data.get('title')
    author = data.get('author')
    release_year = data.get('release_year')
    if not title or not author or release_year is None:
        return 'title, author and release_year are required', 400
    try:
        release_year = int(release_year)
    except (TypeError, ValueError):
        return 'release_year must be an integer', 400

    db = get_db()
    with db:
        db.execute(
            "INSERT INTO books (title, author, release_year, owner_id) VALUES (?, ?, ?, ?);",
            (title, author, release_year, owner['id']),
        )
    return 'Created', 201


@solaris_app.route('/books', methods=['GET'])
def get_books():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    books = get_db().execute("SELECT * FROM books;").fetchall()
    return jsonify({'books': [book_row_to_dict(b) for b in books]}), 200


@solaris_app.route('/book/<int:book_id>', methods=['GET'])
def get_book(book_id):
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    book = get_book_by_id(book_id)
    if book is None:
        return 'Book not found', 404
    return jsonify(book_row_to_dict(book)), 200


@solaris_app.route('/share', methods=['POST'])
def share_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    giver = get_current_user()

    data = request.get_json(silent=True) or {}
    book_id = data.get('book_id')
    taker_id = data.get('taker_id')
    final_date = data.get('final_date')
    if book_id is None or taker_id is None or final_date is None:
        return 'book_id, taker_id and final_date are required', 400

    if get_user_by_id(taker_id) is None:
        return 'Taker not found', 404
    book = get_book_by_id(book_id)
    if book is None:
        return 'Book not found', 404
    if book['owner_id'] != giver['id']:
        return 'You are not an owner of the book', 403  # нельзя шерить чужую книгу

    db = get_db()
    with db:
        cursor = db.execute(
            "INSERT INTO shares (book_id, giver_id, taker_id, final_date) VALUES (?, ?, ?, ?);",
            (book_id, giver['id'], taker_id, final_date),
        )
        share_id = cursor.lastrowid

    return jsonify({'share_id': share_id}), 200


@solaris_app.route('/return', methods=['POST'])
def return_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    user = get_current_user()

    data = request.get_json(silent=True) or {}
    share_id = data.get('share_id')
    if share_id is None:
        return 'share_id is required', 400

    share = get_share_by_id(share_id)
    if share is None:
        return 'Share not found', 404
    if share['giver_id'] != user['id']:
        return 'You are not an owner of the book', 403

    db = get_db()
    with db:
        db.execute("DELETE FROM shares WHERE id = ?;", (share_id,))
    return 'Book was returned', 200


@solaris_app.route('/shares', methods=['GET'])
def get_shares():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    shares = get_db().execute("SELECT * FROM shares;").fetchall()
    return jsonify({'shares': [share_row_to_dict(s) for s in shares]}), 200


@solaris_app.route('/book/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    if not is_auth_valid():
        return 'Request denied, invalid session', 403

    user = get_current_user()

    book = get_book_by_id(book_id)
    if book is None:
        return 'Book not found', 404
    if book['owner_id'] != user['id']:
        return 'You are not an owner of the book', 403  # нельзя удалять чужую книгу

    db = get_db()
    with db:
        # сначала удаляем шеринги книги (иначе внешний ключ не даст удалить)
        db.execute("DELETE FROM shares WHERE book_id = ?;", (book_id,))
        db.execute("DELETE FROM books WHERE id = ?;", (book_id,))
    return 'The book was removed', 200


#####################

if __name__ == '__main__':
    with solaris_app.app_context():
        prepare_tables()
    run_app()
