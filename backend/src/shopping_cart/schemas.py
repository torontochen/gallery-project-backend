import uuid
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date


class ShoppingCartItemModel(BaseModel):
    art_id: uuid.UUID
    artist: str
    quantity: int
    title: str
    medium: str
    description: str
    added_at: datetime = datetime.utcnow()
    price: float
    image_url: str


class ShoppingCartArtsModel(BaseModel):
    art_id: str
    quantity: int
    description: str
    added_at: str
    price: float
    artist: str
    image_url: str
    title: str
    medium: str


class ShoppingCartModel(BaseModel):
    user_id: uuid.UUID
    arts: List[ShoppingCartArtsModel]
    added_date: datetime
    uid: uuid.UUID


class UpdateCartModel(BaseModel):
    art_id: str


# class StripeCustomerModel(BaseModel):
#     email: str
#     name: str
#     phone: Optional[str]
#     delivery_address: str
#     internal_user_id: str


class CardDetailsModel(BaseModel):
    brand: str
    last4: str
    amount: float
    tax: float


class StripeCustomerModel(BaseModel):
    name: str
    email: str
    user_id: str
    order_id: str
