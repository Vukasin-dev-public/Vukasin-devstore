from datetime import datetime
from func.models.user import User
from func.models.message import Message
from func.models.database import database
from func.utils import generate_unique_id

class ChatRoom:
    def __init__(self, id: str, name: str, admin: User, description: str = None, is_private: bool = False, created_at: datetime = None):
        self.id = id
        self.name = name
        self.description = description

        self.is_private = is_private
        self.created_at = created_at or datetime.now()

        self.admin = admin

    def __repr__(self):
        return f"ChatRoom(id={self.id}, name={self.name}, admin={self.admin}, is_private={self.is_private}, created_at={self.created_at})"
    
    @classmethod
    def get(cls, id: str):
        result = database.select("SELECT * FROM chat_rooms WHERE id = %s", (id,), limit=1)
        if result:
            return cls(id=id, name=result['name'], admin=User.get(result['admin_id']), is_private=False)
        return None

    @classmethod
    def create(cls, name: str, admin: User, description: str = None, is_private: bool = False):
        chat_room_id = generate_unique_id()
        chat_room = cls(id=chat_room_id, name=name, admin=admin, description=description, is_private=is_private)
        return chat_room.save(insert=True)
    
    @property
    def members(self):
        result = database.select("SELECT user_id FROM user_chat_rooms WHERE chat_room_id = %s", (self.id,))
        if result:
            members = [User.get(user['user_id']) for user in result]
            return members
        return []
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "admin": self.admin.to_dict(),
            "description": self.description,
            "is_private": self.is_private,
            "created_at": self.created_at
        }

    def add_member(self, user: User):
        accepted = not self.is_private
        database.insert("INSERT INTO user_chat_rooms (user_id, chat_room_id, accepted) VALUES (%s, %s, %s)", (user.id, self.id, accepted))            

    def add_message(self, message: Message):
        database.insert("INSERT INTO messages (id, chat_room_id, content, sender_id, created_at) VALUES (%s, %s, %s, %s, %s)", (message.id, self.id, message.content, message.sender.id, message.created_at))

    def save(self, insert: bool = False):
        query = None
        params = ()

        if insert:
            query = "INSERT INTO chat_rooms (id, name, admin_id, description, is_private, created_at) VALUES (%s, %s, %s, %s, %s, %s)"
            params = (self.id, self.name, self.admin.id, self.description, self.is_private, self.created_at)
        else:
            query = "UPDATE chat_rooms SET name = %s, admin_id = %s, description = %s, is_private = %s WHERE id = %s"
            params = (self.name, self.admin.id, self.description, self.is_private, self.id)

        database.query(query, params)
        return self

    def delete(self):
        database.query("DELETE FROM chat_rooms WHERE id = %s", (self.id,))