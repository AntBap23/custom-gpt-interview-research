import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO")

def create_checkout_session(user_id, user_email):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID_PRO, "quantity": 1}],
        mode="subscription",
        customer_email=user_email,
        success_url="https://your-app-url/?success=true",
        cancel_url="https://your-app-url/?canceled=true",
        metadata={"user_id": user_id}
    )
    return session.url