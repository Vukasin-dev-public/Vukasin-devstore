from func.models.database import database
from func.models.payment import Payment
from func.payment_utils import create_billing_agreement, paypalrestsdk, stripe
from func.models.plan import SubscriptionPlan, get_plan
from typing import Literal
from func.constants import SUPPORTED_PAYMENT_PROVIDERS

from datetime import datetime

# subscriptions {
#   id stirng pk
#   user_id string fk not null
#   platform string // Paypal or Stripe...
#   active boolean default false
#   created_at timestamp
#   updated_at timestamp
#   ends_at timestamp
# }

# subscription_payments {
#   subscription_id string pk
#   payment_id string pk
#   added_at timestamp
# }

class Subscription:
    def __init__(self, id: str, user_id: str, platform: str, ends_at: datetime, active: bool = False, created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.user_id = user_id
        self.platform = platform
        self.active = active

        self.ends_at = ends_at

        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        
    def __repr__(self):
        return f"Subscription(id={self.id}, user_id={self.user_id}, platform={self.platform}, active={self.active}, ends_at={self.ends_at})"
    
    @classmethod
    def get(cls, id: str):
        subscription = database.select("SELECT * FROM subscriptions WHERE id = ?", (id,), limit=1)
        if subscription:
            return cls(id=subscription['id'], user_id=subscription['user_id'], platform=subscription['platform'], active=subscription['active'], ends_at=subscription['ends_at'], created_at=subscription['created_at'], updated_at=subscription['updated_at'])
        return None
    
    @staticmethod
    def create(plan_id: str, platform: Literal['paypal', 'stripe']):
        if platform not in SUPPORTED_PAYMENT_PROVIDERS:
            raise ValueError("Unsupported payment provider")
        return create_billing_agreement(plan_id=plan_id, platform=platform)

    @property
    def user(self):
        if not self.user_id:
            return None
        from func.models.user import User
        return User.get(self.user_id)
    
    @property
    def plan(self):
        result = database.select("SELECT id FROM subscription_plans WHERE subscription_id = ?", (self.id,), limit=1)
        if result:
            return SubscriptionPlan.get(result['id']) if result else None
        return None

    @property
    def payment(self):
        result = database.select("SELECT payment_id FROM subscription_payments WHERE subscription_id = ?", (self.id,), limit=1)
        if result:
            return Payment.get(result['payment_id']) if result else None
        return None

    def add_payment(self, payment: Payment):
        database.query("INSERT INTO subscription_payments (subscription_id, payment_id, added_at) VALUES (%s, %s, %s)", (self.id, payment.id, datetime.now()))
    
    @classmethod
    def activate(cls, token: str, user_id: str, platform: Literal['paypal', 'stripe']):
        # Need fixed: this method should be a class method, not an instance method
        if platform == 'paypal':
            try:
                billing_agreement = paypalrestsdk.BillingAgreement.execute(token)

                if billing_agreement.success():
                    agreement_id = billing_agreement.id
                    ends_at = None
                    price = 0
                    plan_id = None

                    # auto_bill = billing_agreement.plan.merchant_preferences.auto_bill_amount == 'YES'

                    payment_definitions = billing_agreement.plan.payment_definitions
                    for payment_definition in payment_definitions:
                        if payment_definition.type == 'REGULAR':
                            price = float(payment_definition.amount.value)

                    # Extract plan_id from the description
                    subscription_description = billing_agreement.description                    
                    if "Plan ID" in subscription_description:
                        plan_id = int(subscription_description.split("Plan ID ")[-1].strip())
                        plan = get_plan(plan_id)  # Validate the plan ID

                        if plan:
                            ends_at = datetime.now() + timedelta(days=plan['billing_plans']['paypal']['frequency']['days'])

                    subscription = cls(id=agreement_id, user_id=user_id, platform=platform, ends_at=ends_at, active=True) # Create a new subscription object
                    subscription.save(insert=True) # Save the subscription to the database

                    SubscriptionPlan.create(
                        user_id=user_id,
                        subscription_id=subscription.id,
                        plan_id=plan_id,
                        expires_at=ends_at
                    )

                    payment = Payment.create(
                        user_id=user_id,
                        platform=platform,
                        amount=price,
                        reason="Subscription"
                    )
                    subscription.add_payment(payment) # Add the payment to the subscription
                    return subscription # Return the subscription object
                else:
                    print(billing_agreement.error)
                    return None
            except Exception as e:
                print(f"Exception during execution: {str(e)}")
        elif platform == 'stripe':
            try:
                # Retrieve the session from Stripe using the session_id
                checkout_session = stripe.checkout.Session.retrieve(token)
                
                if checkout_session.get('payment_status') == 'paid':
                    subscription_id = checkout_session.get('subscription')

                    # Retrieve the subscription details
                    subscription_object = stripe.Subscription.retrieve(subscription_id)
                    item = subscription_object['items']['data'][0]

                    # Price can be retrieved from the subscription object, based on the plan
                    price = subscription_object.plan.amount / 100  # Assuming amount is in cents, divide by 100 to get dollars

                    # Retrieve the product associated with the plan
                    product = stripe.Product.retrieve(item['price']['product'])
                    product_name = product['name']
                    
                    # Extract plan_id from the product name
                    plan_id = None
                    if product_name and "Plan ID" in product_name:
                        plan_id = int(product_name.split("Plan ID ")[-1].strip())

                    subscription = cls() # Create a new subscription object
                    return subscription.save(insert=True) # Save the subscription to the database
                else:
                    print("Payment not successful")
                    return None
            except Exception as e:
                print(f"Exception during execution: {str(e)}")
        return False
    
    def renew(self, expires_at: datetime):
        # Renew the subscription using the payment provider's API
        # For now, we will just set active to True and update the database
        if expires_at <= datetime.now():
            raise ValueError("Expiration date must be in the future")
        
        self.active = True
        self.updated_at = datetime.now()
        self.ends_at = expires_at

        # Update the subscription in the database
        database.query("UPDATE subscriptions SET active = %s, updated_at = %s, ends_at = %s, WHERE id = %s", (self.active, self.updated_at, self.ends_at, self.id))

        self.plan.renew(expires_at)

    def cancel(self):
        # Cancel the subscription using the payment provider's API
        # For now, we will just set active to False and update the database
        self.active = False
        self.updated_at = datetime.now()
        database.query("UPDATE subscriptions SET active = %s, updated_at = %s WHERE id = %s", (self.active, self.updated_at, self.id))

    def refresh(self):
        # Check if the subscription is active based on the current date and time
        # If refresh is True, it will fetch the latest status from the subscription service
        # For now, we will just return the active status from the database
        pass

    def to_dict(self):
        return {
            "id": self.id,
            "platform": self.platform,
            "active": self.active,
            "ends_at": self.ends_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def save(self, insert: bool = False):
        # Save the subscription to the database
        query = None
        params = ()

        if insert:
            query = "INSERT INTO subscriptions (id, user_id, platform, active, ends_at, created_at, updated_at) VALUES  (%s, %s, %s, %s, %s, %s, %s)"
            params = (self.id, self.user_id, self.platform, self.active, self.ends_at, self.created_at, self.updated_at)
        else:
            query = "UPDATE subscriptions SET user_id = %s, platform = %s, active = %s, ends_at = %s, updated_at = %s WHERE id = %s"
            params = (self.user_id, self.platform, self.active, self.ends_at, self.updated_at, self.id)

        database.query(query, params)
        return self

database.query("""CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ends_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)""")

database.query("""CREATE TABLE IF NOT EXISTS subscription_payments (
    subscription_id VARCHAR(36) NOT NULL,
    payment_id VARCHAR(36) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (subscription_id, payment_id),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
)""")