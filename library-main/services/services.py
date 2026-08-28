import repository.repository as repo
from schemas.schemas import BookResponse, ShareResponse, UserResponse


def user_row_to_dict(row):
    if not row:
        return None
    return UserResponse(id=row[0], name=row[1], email=row[2]).model_dump()


def book_row_to_dict(row):
    if not row:
        return None
    return BookResponse(id=row[0], title=row[1], author=row[2], release_year=row[3], owner_id=row[4]).model_dump()


def share_row_to_dict(row):
    if not row:
        return None
    return ShareResponse(id=row[0], book_id=row[1], giver_id=row[2], taker_id=row[3], final_date=row[4]).model_dump()


def register_user(email, name, password):
    if repo.get_user_by_email(email):
        return "User already exists", 400
    repo.create_user(name, email, password)
    return "Created", 201


def login_user(email, password):
    user = repo.get_user_by_credentials(email, password)
    if not user:
        return "Доступ запрещен", 403
    session_id = repo.create_session(user[0])
    return {"user_id": user[0], "session_id": session_id}, 200


def get_user(user_id):
    user = repo.get_user_by_id(user_id)
    if not user:
        return "User not found", 404
    return user_row_to_dict(user), 200


def get_all_users():
    users = repo.get_all_users()
    return {"users": [user_row_to_dict(u) for u in users]}, 200


def add_book(owner_id, title, author, release_year):
    repo.create_book(title, author, release_year, owner_id)
    return "Created", 201


def get_all_books():
    books = repo.get_all_books()
    return {"books": [book_row_to_dict(b) for b in books]}, 200


def get_book(book_id):
    book = repo.get_book_by_id(book_id)
    if not book:
        return "Book not found", 404
    return book_row_to_dict(book), 200


def delete_book(book_id):
    repo.delete_book(book_id)
    return "The book was removed", 200


def share_book(giver_id, book_id, taker_id, final_date):
    if not repo.get_user_by_id(taker_id):
        return "Taker not found", 404
    if not repo.get_book_by_id(book_id):
        return "Book not found", 404

    share_id = repo.create_share(book_id, giver_id, taker_id, final_date)
    return {"share_id": share_id}, 200


def return_book(giver_id, share_id):
    share = repo.get_share_by_id(share_id)
    if not share:
        return "Share not found", 404
    if share[2] != giver_id:
        return "You are not an owner of the book", 403

    repo.delete_share(share_id)
    return "Book was returned", 200


def get_all_shares():
    shares = repo.get_all_shares()
    return {"shares": [share_row_to_dict(s) for s in shares]}, 200
