# import stripe
import paypalrestsdk
from paypalrestsdk import BillingPlan, BillingAgreement
from typing import Literal
import logging
from datetime import datetime, timedelta, timezone
import stripe

from func.utils import load_json, save_json
from func.constants import (
    APP_NAME,
    AUTO_INIT_PAYPAL_SDK,
    PAYMENT_GATEWAY_MODE, PAYPAL_SUBSCRIPTION_CANCEL_URL, PAYPAL_SUBSCRIPTION_RETURN_URL,
    PAYPAL_PAYMENT_CANCEL_URL, PAYPAL_PAYMENT_RETURN_URL,
    PAYPAL_CLIENT_ID, PAYPAL_SECRET,
    STRIPE_API_KEY, STRIPE_SUBSCRIPTION_CANCEL_URL, STRIPE_SUBSCRIPTION_RETURN_URL,
    PLANS_JSON_FILE_PATH
)


logger = logging.getLogger(__name__)

# Initialize PayPal SDK
def init_paypal_sdk():
    # Set up PayPal SDK configuration
    paypalrestsdk.configure({
        "mode": PAYMENT_GATEWAY_MODE,  # sandbox or live
        "client_id": PAYPAL_CLIENT_ID,
        "client_secret": PAYPAL_SECRET,
    })

    logger.info(f"Initialised PayPal SDK in {PAYMENT_GATEWAY_MODE} mode.")

def create_paypal_billing_agreement(plan_id: str, name: str = f"Monthly Subscription Plan for {APP_NAME}", description: str = f"Monthly subscription plan with recurring payments for {APP_NAME}"):
    """
    Creates a billing agreement using PayPal's API.
    This function creates a billing plan and a billing agreement for PayPal service.

        Args: 
            name (str): The name of the billing plan.
            description (str): The description of the billing plan.
            metadata (str): Metadata for the billing plan.
            price (float): The price of the billing plan.
            duration (int): The duration of the subscription in days.
        Returns:
            str: The approval URL for the billing agreement.
    """
    try:
        # Check if the PayPal SDK is initialized
        if not paypalrestsdk.api:
            init_paypal_sdk()
        
        # Load the plans from the JSON file
        plans = load_json(PLANS_JSON_FILE_PATH)

        # Get the plan details from the JSON file
        plan = plans.get(plan_id, {})
        if not plan:
            logger.error(f"Plan ID ({plan_id}) not found")
            return None

        billing_plan_id = plan['billing_plans']['paypal']['billing_plan_id']
        if billing_plan_id:
            try:
                billing_plan = BillingPlan.find(billing_plan_id)
                logger.info("Got Billing Plan Details for Billing Plan[%s]" % (billing_plan.id))

                if not billing_plan.state == 'ACTIVE':
                    if billing_plan.activate():
                        billing_plan = BillingPlan.find(billing_plan_id)
                        logger.info("Billing Plan [%s] state changed to [%s]" %
                            (billing_plan.id, billing_plan.state))
                    else:
                        logger.error(billing_plan.error)
                else:
                    logger.info("Billing Plan [%s] is active!" % billing_plan.id)

            except paypalrestsdk.ResourceNotFound as error:
                logger.error("Billing Plan Not Found:", error)
                billing_plan_id = None

        if not billing_plan_id:
            billing_plan_attributes = {
                "name": name + (f' - Plan ID {plan_id}'),
                "description": description + (f' - Plan ID {plan_id}'),
                "type": "infinite",
                "payment_definitions": [
                    {
                        "name": f"Monthly Payments for {APP_NAME}",
                        "type": "REGULAR",
                        "frequency": plan['billing_plans']['paypal']['frequency']['unit'],
                        "frequency_interval": str(plan['billing_plans']['paypal']['frequency']['value']),
                        "amount": {
                            "currency": plan['billing_plans']['paypal']['currency'],
                            "value": plan['price']
                        },
                        "cycles": str(plan['billing_plans']['paypal']['cycles']),
                    }
                ],
                "merchant_preferences": {
                    "cancel_url": PAYPAL_SUBSCRIPTION_CANCEL_URL,
                    "return_url": PAYPAL_SUBSCRIPTION_RETURN_URL,
                    "max_fail_attempts": "3",
                    "auto_bill_amount": "YES",
                    "initial_fail_amount_action": "CONTINUE"
                }
            }

            billing_plan = BillingPlan(billing_plan_attributes)

            if billing_plan.create():
                logger.info("Billing Plan created successfully")
            else:
                logger.error("Error creating Billing Plan:", billing_plan.error)
                return None

            if billing_plan.activate():
                logger.info("Billing Plan activated successfully")
            else:
                logger.error("Error activating Billing Plan:", billing_plan.error)
                return None

            billing_plan_id = billing_plan.id

            # Update the plan with the new billing plan ID
            plan['billing_plans']['paypal']['billing_plan_id'] = billing_plan_id
            plans[plan_id] = plan

            # Save the updated plan to the JSON file
            save_json(plans, PLANS_JSON_FILE_PATH)

        start_date = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        billing_agreement_attributes = {
            "name": "Monthly Subscription Agreement" + (f' - Plan ID {plan_id}'),
            "description": f"Agreement for Monthly Subscription Plan" + (f' - Plan ID {plan_id}'),
            "start_date": start_date,
            "plan": {
                "id": billing_plan_id
            },
            "payer": {
                "payment_method": "paypal"
            }
        }

        billing_agreement = BillingAgreement(billing_agreement_attributes)

        if billing_agreement.create():
            logger.info("Billing Agreement created successfully")
            for link in billing_agreement.links:
                if link.rel == "approval_url":
                    approval_url = str(link.href)
                    return approval_url
        else:
            logger.error("Error creating Billing Agreement:", billing_agreement.error)
    except Exception as e:
        logger.error("Error creating Billing Plan:", e)
    return None

