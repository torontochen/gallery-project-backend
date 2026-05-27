import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from datetime import datetime
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.models import ShoppingCart, Transaction, Art
from src.shopping_cart.schemas import (
    ShoppingCartModel,
    ShoppingCartItemModel,
    UpdateCartModel,
    CardDetailsModel,
    StripeCustomerModel,
)
from sqlmodel import select, desc
from src.celery_tasks import send_email


class ShoppingCartService:
    async def get_shopping_cart_by_user(
        self, user_id: str, session: AsyncSession
    ) -> List:
        statement = (
            select(ShoppingCart)
            .where(ShoppingCart.user_id == user_id)
            .order_by(ShoppingCart.added_date.desc())
        )
        result = await session.exec(statement)
        # print(result)
        item = result.first()
        return item

    async def add_item_to_cart(
        self, user_id: str, item_data: ShoppingCartItemModel, session: AsyncSession
    ):
        # print(user_id)
        # print(item_data)
        statement = select(ShoppingCart).where(ShoppingCart.user_id == user_id)
        user_cart_data = await session.exec(statement)
        # print(user_cart_data.first())
        user_cart = user_cart_data.first()
        if user_cart is None:
            item_data_dict = item_data.model_dump()
            # print("None")
            item_data_dict["art_id"] = str(item_data_dict["art_id"])
            item_data_dict["added_at"] = str(item_data_dict["added_at"])
            art_list = []
            art_list.append(item_data_dict)
            # print(art_list)
            new_shopping_cart = ShoppingCart(user_id=user_id, arts=art_list)
            # print(new_shopping_cart)
            session.add(new_shopping_cart)
            await session.commit()
            await session.refresh(new_shopping_cart)
            return new_shopping_cart
        else:

            item_data_dict = item_data.model_dump()
            item_data_dict["art_id"] = str(item_data_dict["art_id"])
            item_data_dict["added_at"] = str(item_data_dict["added_at"])

            user_cart.arts.append(item_data_dict)
            user_cart.added_date = datetime.utcnow()
            session.add(user_cart)
            await session.commit()
            return user_cart

    async def update_cart(
        self, user_id: str, update_data: UpdateCartModel, session: AsyncSession
    ):
        statement = select(ShoppingCart).where(ShoppingCart.user_id == user_id)
        result = await session.exec(statement)
        item = result.first()
        item_dict = item.model_dump()
        # print(item_dict)
        if item:
            item.arts = [
                art for art in item_dict["arts"] if art["art_id"] != update_data.art_id
            ]
            await session.commit()
            return item
        return False

    async def update_database_after_payment(
        self,
        customer_info: StripeCustomerModel,
        payment_info: CardDetailsModel,
        session: AsyncSession,
    ):
        print("customer info is", customer_info)
        statement_shopping_cart = select(ShoppingCart).where(
            ShoppingCart.uid == customer_info["order_id"]
        )
        result = await session.exec(statement_shopping_cart)
        shopping_cart = result.first()
        if shopping_cart:
            new_transaction = Transaction(
                user_id=customer_info["user_id"],
                uid=customer_info["order_id"],
                amount=payment_info["amount"],
                tax=payment_info["tax"],
                total_amount=payment_info["amount"] + payment_info["tax"],
                items=shopping_cart.arts,
            )
            shopping_cart_dict = shopping_cart.model_dump()
            arts_list = shopping_cart_dict["arts"]
            for art in arts_list:
                statement_art = select(Art).where(Art.uid == art["art_id"])
                result_art = await session.exec(statement_art)
                art_item = result_art.first()
                art_item.status = "sold"

            template_name = "order_confirmation_email.html"
            template_body = {
                "name": customer_info["name"],
                "message": (
                    f"Thank you for purchasing from Monohaus Gallery. Your order has been successfully processed with. Payment  has been charged to your {payment_info['brand']} card {payment_info['last4']}. We will notify you once your order is shipped."
                ),
                "tax": payment_info["tax"],
                "subtotal": payment_info["amount"],
                "total_amount": payment_info["amount"] + payment_info["tax"],
                "item_list": shopping_cart.arts,
            }

            emails = [customer_info["email"]]

            subject = (
                f"order confirmation - Monohaus Gallery ({customer_info['order_id']})"
            )

            send_email.delay(emails, subject, template_body, template_name)

            session.add(new_transaction)

            await session.delete(shopping_cart)
            await session.commit()
            return True
        return False
