from typing import List, Annotated
import os
import json
import stripe


from fastapi import APIRouter, Depends, status, responses, Request, Header
from fastapi.exceptions import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession


from src.auth.dependencies import AccessTokenBearer, RoleChecker
from src.auth.service import UserService
from src.shopping_cart.service import ShoppingCartService
from src.db.main import get_session
from src.config import Config

from .schemas import ShoppingCartItemModel, ShoppingCartModel, UpdateCartModel
from .utils import create_dynamic_customer
from src.errors import ShoppingCartNotFound, UserNotFound

shopping_cart_router = APIRouter()
shopping_cart_service = ShoppingCartService()
user_service = UserService()
access_token_bearer = AccessTokenBearer()
role_checker = Depends(RoleChecker(["admin", "user", "artist"]))
stripe.api_key = Config.STRIPE_SECRET_KEY


# @shopping_cart_router.get("/{user_id}", response_model=List[ShoppingCartModel], dependencies=[role_checker])
@shopping_cart_router.get(
    "/{user_id}", response_model=ShoppingCartModel, dependencies=[role_checker]
)
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
@shopping_cart_router.post(
    "/{user_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=ShoppingCartModel,
    dependencies=[role_checker],
)
async def add_item_to_shopping_cart(
    user_id: str,
    item_data: ShoppingCartItemModel,
    session: AsyncSession = Depends(get_session),
):
    user_id = (
        user_id  # Assuming the user_id is part of the item data; adjust as necessary
    )
    item_data.art_id = item_data.art_id
    updated_cart = await shopping_cart_service.add_item_to_cart(
        user_id, item_data, session
    )
    if updated_cart is None:
        raise UserNotFound()
    else:
        return updated_cart


@shopping_cart_router.put(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=ShoppingCartModel,
    dependencies=[role_checker],
)
async def update_shopping_cart(
    user_id: str,
    update_data: UpdateCartModel,
    session: AsyncSession = Depends(get_session),
):
    updated_cart = await shopping_cart_service.update_cart(
        user_id, update_data, session
    )
    if updated_cart is None:
        raise UserNotFound()
    else:
        return updated_cart


@shopping_cart_router.post(
    "/checkout/{orderId}",
)
async def create_checkout_session(
    orderId: str,
    token_details: dict = Depends(access_token_bearer),
    session: AsyncSession = Depends(get_session),
):
    # print("order id is", orderId)
    user_id = token_details.get("user")["user_uid"]
    # print("user id is", type(user_id))
    user_email = token_details.get("user")["email"]
    user = await user_service.get_user_by_email(user_email, session)
    user_name = user.first_name + " " + user.last_name
    # print("user is", user)
    customer_data = {
        "email": user_email,
        "name": user_name,
        "phone": user.phone_number if user.phone_number else "",
        # "delivery_address": user.delivery_address if user.delivery_address else user.address,
        "user_id_internal": user_id,
    }
    customer = await create_dynamic_customer(customer_data)
    shopping_cart = await shopping_cart_service.get_shopping_cart_by_user(
        user_id, session
    )
    # print("shopping cart is", shopping_cart)
    line_items_list = []
    for item in shopping_cart.arts:
        line_items_list.append(
            {
                "price_data": {
                    "currency": "cad",
                    "product_data": {
                        "name": item["title"]
                        + " by "
                        + item["artist"]
                        + " "
                        + item["description"]
                        + " "
                        + item["medium"]
                    },
                    "unit_amount": int(item["price"]) * 100,
                },
                "quantity": item["quantity"],
            }
        )
    # checkout_session =  stripe.checkout.Session.create(
    checkout_session = await stripe.checkout.Session.create_async(
        line_items=line_items_list,
        metadata={
            "user_id": user_id,
            "email": user_email,
            "order_id": orderId,
        },
        mode="payment",
        payment_method_types=["card"],
        # success_url=Config.BASE_URL+ "shopping-cart",
        success_url=f"{Config.BASE_URL}?session_id={{CHECKOUT_SESSION_ID}}",
        # success_url=f"http://localhost:8000/api/shopping_cart/stripe/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=Config.BASE_URL + "checkout",
        customer=customer.id,
        expand=["payment_intent"],
    )
    session = await stripe.checkout.Session.retrieve_async(
        checkout_session.id, expand=["payment_intent"]
    )

    # print("checkout session is", checkout_session)
    # return responses.RedirectResponse(url=checkout_session.url, status_code=status.HTTP_200_SEE_OTHER)
    return {
        "checkout_url": checkout_session.url,
        "payment_status": session.payment_status,
    }


@shopping_cart_router.get("/stripe/success")
async def payment_success(session_id: str):
    try:
        session = await stripe.checkout.Session.retrieve_async(checkout_session)
        # print("Session details:", session)

        if session.payment_status == "paid":
            # TODO: Here, you could save the order to your database
            # TODO: Here, you could send a confirmation email to the user
            # return {"status": "success", "customer_email": session.customer_details.email}
            return responses.RedirectResponse(
                url=f"{Config.BASE_URL}", status_code=status.HTTP_200_OK
            )

        return {"status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@shopping_cart_router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request, session: AsyncSession = Depends(get_session)
):
    stripe_signature = request.headers.get("stripe-signature")
    payload = await request.body()
    # print("payload is", payload)
    event = None

    try:
        # event =  stripe.Event.construct_from(json.loads(payload), stripe_signature, Config.STRIPE_WEBHOOK_SECRET)
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, Config.STRIPE_WEBHOOK_SECRET
        )
        # print("event received is", event)
    except ValueError as e:
        print("Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        print("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        # session_id = event['data']['object']['id']

        # 3. Retrieve the full session and "expand" the payment_intent
        # This replaces the PI ID with the full PaymentIntent object
        # full_session = stripe.checkout.Session.retrieve(
        #     session_id,
        #     expand=['payment_intent']
        # )

        # Now you can access full PI data directly
        # payment_intent = full_session.payment_intent

        # Assuming payload is the JSON from the webhook
        payment_intent_id = event["data"]["object"]["payment_intent"]

        # Retrieve the PaymentIntent
        payment_intent = stripe.PaymentIntent.retrieve(
            payment_intent_id, expand=["payment_method"]
        )

        card_details = payment_intent.payment_method.card
        last4 = card_details.last4
        brand = card_details.brand
        # print("PaymentIntent details:", payment_intent)
        # print("checkout.session.completed", event)
        payment = event["data"]["object"]
        amount = payment["amount_total"]
        currency = payment["currency"]
        user_id = payment["metadata"]["user_id"]  # get custom user id from metadata
        user_email = payment["customer_details"]["email"]
        user_name = payment["customer_details"]["name"]
        order_id = payment["metadata"]["order_id"]
        customer_info = {
            "email": user_email,
            "name": user_name,
            "user_id": user_id,
            "order_id": order_id,
        }
        payment_info = {
            "brand": brand,
            "last4": last4,
            "amount": amount / 100,  # Convert from cents to dollars
            "tax": amount
            * 0.13
            / 100,  # Assuming tax is not calculated separately in this example
        }

        await shopping_cart_service.update_database_after_payment(
            customer_info=customer_info, payment_info=payment_info, session=session
        )

    elif event["type"] == "invoice.payment_failed":
        print("Payment failed")
        return responses.RedirectResponse(
            url=checkout_session.url, status_code=status.HTTP_303_SEE_OTHER
        )

        # save to db
        # send email in background task
    return {"status": "success"}
