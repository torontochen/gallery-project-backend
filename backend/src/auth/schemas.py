import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# from src.books.schemas import Book
# from src.reviews.schemas import ReviewModel


class UserCreateModel(BaseModel):
    first_name: str = Field(max_length=25)
    last_name: str = Field(max_length=25)
    username: str = Field(max_length=8)
    email: str = Field(max_length=40)
    password: str = Field(min_length=6)
    role: str = Field(default="user")

    # model_config = {
    #     "json_schema_extra": {
    #         "example": {
    #             "first_name": "John",
    #             "last_name": "Doe",
    #             "username": "johndoe",
    #             "email": "johndoe123@co.com",
    #             "password": "testpass123",
    #         }
    #     }
    # }


class UserModel(BaseModel):
    uid: uuid.UUID
    username: str
    email: str
    first_name: str
    last_name: str
    is_verified: bool
    hashed_password: str = Field(exclude=True)
    role: str
    bio: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    delivery_address: Optional[str] = None
    phone_number: Optional[str] = None



# class UserBooksModel(UserModel):
#     books: List[Book]
#     reviews: List[ReviewModel]


class UserLoginModel(BaseModel):
    email: str = Field(max_length=40)
    password: str = Field(min_length=6)


class EmailModel(BaseModel):
    addresses : List[str]


class PasswordResetRequestModel(BaseModel):
    email: str


class PasswordResetConfirmModel(BaseModel):
    new_password: str
    confirm_new_password: str