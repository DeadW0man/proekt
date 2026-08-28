from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from repository.repository import get_user_by_session_id
from schemas.schemas import UserRegister, UserLogin, BookCreate, ShareCreate, ShareReturn
import services.services as service

api_bp = Blueprint('api', __name__)


def validate_session_id(session_id):
    if not session_id:
        return False
    return get_user_by_session_id(session_id) is not None


def is_auth_valid():
    session_id = request.headers.get('SessionID')
    if session_id:
        return validate_session_id(session_id)
    return False


def get_current_user():
    session_id = request.headers.get('SessionID')
    if not session_id:
        return None
    return get_user_by_session_id(session_id)


@api_bp.route('/', methods=['GET'])
def index():
    return 'Hello from Solaris app'


@api_bp.route('/register', methods=['POST'])
def register():
    try:
        data = UserRegister(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400
    res, status = service.register_user(data.email, data.name, data.password)
    return (jsonify(res) if isinstance(res, dict) else res), status


@api_bp.route('/login', methods=['POST'])
def login():
    try:
        data = UserLogin(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400
    res, status = service.login_user(data.email, data.password)
    return (jsonify(res) if isinstance(res, dict) else res), status


@api_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    res, status = service.get_user(user_id)
    return (jsonify(res) if isinstance(res, dict) else res), status


@api_bp.route('/users', methods=['GET'])
def get_users():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    res, status = service.get_all_users()
    return jsonify(res), status


@api_bp.route('/book', methods=['POST'])
def add_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    try:
        data = BookCreate(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400
    user = get_current_user()
    res, status = service.add_book(user[0], data.title, data.author, data.release_year)
    return (jsonify(res) if isinstance(res, dict) else res), status


@api_bp.route('/books', methods=['GET'])
def get_books():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    res, status = service.get_all_books()
    return jsonify(res), status


@api_bp.route('/book/<int:book_id>', methods=['GET'])
def get_book(book_id):
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    res, status = service.get_book(book_id)
    return (jsonify(res) if isinstance(res, dict) else res), status


@api_bp.route('/share', methods=['POST'])
def share_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    try:
        data = ShareCreate(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400
    user = get_current_user()
    res, status = service.share_book(user[0], data.book_id, data.taker_id, data.final_date)
    return (jsonify(res) if isinstance(res, dict) else res), status


@api_bp.route('/return', methods=['POST'])
def return_book():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    try:
        data = ShareReturn(**request.json)
    except ValidationError as e:
        return jsonify(e.errors()), 400
    user = get_current_user()
    res, status = service.return_book(user[0], data.share_id)
    return (jsonify(res) if isinstance(res, dict) else res), status


@api_bp.route('/shares', methods=['GET'])
def get_shares():
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    res, status = service.get_all_shares()
    return jsonify(res), status


@api_bp.route('/book/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    if not is_auth_valid():
        return 'Request denied, invalid session', 403
    res, status = service.delete_book(book_id)
    return (jsonify(res) if isinstance(res, dict) else res), status
