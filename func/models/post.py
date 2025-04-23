from __future__ import annotations 
from func.models.media import Media
from func.models.interest import Interest

from func.models.database import database
from func.utils import generate_unique_id
from typing import List, TYPE_CHECKING
from datetime import datetime
if TYPE_CHECKING:
    from func.models.message import Message
class PostComment:
    def __init__(self, id: str, user_id: str, post_id: str, content: str, created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.user_id = user_id
        self.post_id = post_id
        self.content = content

        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self):
        return f"PostComment(id={self.id}, user_id={self.user_id}, post_id={self.post_id}, content={self.content})"
    
    @property
    def user(self):
        from func.models.user import User
        return User.get(self.user_id)
    
    @property
    def post(self):
        return Post.get(self.post_id)

    @classmethod
    def create(cls, user_id: str, post_id: str, content: str):
        comment_id = generate_unique_id()
        comment = cls(id=comment_id, user_id=user_id, post_id=post_id, content=content)
        return comment.save(insert=True)
    
    @classmethod
    def get(cls, comment_id: str):
        comment = database.select("SELECT * FROM comments WHERE id = ?", (comment_id,), limit=1)

        if comment:
            comment = cls(
                id=comment['id'],
                user_id=comment['user_id'],
                post_id=comment['post_id'],
                content=comment['content'],
                created_at=comment['created_at']
            )
            return comment
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.to_dict(minimized=True),
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def save(self, insert: bool = False):
        query = None
        params = ()

        if insert:
            query = "INSERT INTO comments (id, user_id, post_id, content, created_at) VALUES (?, ?, ?, ?, ?)"
            params = (self.id, self.user_id, self.post_id, self.content, self.created_at)
        else:
            query = "UPDATE comments SET content = ?, updated_at = ? WHERE id = ?"
            params = (self.content, self.updated_at, self.id)

        database.query(query, params)
        return self
    
    def delete(self):
        query = "DELETE FROM comments WHERE id = ?"
        params = (self.id,)

        database.query(query, params)

class Post:
    def __init__(self, id: str, user_id: str, title: str, content: str, created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.content = content
        self.created_at = created_at if created_at else datetime.now()
        self.updated_at = updated_at if updated_at else datetime.now()

    def __repr__(self):
        return f"Post(id={self.id}, user_id={self.user_id}, title={self.title}, content={self.content})"

    @classmethod
    def create(cls, user_id: str, title: str, content: str):
        from func.models.user_embedding import UserEmbedding
        from scripts.ollama import text_to_embedding      
        from func.models.user import User
        from func.models.interest import Interest
        
        
        post_id = generate_unique_id()
        post = cls(id=post_id, user_id=user_id, title=title, content=content)
        post.save(insert=True)
        user = User.get(id=user_id)
        if not user:
            raise ValueError("User not found")
        bio = user.bio or ""

         # Fetch the user's interests
        interests = Interest.get(id=user_id)
        if interests is None:
            interests_text=""
        else:
            interests_text = " ".join([interest.name for interest in interests]) if interests else ""

        # Fetch the user's posts
        

        # Combine all text data
        combined_text = f"{bio} {interests_text} {title} {content}"
        #user_text = f"{title} {content}"  # Combine the title and content of the post
        embedding = text_to_embedding(combined_text)  # Generate the embedding for the post content
        
        if embedding is not None:
            # Update the user's embedding in the user_embeddings table
            existing_embedding = UserEmbedding.get(user_id=user_id)
           
        if existing_embedding:
            # Update the existing embedding
            existing_embedding.embedding = embedding.tolist()
            existing_embedding.updated_at = datetime.now()
            existing_embedding.save()
           
        else:
            # Create a new embedding record if it doesn't exist
            UserEmbedding.create(user_id=user_id, embedding=embedding.tolist())
         
        return post
    @classmethod
    def get(cls, post_id: str):
        post = database.select("SELECT * FROM posts WHERE id = ?", (post_id,), limit=1)

        if post:
            post = cls(
                id=post['id'],
                user_id=post['user_id'],
                title=post['title'],
                content=post['content'],
                created_at=post['created_at'],
                updated_at=post['updated_at']
            )
            return post
        return None
    
    @property
    def user(self):
        from func.models.user import User
        return User.get(self.user_id)
    
    @property
    def comments(self) -> List[PostComment]:
        query = "SELECT id FROM comments WHERE post_id = ?"
        results = database.select(query, (self.id,))
        
        if results:
            return [PostComment.get(id) for id in results]
        return []

    @property
    def medias(self) -> List[Media]:
        query = "SELECT media_id FROM post_media WHERE post_id = ?"
        media_ids = database.select(query, (self.id,))
        
        medias = []
        if media_ids:
            for media_id in media_ids:
                if media_id:
                    media = Media.get(media_id)
                    if media:
                        medias.append(media)
        return medias
    
    @property
    def interests(self) -> List[Interest]:
        query = "SELECT interest_id FROM post_interests WHERE post_id = ?"
        interest_ids = database.select(query, (self.id,))
        
        interests = []
        if interest_ids:
            for interest_id in interest_ids:
                if interest_id:
                    interest = Interest.get(interest_id)
                    if interest:
                        interests.append(interest)
        return interests
    
    @property
    def messages(self) -> List[Message]:
        query = "SELECT message_id FROM post_messages WHERE post_id = %s"
        message_ids = database.select(query, (self.id,))

        messages = []
        if message_ids:
            for message_id in message_ids:
                if message_id:
                    message = Message.get(message_id)
                    if message:
                        messages.append(message)
        return messages
    
    @property
    def likes(self):
        query = "SELECT user_id FROM post_likes WHERE post_id = ?"
        user_ids = database.select(query, (self.id,))

        users = []
        if user_ids:
            from func.models.user import User
            for user_id in user_ids:
                if user_id:
                    user = User.get(user_id)
                    if user:
                        users.append(user)
        return users

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "medias": [media.url for media in self.medias],
            "interests": [interest.to_dict() for interest in self.interests],
            "comments": [comment.to_dict() for comment in self.comments],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def add_media(self, media: Media):
        database.query("INSERT INTO post_media (post_id, media_id) VALUES (?, ?)", (self.id, media.id))

    def add_interest(self, interest: Interest):
        database.query("INSERT INTO post_interests (post_id, interest_id) VALUES (?, ?)", (self.id, interest.id))

    def add_message(self, message: Message):
        database.query("INSERT INTO post_messages (post_id, message_id) VALUES (%s, %s)", (self.id, message.id))

    def add_like(self, from_user):
        from func.models.user import User
        if not isinstance(from_user, User):
            raise ValueError("Invalid user type. Expected an instance of User.")
        
        query = "INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)"
        database.query(query, (self.id, from_user.id))

    def save(self, insert: bool = False):
        query = None
        params = ()

        if insert:
            query = "INSERT INTO posts (id, user_id, title, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
            params = (self.id, self.user_id, self.title, self.content, self.created_at, self.updated_at)
        else:
            query = "UPDATE posts SET title = ?, content = ?, updated_at = ? WHERE id = ?"
            params = (self.title, self.content, self.updated_at, self.id)

        database.query(query, params)
        
        return self
    
    def delete(self):
        database.query("DELETE FROM posts WHERE id = ?", (self.id,))
