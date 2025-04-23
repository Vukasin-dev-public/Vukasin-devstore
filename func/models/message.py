from datetime import datetime
from func.models.media import Media

from func.models.database import database
from func.utils import generate_unique_id
from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from func.models.user import User
class Message:
    def __init__(self, id: str, chat_room_id: str, content: str, sender_id: str, created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.chat_room_id = chat_room_id
        self.content = content

        self.sender_id = sender_id

        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self):
        return f"Message(sender={self.sender}, recipient={self.recipient}, content={self.content})"
    
    @classmethod
    def get(cls, id: str):
        result = database.select("SELECT * FROM messages WHERE id = %s", params=(id,), limit=1)
        if result:
            return cls(
                id=result["id"],
                chat_room_id=result["chat_room_id"],
                content=result["content"],
                sender_id=result['sender_id'],
                created_at=result["created_at"],
                updated_at=result["updated_at"],
            )
        return None

    @classmethod
    def create(cls, chat_room_id: str, content: str, sender_id: str, medias: List[Media] = []):
        message_id = generate_unique_id()
        message = cls(
            id=message_id,
            chat_room_id=chat_room_id,
            content=content,
            sender_id=sender_id,
        )
        message.save(insert=True)

        # Save associated medias
        for media in medias:
            message.add_media(media)

        return message
    
    def to_dict(self):
        return {
            "id": self.id,
            "chat_room_id": self.chat_room_id,
            "content": self.content,
            "sender": self.sender.to_dict(minimized=True),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "read_by": [user.to_dict() for user in self.read_by],
            "medias": [media.to_dict() for media in self.medias]
        }
    
    @property
    def sender(self):
        if self.sender_id:
            return User.get(id=self.sender_id)
        return None

    @property
    def read_by(self):
        user_ids = database.select("SELECT user_id FROM message_read_by WHERE message_id = %s", params=(self.id, ))

        users = []
        for user_id in user_ids:
            user = User.get(id=user_id)
            if user:
                users.append(user)
        
        return users
    
    @property
    def media(self):
        media_ids = database.select("SELECT media_id FROM message_medias WHERE message_id = %s", params=(self.id,))

        medias = []
        for media_id in media_ids:
            media = Media.get(media_id)
            if media:
                medias.append(media)

        return medias

    @property
    def chat_room(self):
        from func.models.chat_room import ChatRoom
        if self.chat_room_id:
            return ChatRoom.get(self.chat_room_id)
        return None
    
    @property
    def post(self):
        result = database.select("SELECT post_id FROM post_chat_rooms WHERE chat_room_id = %s", params=(self.chat_room_id), limit=1)
        if result:
            post_id = result["post_id"]
            if post_id:
                from func.models.post import Post
                return Post.get(post_id)
        return None

    def read_by(self, user: User):
        if user not in self.read_by:
            self.read_by.append(user)
            database.query("INSERT INTO message_read_by (message_id, user_id) VALUES (%s, %s)", params=(self.id, user.id))

        return self.read_by
    
    def add_media(self, media: Media):
        database.query("INSERT INTO message_media (message_id, media_id) VALUES (%s, %s)", params=(self.id, media.id))
    
    def save(self, insert: bool = False):
        query = None
        params = ()

        if insert:
            query = "INSERT INTO messages (id, chat_room_id, content, sender_id) VALUES (%s, %s, %s, %s)"
            params = (self.id, self.chat_room_id, self.content, self.sender_id)
        else:
            self.updated_at = datetime.now()

            query = "UPDATE messages SET content = %s, updated_at = %s WHERE id = %s"
            params = (self.content, self.updated_at, self.id)

        database.query(query, params)
        return self
        
    def delete(self):
        # Delete associated medias
        for media in self.medias:
            media.delete()

        # This method deletes the message from the database
        database.query("DELETE FROM messages WHERE id = %s", (self.id,))