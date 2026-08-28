from db.db import get_db


def get_user_by_id(user_id):
    cursor = get_db().cursor()
    user = cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
    cursor.close()
    return user


def get_user_by_email(email):
    cursor = get_db().cursor()
    user = cursor.execute("SELECT * FROM users WHERE email = ?;", (email,)).fetchone()
    cursor.close()
    return user


def get_user_by_credentials(email, password):
    cursor = get_db().cursor()
    user = cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?;", (email, password)).fetchone()
    cursor.close()
    return user


def create_user(name, email, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?);", (name, email, password))
    db.commit()
    cursor.close()


def create_session(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO sessions (user_id) VALUES (?);", (user_id,))
    session_id = cursor.lastrowid
    db.commit()
    cursor.close()
    return session_id


def get_user_by_session_id(session_id):
    cursor = get_db().cursor()
    user_id_row = cursor.execute("SELECT user_id FROM sessions WHERE session_id = ?;", (session_id,)).fetchone()
    cursor.close()
    if user_id_row is None:
        return None
    return get_user_by_id(user_id_row[0])


def get_all_users():
    cursor = get_db().cursor()
    users = cursor.execute("SELECT * FROM users;").fetchall()
    cursor.close()
    return users


def get_book_by_id(book_id):
    cursor = get_db().cursor()
    book = cursor.execute("SELECT * FROM books WHERE id = ?;", (book_id,)).fetchone()
    cursor.close()
    return book


def get_all_books():
    cursor = get_db().cursor()
    books = cursor.execute("SELECT * FROM books;").fetchall()
    cursor.close()
    return books


def create_book(title, author, release_year, owner_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO books(title, author, release_year, owner_id) VALUES (?, ?, ?, ?);",
                   (title, author, release_year, owner_id))
    db.commit()
    cursor.close()


def delete_book(book_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM books WHERE id = ?;", (book_id,))
    db.commit()
    cursor.close()


def get_share_by_id(share_id):
    cursor = get_db().cursor()
    share = cursor.execute("SELECT * FROM shares WHERE id = ?;", (share_id,)).fetchone()
    cursor.close()
    return share


def get_all_shares():
    cursor = get_db().cursor()
    shares = cursor.execute("SELECT * FROM shares;").fetchall()
    cursor.close()
    return shares


def create_share(book_id, giver_id, taker_id, final_date):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO shares(book_id, giver_id, taker_id, final_date) VALUES (?, ?, ?, ?);",
                   (book_id, giver_id, taker_id, final_date))
    share_id = cursor.lastrowid
    db.commit()
    cursor.close()
    return share_id


def delete_share(share_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM shares WHERE id = ?;", (share_id,))
    db.commit()
    cursor.close()
