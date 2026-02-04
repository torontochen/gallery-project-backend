import stripe
from src.config import Config
from schemas import StripeCustomerModel
stripe.api_key = Config.STRIPE_SECRET_KEY


async def create_dynamic_customer(customer_data: StripeCustomerModel):
    customer =  stripe.Customer.create(
        email=customer_data.email,
        name=customer_data.name,
        phone=customer_data.phone,
        delivery_address=customer_data.delivery_address,
        # Metadata is crucial for linking back to your internal database
        metadata={
            'internal_user_id': customer_data.user_id_internal
        }
    )
    return customer