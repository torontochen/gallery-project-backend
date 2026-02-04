import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from datetime import datetime
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import ShoppingCart
from src.shopping_cart.schemas import ShoppingCartModel, ShoppingCartItemModel
from sqlmodel import select, desc

class ShoppingCartService:
    async def get_shopping_cart_by_user(self, user_id: str, session: AsyncSession) -> List:
        statement = select(ShoppingCart).where(ShoppingCart.user_id == user_id).order_by(ShoppingCart.added_date.desc())
        result = await session.exec(statement)
        print(result)
        item = result.first()
        return item

    async def add_item_to_cart(self,  user_id: str, item_data: ShoppingCartItemModel, session: AsyncSession):
        # print(user_id)
        # print(item_data)
        statement = select(ShoppingCart).where(ShoppingCart.user_id == user_id)
        user_cart_data = await session.exec(statement)
        # print(user_cart_data.first())
        user_cart = user_cart_data.first()
        if user_cart is None:
            item_data_dict = item_data.model_dump()
            print('None')
            item_data_dict['art_id'] = str(item_data_dict['art_id'])
            item_data_dict['added_at'] = str(item_data_dict['added_at'])
            art_list = []
            art_list.append(item_data_dict)
            # print(art_list)
            new_shopping_cart = ShoppingCart(user_id = user_id, arts=art_list)
            # print(new_shopping_cart)
            session.add(new_shopping_cart)
            await session.commit()
            await session.refresh(new_shopping_cart)
            return new_shopping_cart
        else:
           
            item_data_dict = item_data.model_dump()
            item_data_dict['art_id'] = str(item_data_dict['art_id'])
            item_data_dict['added_at'] = str(item_data_dict['added_at'])
            
            user_cart.arts.append(item_data_dict)
            user_cart.added_date = datetime.utcnow()
            session.add(user_cart)
            await session.commit()

            
            return user_cart

    async def remove_item_from_cart(self, item_id: str, session: AsyncSession):
        statement = select(ShoppingCart).where(ShoppingCart.id == item_id)
        result = await session.exec(statement)
        item = result.first()
        if item:
            await session.delete(item)
            await session.commit()
            return True
        return False