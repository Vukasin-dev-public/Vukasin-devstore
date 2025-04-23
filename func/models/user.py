from __future__ import annotations 
from datetime import datetime
from scripts.ollama import text_to_embedding

import re
from typing import List , TYPE_CHECKING
from func.models.media import Media
from func.models.interest import Interest

from func.models.notification import Notification
from func.models.database import database

from func.utils import generate_unique_id, hash_password, verify_password, validate_email, validate_username, validate_password

if TYPE_CHECKING:
    from func.models.post import Post 
class User:
    def __init__(self, id: str, username: str, email: str, password_hash: str, bio: str = None, 
                 is_private: bool = False, avatar: Media = None, created_at: datetime = None, updated_at: datetime = None,
                 google_id: str = None, apple_id: str = None):
        self.id = id
        self.username = username 
        self.email = email
        self.password_hash = password_hash
        self.bio = bio
        self.is_private = is_private
        self.avatar = avatar

        self.google_id = google_id
        self.apple_id = apple_id

        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self):
        return f"User(id={self.id}, username={self.username}, email={self.email}, bio={self.bio}, is_private={self.is_private})"

    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, User):
            return self.id == other.id
        return False

    @classmethod
    def get(cls, id: str = None, username: str = None, email: str = None, google_id: str = None, apple_id: str = None):
        if all(param is None for param in [id, username, email, google_id, apple_id]):
            raise ValueError("At least one parameter must be provided")
        
        query_parts = []
        params = []
        
        if id is not None:
            query_parts.append("id = %s")
            params.append(id)
        if username is not None:
            query_parts.append("username = %s")
            params.append(username)
        if email is not None:
            query_parts.append("email = %s")
            params.append(email)
        if google_id is not None:
            query_parts.append("google_id = %s")
            params.append(google_id)
        if apple_id is not None:
            query_parts.append("apple_id = %s")
            params.append(apple_id)
            
        query = f"SELECT * FROM users WHERE {' OR '.join(query_parts)} LIMIT 1"
        result = database.select(query, params, limit=1)
        
        if not result:
            return None
            
        return cls(
            id=result['id'],
            username=result['username'],
            email=result['email'],
            password_hash=result['password_hash'],
            bio=result.get('bio'),
            is_private=result.get('is_private', False),
            avatar=Media.get(result['avatar_id']) if result['avatar_id'] else None,
            created_at=result.get('created_at'),
            updated_at=result.get('updated_at'),
            google_id=result.get('google_id'),
            apple_id=result.get('apple_id')
        )

    @classmethod
    def create(cls, username: str, email: str, password: str, bio: str = None,
               is_private: bool = False, avatar: Media = None, google_id: str = None, apple_id: str = None):
        from func.models.user_embedding import UserEmbedding  # Import UserEmbedding here to avoid circular imports
        from scripts.ollama import text_to_embedding 
        password_hash = hash_password(password) if password else None
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email format")
            
        user_id = generate_unique_id()

        # Check if the username or email already exists
        existing_user = cls.get(username=username)
        if existing_user:
            raise ValueError("Username already exists")
        
        existing_user = cls.get(email=email)
        if existing_user:
            raise ValueError("Email already exists")

        # Checking if user exists with Google ID or Apple ID
        if google_id:
            existing_user = cls.get(google_id=google_id)
            if existing_user:
                return existing_user
                
        if apple_id:
            existing_user = cls.get(apple_id=apple_id)
            if existing_user:
                return existing_user
        
        user = cls(
            id=user_id, 
            username=username, 
            email=email, 
            password_hash=password_hash, 
            bio=bio, 
            is_private=is_private, 
            avatar=avatar, 
            google_id=google_id,
            apple_id=apple_id
        )
        
        user = user.save(insert=True)
        return user

    @classmethod
    def authenticate(cls, login: str, password: str):
        """Authenticate a user by username/email and password"""
        user = cls.get(username=login)
        
        # If user not found, try email
        if not user:
            user = cls.get(email=login)
            
        # If still not found or password doesn't match, return None
        if not user or not verify_password(password, user.password_hash):
            return None
            
        return user
        
    @classmethod
    def find_by_username_prefix(cls, prefix: str, limit: int = 5) -> List['User']:
        """Find users by username prefix"""
        if len(prefix) < 3:
            return []
            
        query = "SELECT id FROM users WHERE username LIKE %s LIMIT %s"
        params = (f"{prefix}%", limit)
        
        results = database.select(query, params)
        return [cls.get(id) for id in results]
        
    @classmethod
    def username_exists(cls, username: str):
        """Check if a username already exists"""
        query = "SELECT EXISTS(SELECT 1 FROM users WHERE username = %s)"
        result = database.select(query, (username,), limit=1)
        return result
    
    @classmethod
    def email_exists(cls, email: str):
        """Check if a username already exists"""
        query = "SELECT EXISTS(SELECT 1 FROM users WHERE email = %s)"
        result = database.select(query, (email,), limit=1)
        return result

    @classmethod
    def authenticate_with_google(cls, google_id: str, email: str, name: str = None):
        """Authenticate or create a user with Google credentials"""
        user = cls.get(google_id=google_id)
        
        if user:
            return user
            
        # If user not found by google_id, try by email
        user = cls.get(email=email)
        
        if user:
            # Update existing user with Google ID
            user.google_id = google_id
            user.save()
            return user
            
        # Create new user if not found
        username = email.split('@')[0]
        # Ensure username is unique
        base_username = username
        counter = 1
        while cls.username_exists(username):
            username = f"{base_username}{counter}"
            counter += 1
            
        return cls.create(
            username=username,
            email=email,
            bio=None,
            google_id=google_id
        )
        
    @classmethod
    def authenticate_with_apple(cls, apple_id: str, email: str = None):
        """Authenticate or create a user with Apple credentials"""
        user = cls.get(apple_id=apple_id)
        
        if user:
            return user
            
        # If user not found by apple_id and email is provided, try by email
        if email:
            user = cls.get(email=email)
            
            if user:
                # Update existing user with Apple ID
                user.apple_id = apple_id
                user.save()
                return user
                
            # Create new user if not found
            username = email.split('@')[0]
            # Ensure username is unique
            base_username = username
            counter = 1
            while cls.username_exists(username):
                username = f"{base_username}{counter}"
                counter += 1
                
            return cls.create(
                username=username,
                email=email,
                bio=None,
                apple_id=apple_id
            )
        
        return None

    def to_dict(self, include_private=False, minimized=False) -> dict:
        """Convert user object to dictionary"""
        user_dict = {
            "username": self.username,
            "bio": self.bio,
            "is_private": self.is_private,
            "avatar": self.avatar.url if self.avatar else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if not minimized:
            user_dict.update({
                "interests": [interest.to_dict() for interest in self.interests] if not self.is_private or include_private else len(self.interests),
                "posts": [post.to_dict() for post in self.posts] if not self.is_private or include_private else len(self.posts),
                "followers": [follower.to_dict(minimized=True) for follower in self.followers] if not self.is_private or include_private else len(self.followers),
                "following": [followee.to_dict(minimized=True) for followee in self.following] if not self.is_private or include_private else len(self.following),
            })

        if include_private:
            user_dict.update({
                "id": self.id,
                "email": self.email,
                "notifications": [notification.to_dict() for notification in self.notifications] if not self.is_private else [],
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "has_google_auth": bool(self.google_id),
                "has_apple_auth": bool(self.apple_id),
            })
            
        return user_dict

    def set_private(self, private: bool = True):
        if self.is_private == private:
            return True
        
        self.is_private = private
        database.query("UPDATE users SET is_private = %s WHERE id = %s", params=(private, self.id))

    def change_password(self, new_password: str):
        success, errors = validate_password(new_password)
        if not success:
            return errors
        
        new_password_hash = hash_password(new_password)
        if self.password_hash == new_password_hash:
            return ["New password should be different from the old one."]
        
        self.password_hash = new_password_hash
        database.query("UPDATE users SET password_hash = %s WHERE id = %s", params=(new_password_hash, self.id))

        return errors

    def change_username(self, new_username: str):
        if User.username_exists(new_username):
            return [f"Username ({new_username}) already exists."]
        
        success, errors = validate_username(new_username)
        if not success:
            return errors

        self.username = new_username
        database.query("UPDATE users SET username = %S WHERE id = %s", params=(new_username, self.id))

        return errors
    
    def change_email(self, new_email: str):
        if User.email_exists(new_email):
            return [f"Email ({new_email}) already exists."]
        
        if not validate_email(new_email):
            return [f"Email ({new_email}) is not valid."]
        
        self.email = new_email
        database.query("UPDATE users SET email = %s WHERE id = %s", params=(new_email, self.id))
        return []

    @property
    def followers(self) -> List['User']:
        query = "SELECT follower_id FROM follows WHERE followee_id = %s AND accepted = %s"
        params = (self.id, True)

        result = database.select(query, params)
        if result:
            return [User.get(user_id) for user_id in result]
        return []

    @property
    def following(self) -> List['User']:
        query = "SELECT followee_id FROM follows WHERE follower_id = %s AND accepted = %s"
        params = (self.id, True)

        result = database.select(query, params)
        if result:
            return [User.get(user_id) for user_id in result]
        return []
    
    def follower_requests(self, accepted: bool = False) -> List['User']:
        query = "SELECT follower_id FROM follows WHERE followee_id = %s AND accepted = %s"
        result = database.select(query, (self.id, accepted))
        if result:
            return [User.get(user_id) for user_id in result]
        return []
    
    def following_requests(self, accepted: bool = False) -> List['User']:
        query = "SELECT followee_id FROM follows WHERE follower_id = %s AND accepted = %s"
        result = database.select(query, (self.id, accepted))
        if result:
            return [User.get(user_id) for user_id in result]
        return []

    @property
    def posts(self) -> List[Post]:
        from func.models.post import Post

        query = "SELECT id FROM posts WHERE user_id = %s"
        result = database.select(query, (self.id,))
        if result:
            return [Post.get(post_id) for post_id in result]
        return []

    @property
    def interests(self) -> List[Interest]:
        query = "SELECT interest_id FROM user_interests WHERE user_id = %s"
        result = database.select(query, (self.id,))
        if result:
            return [Interest.get(interest_id) for interest_id in result]
        return []

    @property
    def notifications(self) -> List[Notification]:
        query = "SELECT id FROM notifications WHERE user_id = %s"
        result = database.select(query, (self.id,))
        if result:
            return [Notification.get(notification_id) for notification_id in result]
        return []

    def follow_user(self, user: 'User'):
        """Returns True if the follow request has been accepted automatically, or False, if pending"""
        accepted = not user.is_private

        query = "INSERT INTO follows (follower_id, followee_id, accepted) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
        database.query(query, (self.id, user.id, accepted))

        if not accepted:
            self.add_notification(
                content=f"Your follow request has been sent to {user.username}!"
            )
            self.add_notification(
                content=f"You have a new follow request from {self.username}."
            )
        else:
            self.add_notification(
                content=f"You have started following {user.username}!"
            )
            self.add_notification(
                content=f"{self.username} have started following you!"
            )

        return accepted

    def accept_follow(self, user: 'User'):
        """Returns False on error, and True when the follow request has been accepted"""
        follower_requests = self.follower_requests()
        if not user in follower_requests:
            return False
        
        query = "UPDATE follows SET accepted = %s WHERE follower_id = %s AND followee_id = %s"
        params = (True, user.id, self.id)

        database.query(query, params)

        self.add_notification(
            content=f"You have accepted {user.username} follow request."
        )
        self.add_notification(
            content=f"You have started following {self.username}."
        )
        return True

    def unfollow_user(self, user: 'User'):
        """Unfollow a user"""
        query = "DELETE FROM follows WHERE follower_id = %s AND followee_id = %s"
        database.query(query, (self.id, user.id))

    def is_following(self, user: 'User'):
        """Check if this user is following another user"""
        query = "SELECT EXISTS(SELECT 1 FROM follows WHERE follower_id = %s AND followee_id = %s)"
        result = database.select(query, (self.id, user.id), limit=1)
        return result

    def remove_post(self, post: Post):
        """Remove a post from user's profile"""
        post.delete()
    
    def add_interest(self, interest: Interest):
        """Add an interest to user's profile"""
        if interest in self.interests:
            print("Interest already exists in user's profile")
            return
        
        query = "INSERT INTO user_interests (user_id, interest_id) VALUES (%s, %s) ON CONFLICT DO NOTHING"
        database.query(query, (self.id, interest.id))

        self.add_notification(
            content=f"You have added {interest.name} to your interests.",
            icon=Media.get("interest_icon")
        )
    
    def remove_interest(self, interest: Interest):
        """Remove an interest from user's profile"""
        query = "DELETE FROM user_interests WHERE user_id = %s AND interest_id = %s"
        database.query(query, (self.id, interest.id))

    def add_notification(self, content: str, icon: Media = None):
        return Notification.create(
            user_id=self.id,
            content=content,
            icon=icon
        )
    
    def remove_notification(self, notification: Notification):
        """Remove a notification from user's profile"""
        notification.delete()

    def activate_subscription(self, token: str, platform: str):
        """Activate a subscription for the user"""
        from func.models.subscription import Subscription
        subscription = Subscription.activate(token, self.id, platform)
        if isinstance(subscription, Subscription):
            return subscription
        
        # Handle errors based on the subscription status
        if subscription is None:
            self.add_notification(
                content="Subscription activation failed. Please contact support.", 
                icon=Media.get("error_icon")
            )
        elif subscription == False:
            self.add_notification(
                content="An error occurred while activating your subscription. Please contact support.",
                icon=Media.get("error_icon") 
            )
    
    def save(self, insert: bool = False):
        """Save user changes to database"""
        query = None
        params = ()

        self.updated_at = datetime.now()
        avatar_id = self.avatar.id if self.avatar else None

        if insert:
            query = """
                INSERT INTO users (id, username, email, password_hash, bio, is_private, 
                                avatar_id, updated_at, google_id, apple_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING
            """

            params = (
                self.id, self.username, self.email, self.password_hash, self.bio, 
                self.is_private, avatar_id, self.updated_at, self.google_id, self.apple_id
            )
        else:
            query = """
                UPDATE users 
                SET username = %s, email = %s, password_hash = %s, bio = %s, 
                    is_private = %s, avatar_id = %s, updated_at = %s, google_id = %s, apple_id = %s
                WHERE id = %s
            """

            params = (
                self.username, self.email, self.password_hash, self.bio, 
                self.is_private, avatar_id, self.updated_at, self.google_id, self.apple_id,
                self.id
            )
        
        database.query(query, params)
        return self