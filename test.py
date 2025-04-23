from func.models.subscription import Subscription

subscription = Subscription.create("1", platform="stripe")
print(subscription)