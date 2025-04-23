from func.models.database import database
from datetime import datetime
from func.models.media import Media
from func.utils import generate_unique_id

class Notification:
    def __init__(self, id: str, user_id: str, content: str, icon: Media = None, created_at: datetime = None):
        self.id = id
        self.user_id = user_id
        self.icon = icon
        self.content = content
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"Notification(id={self.id}, user_id={self.user_id}, content={self.content})"
    
    @classmethod
    def get(cls, id: str):
        result = database.select("SELECT * FROM notifications WHERE id = %s", (id,), limit=1)
        if result:
            return cls(
                id=result['id'],
                user_id=result['user_id'],
                content=result['content'],
                icon=Media.get(result['icon_id']) if result['icon_id'] is not None else None,
                created_at=result['created_at']
            )
        return None
    
    @classmethod
    def create(cls, user_id: str, content: str, icon: Media = None):
        id = generate_unique_id()
        notification = cls(id=id, user_id=user_id, content=content, icon=icon)
        return notification.save()
    
    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "icon": self.icon.url if self.icon else None,
            "created_at": self.created_at
        }
    
    def save(self):
        query = "INSERT INTO notifications (id, user_id, content, icon_id, created_at) VALUES (%s, %s, %s, %s, %s)"
        params = (self.id, self.user_id, self.content, self.icon.id if self.icon else None, self.created_at)

        database.query(query, params)
        return self
    
    def delete(self):
        query = "DELETE FROM notifications WHERE id = %s"
        params = (self.id,)

        database.query(query, params)   