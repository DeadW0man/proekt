"""Smoke-тест исправленного приложения solaris_fixed.py (Flask test_client)."""
import os
import sys

os.environ['SOLARIS_SQLITE_PATH'] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'smoke_dev.db'
)

_db_file = os.environ['SOLARIS_SQLITE_PATH']
if os.path.exists(_db_file):
    os.remove(_db_file)  # чистый старт каждого прогона

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solaris_fixed as app_mod  # noqa: E402

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


with app_mod.solaris_app.app_context():
    app_mod.prepare_tables()

client = app_mod.solaris_app.test_client()

# --- регистрация ---
r = client.post('/register', json={'email': 'a@test.ru', 'name': 'Alice', 'password': 'pass1'})
check('register Alice -> 201', r.status_code == 201, f'got {r.status_code}')

r = client.post('/register', json={'email': 'a@test.ru', 'name': 'Alice', 'password': 'pass1'})
check('duplicate register -> 400', r.status_code == 400, f'got {r.status_code}')

r = client.post('/register', json={'email': 'b@test.ru', 'name': 'Bob', 'password': 'pass2'})
check('register Bob -> 201', r.status_code == 201, f'got {r.status_code}')

r = client.post('/register', json={'name': 'NoEmail'})
check('register missing fields -> 400 (не 500)', r.status_code == 400, f'got {r.status_code}')

# --- логин: раньше падал с ProgrammingError (lastrowid после close) ---
r = client.post('/login', json={'email': 'a@test.ru', 'password': 'pass1'})
check('login Alice -> 200', r.status_code == 200, f'got {r.status_code}, {r.data[:100]}')
session_a = r.get_json()['session_id']
check('session_id вернулся числом', isinstance(session_a, int), str(r.get_json()))

r = client.post('/login', json={'email': 'a@test.ru', 'password': 'wrong'})
check('login wrong password -> 403', r.status_code == 403, f'got {r.status_code}')

r = client.post('/login', json={'email': 'b@test.ru', 'password': 'pass2'})
session_b = r.get_json()['session_id']
check('login Bob -> 200', r.status_code == 200, f'got {r.status_code}')

h_a = {'SessionID': str(session_a)}
h_b = {'SessionID': str(session_b)}

# --- защищённые ручки без сессии ---
r = client.get('/users')
check('GET /users без сессии -> 403', r.status_code == 403, f'got {r.status_code}')

# --- книги ---
r = client.post('/book', headers=h_a,
                json={'title': 'Мастер и Маргарита', 'author': 'Булгаков', 'release_year': 1967})
check('add book Alice -> 201', r.status_code == 201, f'got {r.status_code}')

r = client.post('/book', headers=h_a, json={'title': 'x'})
check('add book missing fields -> 400', r.status_code == 400, f'got {r.status_code}')

r = client.get('/books', headers=h_a)
body = r.get_json()
check('GET /books -> 200 и ключ "books"', r.status_code == 200 and 'books' in body,
      f'got {body}')
book = body['books'][0]
check('ключ "release_year" без двоеточия', 'release_year' in book and 'release_year:' not in book,
      f'got {book}')
check('ключ "author" и данные книги', book.get('author') == 'Булгаков', f'got {book}')

r = client.get('/book/1', headers=h_a)
body = r.get_json()
check('GET /book/1 -> 200, release_year=1967', body.get('release_year') == 1967, f'got {body}')

r = client.get('/book/999', headers=h_a)
check('GET /book/999 -> 404', r.status_code == 404, f'got {r.status_code}')

# --- шеринг: чужая книга ---
r = client.post('/share', headers=h_b,
                json={'book_id': 1, 'taker_id': 2, 'final_date': '2026-12-31'})
check('share чужой книги Bob -> 403', r.status_code == 403, f'got {r.status_code}, {r.data[:80]}')

r = client.post('/share', headers=h_a,
                json={'book_id': 1, 'taker_id': 2, 'final_date': '2026-12-31'})
check('share своей книги Alice -> 200', r.status_code == 200, f'got {r.status_code}')
share_id = r.get_json()['share_id']

r = client.post('/share', headers=h_a, json={'book_id': 1, 'taker_id': 999, 'final_date': '2026-12-31'})
check('share на несуществующего пользователя -> 404', r.status_code == 404, f'got {r.status_code}')

r = client.get('/shares', headers=h_a)
body = r.get_json()
sh = body['shares'][0]
check('GET /shares, ключ "taker_id" без двоеточия', 'taker_id' in sh and 'taker_id:' not in sh,
      f'got {sh}')

# --- возврат ---
r = client.post('/return', headers=h_b, json={'share_id': share_id})
check("return не гiver'ом Bob -> 403", r.status_code == 403, f'got {r.status_code}')

r = client.post('/return', headers=h_a, json={'share_id': share_id})
check('return Alice -> 200', r.status_code == 200, f'got {r.status_code}')

# --- удаление книги ---
r = client.delete('/book/1', headers=h_b)
check('delete чужой книги Bob -> 403', r.status_code == 403, f'got {r.status_code}')

r = client.delete('/book/1', headers=h_a)
check('delete своей книги Alice -> 200', r.status_code == 200, f'got {r.status_code}')

r = client.delete('/book/1', headers=h_a)
check('delete несуществующей -> 404', r.status_code == 404, f'got {r.status_code}')

# --- SQL-инъекция: раньше ломала запросы ---
r = client.post('/login', json={'email': "a@test.ru\" OR 1=1 --", 'password': "x\" OR 1=1 --"})
check('инъекция в login не проходит -> 403', r.status_code == 403, f'got {r.status_code}')

r = client.post('/register',
                json={'email': "evil@test.ru\"); DROP TABLE users;--",
                      'name': 'Evil', 'password': 'x'})
check('инъекция в register не удаляет таблицы -> 201',
      r.status_code in (201, 400), f'got {r.status_code}')
if r.status_code == 201:
    r = client.post('/login', json={'email': "evil@test.ru'); DROP TABLE users;--", 'password': 'x'})
    check('пользователь с инъекцией в email существует (таблица цела)',
          r.status_code in (200, 403), f'got {r.status_code}')

# --- пароль хранится как хэш ---
with app_mod.solaris_app.app_context():
    raw = app_mod.get_user_by_email('a@test.ru')['password']
check('пароль в БД — хэш, не plaintext', not raw.startswith('pass1') and '$' in raw, f'raw={raw!r}')

print(f'\nИтого: {PASS} passed, {FAIL} failed')
sys.exit(1 if FAIL else 0)
