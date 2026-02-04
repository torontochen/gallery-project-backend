import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel
from src.auth.schemas import UserModel

# class ArtistModel(BaseModel):
#     uid: uuid.UUID
#     full_name: str
#     bio: str
#     country: str

class ArtModel(BaseModel):
    uid: uuid.UUID 
    title: str
    description: str
    creation_date: datetime
    price: float
    image_url: str
    artist: UserModel 
    transaction_id: Optional[uuid.UUID] = None
    shopping_cart: Optional[uuid.UUID] = None

class ArtCreateModel(BaseModel):
    title: str
    description: str
    creation_date: datetime = datetime.utcnow()
    price: float
    image_url: str
    artist_id: uuid.UUID

class ArtUpdateModel(BaseModel):
    title: str
    description: str
    price: float