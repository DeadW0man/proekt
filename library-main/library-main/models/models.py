from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    password: str


class Session(BaseModel):
    session_id: Optional[int] = None
    user_id: int


class Book(BaseModel):
    id: Optional[int] = None
    title: str
    author: str
    release_year: int
    owner_id: int


class Share(BaseModel):
    id: Optional[int] = None
    book_id: int
    giver_id: int
    taker_id: int
    final_date: str
