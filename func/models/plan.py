from func.models.database import database
from func.utils import generate_unique_id, load_json
from datetime import datetime
from func.constants import PLANS_JSON_FILE_PATH

# plans {
#   id string pk
#   user_id string fk not null
#   plan_id string not null // Get from plans.json, where plan properties and description is listed
#   subscription_id string fk not null
#   cycles int // How many times it was updated, or renewed
#   expires_at timestamp
# }

def get_plan(plan_id: str) -> dict:
    plans = load_json(PLANS_JSON_FILE_PATH)

    plan = plans.get(plan_id, {})
    if plan:
        plan['id'] = plan_id
    return plan        

class SubscriptionPlan:
    def __init__(self, id: str, user_id: str, subscription_id: str, plan_id: str, cycles: int, expires_at: datetime):
        self.id = id
        self.user_id = user_id
        self.subscription_id = subscription_id
        self.plan_id = plan_id
        self.cycles = cycles
        self.expires_at = expires_at

    def __repr__(self):
        return f"Plan(id={self.id}, user_id={self.user_id}, subscription_id={self.subscription_id}, plan_id={self.plan_id}, cycles={self.cycles}, expires_at={self.expires_at})"
    
    @classmethod
    def get(cls, id: str):
        plan = database.select("SELECT * FROM plans WHERE id = ?", (id,), limit=1)
        if plan:
            return cls(id=plan['id'], user_id=plan['user_id'], subscription_id=plan['subscription_id'], plan_id=plan['plan_id'], cycles=plan['cycles'], expires_at=plan['expires_at'])
        return None

    @classmethod
    def create(cls, user_id: str, subscription_id: str, plan_id: str, expires_at: datetime):
        if not get_plan(plan_id):
            raise ValueError("Invalid plan ID")
        
        id = generate_unique_id()
        plan = cls(id=id, user_id=user_id, subscription_id=subscription_id, plan_id=plan_id, expires_at=expires_at)
        return plan.save(insert=True)
    
    @property
    def user(self):
        from func.models.user import User
        return User.get(self.user_id)
    
    @property
    def subscription(self):
        from func.models.subscription import Subscription
        return Subscription.get(self.subscription_id)
    
    @property
    def plan(self):
        return get_plan(self.plan_id)
    
    @property
    def active(self):
        return self.subscription.active
    
    @property
    def expired(self):
        return self.expires_at < datetime.now()

    @property
    def properties(self):
        return self.plan.get("properties", {})

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.as_dict(),
            "subscription": self.subscription.as_dict(),
            "plan": self.plan,
            "cycles": self.cycles,
            "expires_at": self.expires_at.isoformat(),
        }
    
    def renew(self, expires_at: datetime):
        if expires_at <= datetime.now():
            raise ValueError("Expiration date must be in the future")
        
        self.cycles += 1
        self.expires_at = expires_at
        database.query("UPDATE plans SET cycles = %s, expires_at = %s WHERE id = %s", (self.cycles, self.expires_at, self.id))

        return self
    
    def cancel(self):
        self.subscription.cancel()

    def save(self, insert: bool = False):
        query = None
        params = ()

        if insert:
            query = "INSERT INTO plans (id, user_id, subscription_id, plan_id, cycles, expires_at) VALUES (%s, %s, %s, %s, %s, %s)"
            params = (self.id, self.user_id, self.subscription_id, self.plan_id, self.cycles, self.expires_at)
        else:
            query = "UPDATE plans SET user_id = %s, subscription_id = %s, plan_id = %s, cycles = %s, expires_at = %s WHERE id = %s"
            params = (self.user_id, self.subscription_id, self.plan_id, self.cycles, self.expires_at, self.id)

        database.query(query, params)
        return self

database.query("""CREATE TABLE IF NOT EXISTS subscription_plans (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    subscription_id VARCHAR(255) NOT NULL,
    plan_id VARCHAR(255) NOT NULL,
    cycles INT DEFAULT 0,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
)""")