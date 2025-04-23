from func.models.database import database
from func.payment_utils import (
    create_payment,
    execute_payment,
)
from func.utils import generate_unique_id
from datetime import datetime

# payments {
#   id string pk
#   user_id string fk
#   amount float
#   platform string // Paypal or Stripe...
#   payment_date timestamp
#   reason text
# }

class Payment:
    def __init__(self, id: str, user_id: str, amount: float, platform: str, payment_date: datetime, reason: str):
        self.id = id
        self.user_id = user_id
        self.amount = amount
        self.platform = platform
        self.payment_date = payment_date
        self.reason = reason

    def __repr__(self):
        return f"Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, platform={self.platform}, payment_date={self.payment_date}, reason={self.reason})"
    
    @classmethod
    def get(cls, id: str):
        payment = database.select("SELECT * FROM payments WHERE id = %s", (id,), limit=1)
        if payment:
            return cls(id=payment['id'], user_id=payment['user_id'], amount=payment['amount'], platform=payment['platform'], payment_date=payment['payment_date'], reason=payment['reason'])
        return None
    
    @classmethod
    def create(cls, user_id: str, amount: float, platform: str, reason: str):
        # Check if user_id exists in users table
        user = database.select("SELECT id FROM users WHERE id = %s", (user_id,), limit=1)
        if not user:
            raise ValueError("User ID does not exist")
        
        # Generate a unique ID for the payment
        # The payment ID should be the value of the payment_id provided by the API request from the payment provider
        # For now, we will just generate a random string as the ID
        id = generate_unique_id()
        
        payment = cls(id=id, user_id=user_id, amount=amount, platform=platform, payment_date=datetime.now(), reason=reason)
        return payment.save(insert=True)
    
    @property
    def user(self):
        from func.models.user import User
        return User.get(self.user_id)

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "platform": self.platform,
            "payment_date": self.payment_date,
            "reason": self.reason
        }
    
    def save(self, insert: bool = False):
        query = None
        params = ()

        if insert:
            query = "INSERT INTO payments (id, user_id, amount, platform, payment_date, reason) VALUES (%s, %s, %s, %s, %s, %s)"
            params = (self.id, self.user_id, self.amount, self.platform, self.payment_date, self.reason)
        else:
            query = "UPDATE payments SET user_id = %s, amount = %s, platform = %s, payment_date = %s, reason = %s WHERE id = %s"
            params = (self.user_id, self.amount, self.platform, self.payment_date, self.reason, self.id)
    
        database.query(query, params)
        return self
    
database.query("""
    CREATE TABLE IF NOT EXISTS payments (
        id VARCHAR(36) PRIMARY KEY,
        user_id VARCHAR(36) NOT NULL,
        amount FLOAT NOT NULL,
        platform VARCHAR(50) NOT NULL,
        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reason TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")