from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr


class BookCreate(BaseModel):
    title: str
    author: str
    release_year: int


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    release_year: int
    owner_id: int


class ShareCreate(BaseModel):
    book_id: int
    taker_id: int
    final_date: str


class ShareReturn(BaseModel):
    share_id: int


class ShareResponse(BaseModel):
    id: int
    book_id: int
    giver_id: int
    taker_id: int
    final_date: str
