"""Smoke-тест приложения после реструктуризации (app/api/db/...)."""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'library-main')
os.environ['SOLARIS_SQLITE_PATH'] = os.path.join(ROOT, 'smoke_dev.db')
if os.path.exists(os.environ['SOLARIS_SQLITE_PATH']):
    os.remove(os.environ['SOLARIS_SQLITE_PATH'])

sys.path.insert(0, ROOT)

from db.db import prepare_tables  # noqa: E402
from app.main import solaris_app  # noqa: E402

PASS = 0
FAIL = 0


def check(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f'  OK   {name}')
    else:
        FAIL += 1
        print(f'  FAIL {name} {detail}')


with solaris_app.app_context():
    prepare_tables()

client = solaris_app.test_client()

# --- index ---
r = client.get('/')
check('GET / -> Hello from Solaris app', r.status_code == 200 and b'Solaris' in r.data, f'got {r.status_code}')

# --- регистрация/логин ---
r = client.post('/register', json={'email': 'a@test.ru', 'name': 'Alice', 'password': 'pass1'})
check('register Alice -> 201', r.status_code == 201, f'got {r.status_code}, {r.data[:80]}')

r = client.post('/register', json={'email': 'a@test.ru', 'name': 'Alice', 'password': 'pass1'})
check('duplicate register -> 400', r.status_code == 400, f'got {r.status_code}')

r = client.post('/register', json={'email': 'b@test.ru', 'name': 'Bob', 'password': 'pass2'})
check('register Bob -> 201', r.status_code == 201, f'got {r.status_code}')

r = client.post('/register', json={'name': 'NoEmail'})
check('register missing fields -> 400 (не 500)', r.status_code == 400, f'got {r.status_code}')

r = client.post('/login', json={'email': 'a@test.ru', 'password': 'pass1'})
check('login Alice -> 200', r.status_code == 200, f'got {r.status_code}, {r.data[:100]}')
session_a = r.get_json()['session_id']
check('session_id число', isinstance(session_a, int), str(r.get_json()))

r = client.post('/login', json={'email': 'a@test.ru', 'password': 'wrong'})
check('login wrong password -> 403', r.status_code == 403, f'got {r.status_code}')

r = client.post('/login', json={'email': 'b@test.ru', 'password': 'pass2'})
session_b = r.get_json()['session_id']
check('login Bob -> 200', r.status_code == 200, f'got {r.status_code}')

h_a = {'SessionID': str(session_a)}
h_b = {'SessionID': str(session_b)}

r = client.get('/users')
check('GET /users без сессии -> 403', r.status_code == 403, f'got {r.status_code}')

r = client.get('/user/1', headers=h_a)
check('GET /user/1 -> 200', r.status_code == 200 and r.get_json().get('name') == 'Alice', f'got {r.status_code}')

# --- книги ---
r = client.post('/book', headers=h_a,
                json={'title': 'Мастер и Маргарита', 'author': 'Булгаков', 'release_year': 1967})
check('add book Alice -> 201', r.status_code == 201, f'got {r.status_code}')

r = client.post('/book', headers=h_a, json={'title': 'x'})
check('add book missing fields -> 400', r.status_code == 400, f'got {r.status_code}')

r = client.get('/books', headers=h_a)
body = r.get_json()
check('GET /books -> 200 и ключ "books"', r.status_code == 200 and 'books' in body, f'got {body}')
book = body['books'][0]
check('ключ "release_year" без двоеточия', 'release_year' in book and 'release_year:' not in book, f'got {book}')
check('данные книги', book.get('author') == 'Булгаков', f'got {book}')

r = client.get('/book/1', headers=h_a)
check('GET /book/1 -> 200, release_year=1967', r.get_json().get('release_year') == 1967, f'got {r.status_code}')

r = client.get('/book/999', headers=h_a)
check('GET /book/999 -> 404', r.status_code == 404, f'got {r.status_code}')

# --- шеринг/возврат ---
r = client.post('/share', headers=h_a,
                json={'book_id': 1, 'taker_id': 2, 'final_date': '2026-12-31'})
check('share Alice -> 200', r.status_code == 200, f'got {r.status_code}, {r.data[:80]}')
share_id = r.get_json()['share_id']

r = client.post('/share', headers=h_a,
                json={'book_id': 1, 'taker_id': 999, 'final_date': '2026-12-31'})
check('share на несуществующего пользователя -> 404', r.status_code == 404, f'got {r.status_code}')

r = client.get('/shares', headers=h_a)
body = r.get_json()
sh = body['shares'][0]
check('GET /shares, ключ "taker_id" без двоеточия', 'taker_id' in sh and 'taker_id:' not in sh, f'got {sh}')

r = client.post('/return', headers=h_b, json={'share_id': share_id})
check("return не giver'ом -> 403", r.status_code == 403, f'got {r.status_code}')

r = client.post('/return', headers=h_a, json={'share_id': share_id})
check('return Alice -> 200', r.status_code == 200, f'got {r.status_code}')

# --- удаление ---
r = client.delete('/book/1', headers=h_a)
check('delete своей книги -> 200', r.status_code == 200, f'got {r.status_code}')

r = client.get('/book/1', headers=h_a)
check('книга удалена (GET -> 404)', r.status_code == 404, f'got {r.status_code}')

# --- SQL-инъекция: блокируется валидацией, приложение живо ---
r = client.post('/login', json={'email': "a@test.ru\" OR 1=1 --", 'password': "x\" OR 1=1 --"})
check('инъекция в login -> 400 (валидация)', r.status_code == 400, f'got {r.status_code}')

r = client.post('/register',
                json={'email': "evil@test.ru\"); DROP TABLE users;--", 'name': 'Evil', 'password': 'x'})
check('инъекция в register -> 400 (валидация)', r.status_code == 400, f'got {r.status_code}')

r = client.post('/login', json={'email': 'a@test.ru', 'password': 'pass1'})
check('после инъекций логин работает -> 200', r.status_code == 200, f'got {r.status_code}')

print(f'\nИтого: {PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
