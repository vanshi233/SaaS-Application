import stripe
from decouple import config
from . import date_utils

# -----------------------------
# ✅ Helper: Always use latest Stripe key from .env
# -----------------------------
def set_stripe_key():
    stripe.api_key = config("STRIPE_SECRET_KEY", default="")
    if not stripe.api_key:
        raise ValueError("Stripe secret key not found in environment!")
    return stripe.api_key


# -----------------------------
# ✅ Subscription Data Serializer
# -----------------------------
def serialize_subscription_data(subscription_response):
    status = subscription_response.status
    current_period_start = date_utils.timestamp_as_datetime(subscription_response.current_period_start)
    current_period_end = date_utils.timestamp_as_datetime(subscription_response.current_period_end)
    cancel_at_period_end = subscription_response.cancel_at_period_end
    return {
        "current_period_start": current_period_start,
        "current_period_end": current_period_end,
        "status": status,
        "cancel_at_period_end": cancel_at_period_end,
    }


# -----------------------------
# ✅ Stripe Operations
# -----------------------------
def create_customer(name="", email="", metadata=None, raw=False):
    set_stripe_key()
    if metadata is None:
        metadata = {}
    response = stripe.Customer.create(
        name=name,
        email=email,
        metadata=metadata,
    )
    return response if raw else response.id


def create_product(name="", metadata=None, raw=False):
    set_stripe_key()
    if metadata is None:
        metadata = {}
    response = stripe.Product.create(
        name=name,
        metadata=metadata,
    )
    return response if raw else response.id


def create_price(currency="usd", unit_amount="9999", interval="month", product=None, metadata=None, raw=False):
    set_stripe_key()
    if metadata is None:
        metadata = {}
    if product is None:
        raise ValueError("Product ID is required to create a price.")

    response = stripe.Price.create(
        currency=currency,
        unit_amount=unit_amount,
        recurring={"interval": interval},
        product=product,
        metadata=metadata,
    )
    return response if raw else response.id


def start_checkout_session(customer_id, success_url="", cancel_url="", price_stripe_id="", raw=True):
    set_stripe_key()

    # Append checkout session ID if not present
    if not success_url.endswith("?session_id={CHECKOUT_SESSION_ID}"):
        success_url = f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}"

    response = stripe.checkout.Session.create(
        customer=customer_id,
        success_url=success_url,
        cancel_url=cancel_url,
        line_items=[{"price": price_stripe_id, "quantity": 1}],
        mode="subscription",
    )

    return response if raw else response.url


def get_checkout_session(stripe_id, raw=True):
    set_stripe_key()
    response = stripe.checkout.Session.retrieve(stripe_id)
    return response if raw else response.url


def get_subscription(stripe_id, raw=True):
    set_stripe_key()
    response = stripe.Subscription.retrieve(stripe_id)
    return response if raw else serialize_subscription_data(response)


def get_customer_active_subscriptions(customer_stripe_id):
    set_stripe_key()
    response = stripe.Subscription.list(customer=customer_stripe_id, status="active")
    return response


def cancel_subscription(stripe_id, reason="", feedback="other", cancel_at_period_end=False, raw=True):
    set_stripe_key()

    if cancel_at_period_end:
        response = stripe.Subscription.modify(
            stripe_id,
            cancel_at_period_end=cancel_at_period_end,
            cancellation_details={"comment": reason, "feedback": feedback},
        )
    else:
        response = stripe.Subscription.cancel(
            stripe_id,
            cancellation_details={"comment": reason, "feedback": feedback},
        )

    return response if raw else serialize_subscription_data(response)


def get_checkout_customer_plan(session_id):
    set_stripe_key()

    checkout_r = get_checkout_session(session_id, raw=True)
    customer_id = checkout_r.customer
    sub_stripe_id = checkout_r.subscription
    sub_r = get_subscription(sub_stripe_id, raw=True)
    sub_plan = sub_r.plan

    subscription_data = serialize_subscription_data(sub_r)
    data = {
        "customer_id": customer_id,
        "plan_id": sub_plan.id,
        "sub_stripe_id": sub_stripe_id,
        **subscription_data,
    }
    return data
