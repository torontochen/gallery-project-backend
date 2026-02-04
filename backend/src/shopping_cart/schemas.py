import uuid
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date



class ShoppingCartItemModel(BaseModel):
    art_id: uuid.UUID
    artist: str
    quantity: int
    title: str
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

class ShoppingCartModel(BaseModel):
    user_id: uuid.UUID
    arts: List[ShoppingCartArtsModel]
    added_date: datetime 

class StripeCustomerModel(BaseModel):
    email: str
    name: str
    phone: Optional[str]
    delivery_address: str
    internal_user_id: str