def create_stripe_billing_plan(plan_id: str, name: str = f"Monthly Subscription Plan for {APP_NAME}", description: str = f"Monthly subscription plan with recurring payments for {APP_NAME}"):
    """
    Creates a billing plan using Stripe's API.

    Args:
        plan_id (str): The ID of the plan.
        name (str): The name of the billing plan.
        description (str): The description of the billing plan.
    Returns:
        dict: The response from Stripe's API.
    """
    try:
        # Initialize Stripe with the API key
        stripe.api_key = STRIPE_API_KEY

        # Load the plans from the JSON file
        plans = load_json(PLANS_JSON_FILE_PATH)

        plan = plans.get(plan_id, {})
        if not plan:
            print(f"Plan ID ({plan_id}) not found")
            return None
        
        price_id = plan['billing_plans']['stripe']['price_id']
        if not price_id:        
            product_id = plan['billing_plans']['stripe']['product_id']
            if not product_id:
                product = stripe.Product.create(name=name + (f' - Plan ID {plan_id}'), description=description + (f' - Plan ID {plan_id}'))
                product_id = product.id

                plan['billing_plans']['stripe']['product_id'] = product_id
                plans[plan_id] = plan
                save_json(plans, PLANS_JSON_FILE_PATH)

            price = stripe.Price.create(
                product=product_id,
                unit_amount=int(plan['price'] * 100),  # Stripe requires amounts in cents
                currency=plan['billing_plans']['stripe']['currency'],
                recurring={"interval": plan['billing_plans']['stripe']['frequency']['unit'], 
                        "interval_count": plan['billing_plans']['stripe']['frequency']['value']},  # Monthly subscription
            )
            price_id = price.id
            plan['billing_plans']['stripe']['price_id'] = price_id
            plans[plan_id] = plan
            save_json(plans, PLANS_JSON_FILE_PATH)

        # Step 3: Create a Checkout Session for this subscription
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            metadata={"plan_id": plan_id},
            success_url=STRIPE_SUBSCRIPTION_RETURN_URL,
            cancel_url=STRIPE_SUBSCRIPTION_CANCEL_URL,
        )

        return checkout_session.url  # Redirect the user to this URL for approval
    except Exception as e:
        print("Error creating billing agreement:", e)
    return None

def create_billing_agreement(plan_id: str, platform: Literal['paypal', 'stripe']):
    # TODO: Implement the logic to create a billing agreement link using the payment provider's API
    """
        Args: 
            plan_id (str): The ID of the plan.
            platform (str): The payment platform (PayPal or Stripe).
        Returns:
            str: The approval URL for the billing agreement.
    """
    if platform == "paypal":
        return create_paypal_billing_agreement(plan_id)
    elif platform == "stripe":
        return create_stripe_billing_plan(plan_id)  # Example values for amount and duration
    else:
        raise ValueError("Invalid platform specified")

def cancel_billing_agreement(subscription_id: str):
    # TODO: Implement the logic to cancel a billing agreement using the payment provider's API
    # Using the subscription_id, get the platform (PayPal or Stripe) from the database and cancel the subscription
    pass

def create_paypal_payemnt(amount: float):
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [{
                "amount": {
                    "total": amount,
                    "currency": "USD"
                },
                "description": f"Credits for {APP_NAME} AI"
            }],
            "redirect_urls": {
                "return_url": PAYPAL_PAYMENT_RETURN_URL,
                "cancel_url": PAYPAL_PAYMENT_CANCEL_URL
            }
        })

        if payment.create():
            print("Payment created successfully.")
            for link in payment.links:
                if link.method == "REDIRECT":
                    redirect_url = link.href
                    return redirect_url
        else:
            print(f"Error while creating payment: {payment.error}")
            return None
    except Exception as e:
        print(f"An error occurred during payment creation: {str(e)}")
        return None

def create_stripe_payment(amount: float):
    # TODO: Implement the logic to create a payment using Stripe's API
    pass

def create_payment(amount: float, platform: Literal['paypal', 'stripe']):
    if platform == 'paypal':
        return create_paypal_payemnt(amount)
    elif platform == "stripe":
        return create_stripe_payment(amount)  # Example values for amount and duration
    else:
        raise ValueError("Invalid platform specified")

def execute_paypal_payment(payment_id: str, payer_id: str):
    # TODO: Implement the logic to execute the payment using PayPal's API
    pass

def execute_stripe_payment(payment_id: str, payer_id: str):
    # TODO: Implement the logic to execute the payment using Stripe's API
    pass

def execute_payment(platform: Literal['paypal', 'stripe'], payment_id: str, payer_id: str):
    # Based on the documentation of the payment provider, execute the payment and return the result
    # Use also webhooks to do so
    # TODO: Implement the logic to execute the payment using the payment provider's API
    pass

# Initialize the PayPal SDK when the module is loaded
if AUTO_INIT_PAYPAL_SDK:
    init_paypal_sdk()