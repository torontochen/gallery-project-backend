from typing import List
import os
import json
import stripe


from fastapi import APIRouter, Depends, status, responses, Request
from sqlmodel.ext.asyncio.session import AsyncSession


from src.auth.dependencies import AccessTokenBearer, RoleChecker
from src.auth.service import UserService
from src.shopping_cart.service import ShoppingCartService
from src.db.main import get_session
from src.config import Config

from .schemas import ShoppingCartItemModel, ShoppingCartModel
from .utils import create_dynamic_customer
from src.errors import ShoppingCartNotFound, UserNotFound

shopping_cart_router = APIRouter()
shopping_cart_service = ShoppingCartService()
user_service = UserService()
acccess_token_bearer = AccessTokenBearer()
role_checker = Depends(RoleChecker(["admin", "user"]))
stripe.api_key = Config.STRIPE_SECRET_KEY

# @shopping_cart_router.get("/{user_id}", response_model=List[ShoppingCartModel], dependencies=[role_checker])
@shopping_cart_router.get("/{user_id}", response_model=List[ShoppingCartModel])
async def get_shopping_cart_by_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    user_cart = await shopping_cart_service.get_shopping_cart_by_user(user_id, session)
    if user_cart is None:
        raise UserNotFound()
    else:
        return user_cart

# @shopping_cart_router.post("/", status_code=status.HTTP_201_CREATED, response_model=ShoppingCartModel, dependencies=[role_checker])
@shopping_cart_router.post("/{user_id}", status_code=status.HTTP_201_CREATED, response_model=ShoppingCartModel)
async def add_item_to_shopping_cart(
    user_id: str,
    item_data: ShoppingCartItemModel,
    session: AsyncSession = Depends(get_session),
):
    user_id = user_id  # Assuming the user_id is part of the item data; adjust as necessary
    item_data.art_id = item_data.art_id
    updated_cart = await shopping_cart_service.add_item_to_cart(user_id, item_data, session)
    if updated_cart is None:
        raise UserNotFound()
    else:
        return updated_cart

@shopping_cart_router.get("/checkout/{orderId}", )
async def create_checkout_session(orderId: str, token_details: dict = Depends(acccess_token_bearer), session: AsyncSession = Depends(get_session)):
    user_id = token_details.get("user")["user_uid"]
    print("user id is", type(user_id))
    user_email = token_details.get("user")["email"]
    user_name = token_details.get("user")["first_name"] + " " + token_details.get("user")["last_name"]
    user = await user_service.get_user_by_email(user_email, session)
    customer_data = {
        "email": user_email,
        "name": user_name,
        "phone": user.phone if user.phone else "",
        "delivery_address": user.address if user.address else "",
        "user_id_internal": user_id,
    }
    customer =  await create_dynamic_customer(customer_data)
    shopping_cart = await shopping_cart_service.get_shopping_cart_by_user(user_id, session)
    print("shopping cart is", shopping_cart)
    line_items_list = []
    for item in shopping_cart.arts:
        line_items_list.append({
            "price_data": {
                "currency": "cad",
                "product_data": {
                    "name": item['description'],
                },
                "unit_amount": int(item['price']) * 100,
            },
            "quantity": item['quantity'],
        })
    checkout_session =  stripe.checkout.Session.create(
        line_items=line_items_list,
        metadata={
            "user_id": user_id,
            "email": user_email,
            "order_id": orderId,
        },
        mode="payment",
        payment_method_types=["card"],
        success_url=Config.BASE_URL + "/shoppingcart/",
        cancel_url=Config.BASE_URL + "/shoppingcart/",
        customer=customer.id,
    )
    print("checkout session is", checkout_session)
    return responses.RedirectResponse(checkout_session.url, status_code=303)


@shopping_cart_router.post("/webhook/")
async def stripe_webhook(request: Request):
    payload = await request.body()
    event = None

    try:
        event =  stripe.Event.construct_from(json.loads(payload), Config.STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        print("Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    print("event received is", event)
    if event["type"] == "checkout.session.completed":
        payment = event["data"]["object"]
        amount = payment["amount_total"]
        currency = payment["currency"]
        user_id = payment["metadata"]["user_id"] # get custom user id from metadata
        user_email = payment["customer_details"]["email"]
        user_name = payment["customer_details"]["name"]
        order_id = payment["id"]
    elif event["type"] == "invoice.payment_failed":
        print("Payment failed")
        return responses.RedirectResponse(checkout_session.url, status_code=303)
        
        # save to db
        # send email in background task
    return {"status": "success"}