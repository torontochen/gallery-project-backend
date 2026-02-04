import uuid
from datetime import datetime, date
from typing import Optional, List
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlmodel import Field, SQLModel, Relationship, Column,  UniqueConstraint

class User(SQLModel, table=True):
    __tablename__ = "users"
    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    first_name: str
    last_name: str
    role: str = Field(default="user")
    bio: Optional[str] = None
    country: Optional[str] = None
    hashed_password: str = Field( sa_column=Column(pg.VARCHAR, nullable=False), exclude=True)
    is_verified: bool = Field(default=True)
    address: Optional[str] = None
    delivery_address: Optional[str] = None
    phone_number: Optional[str] = None
    transactions: Optional[List["Transaction"]] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})
    shopping_cart: Optional["ShoppingCart"] = Relationship(back_populates="user", sa_relationship_kwargs={"lazy": "selectin"})
    arts: Optional[List["Art"]] = Relationship(back_populates="artist", sa_relationship_kwargs={"lazy": "selectin"})
    # created_at: datetime = Field(default_factory=datetime.utcnow)
    # updated_at: datetime = Field(default_factory=datetime.utcnow)
    def __repr__(self):
            return f"<User {self.username}>"

# class Artist(SQLModel, table=True):
#     __tablename__ = "artists"
#     uid: uuid.UUID = Field(
#         sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
#     )
#     full_name: str
#     bio: Optional[str] = None
#     country: Optional[str] = None
    # arts: List["Art"] = Relationship(back_populates="artist", sa_relationship_kwargs={"lazy": "selectin"})
    # def __repr__(self):
    #         return f"<Artist {self.full_name}>"

class Art(SQLModel, table=True):
    __tablename__ = "arts"
    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    title: str
    description: str
    creation_date:  datetime = Field(default=datetime.utcnow)
    price: float
    status: str = Field(default="available")
    image_url: str
    artist_id: uuid.UUID = Field(foreign_key="users.uid")
    transaction_id: Optional[uuid.UUID] = Field(default = None, foreign_key="transactions.uid")
    # shopping_cart_id: Optional[uuid.UUID] = Field(default = None, foreign_key="shopping_carts.uid")
    artist: User = Relationship(back_populates="arts", sa_relationship_kwargs={"lazy": "selectin"})
    # transaction: Optional["Transaction"] = Relationship(back_populates="art", sa_relationship_kwargs={"lazy": "selectin"})
    # shopping_cart: Optional["ShoppingCart"] = Relationship(back_populates="art", sa_relationship_kwargs={"lazy": "selectin"})
    def __repr__(self):
            return f"<Art {self.title}>"

class Transaction(SQLModel, table=True):
        __tablename__ = "transactions"
        uid: uuid.UUID = Field(
            sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
        )
        user_id: uuid.UUID = Field(foreign_key="users.uid")
        amount: float
        tax: float
        total_amount: float
        transaction_date: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow))
        items: List["Art"] = Field(sa_column=Column(pg.JSON())) 
        user: User = Relationship(back_populates="transactions")
        def __repr__(self):
                return f"<Transaction {self.uid}>"

class ShoppingCart(SQLModel, table=True):
    __tablename__ = "shopping_carts"
    uid: uuid.UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid.uuid4)
    )
    user_id: uuid.UUID = Field(foreign_key="users.uid")
    # work_id: uuid.UUID = Field(foreign_key="works.uid")
    added_date: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.utcnow))
    arts: List["Art"] = Field(sa_type=MutableList.as_mutable(pg.JSON))  # This will be a list of Art items in the cart
    user: User = Relationship(back_populates="shopping_cart")
    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
            return f"<ShoppingCart {self.uid}>"
            
