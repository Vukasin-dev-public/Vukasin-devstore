from datetime import datetime
from func.models.database import database
from func.utils import generate_unique_id

class MediaType:
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"

    @classmethod
    def choices(cls):
        return [cls.IMAGE, cls.VIDEO, cls.AUDIO, cls.DOCUMENT]
    
    @classmethod
    def from_ext(cls, ext: str):
        if ext in ['png', 'jpg', 'jpeg', 'gif']:
            return cls.IMAGE
        elif ext in ['mp4', 'mov']:
            return cls.VIDEO
        elif ext in ['mp3', 'wav']:
            return cls.AUDIO
        elif ext in ['pdf', 'docx']:
            return cls.DOCUMENT
        else:
            raise ValueError("Unsupported file extension")

class Media:
    def __init__(self, id: str, media_type: MediaType, url: str, created_at: datetime = None):
        self.id = id
        self.media_type = media_type
        self.url = url
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"Media(id={self.id}, name={self.name}, type={self.type}, size={self.size}, url={self.url})"
    
    @classmethod
    def get(cls, id: str):
        result = database.select("SELECT * FROM media WHERE id = %s", (id,), limit=1)
        if result:
            return cls(
                id=result['id'],
                media_type=result['media_type'],
                url=result['url'],
                created_at=result['created_at']
            )
        return None
    
    @classmethod
    def create(cls, media_type: MediaType, url: str):
        id = generate_unique_id()
        media = cls(id=id, media_type=media_type, url=url)
        return media.save(insert=True)
    
    @classmethod
    def from_url(cls, url: str):
        result = database.select("SELECT * FROM media WHERE url = %s", (url,), limit=1)
        if result:
            return cls(
                id=result['id'],
                media_type=result['media_type'],
                url=result['url'],
                created_at=result['created_at']
            )
        return None
    
    def to_dict(self):
        return {
            "id": self.id,
            "media_type": self.media_type,
            "url": self.url,
            "created_at": self.created_at
        }
    
    def save(self, insert: bool = False):
        query = None
        params = ()

        if insert:
            query = "INSERT INTO media (id, media_type, url, created_at) VALUES (%s, %s, %s, %s)"
            params = (self.id, self.media_type, self.url, self.created_at)
        else:
            query = "UPDATE media SET media_type = %s, url = %s WHERE id = %s"
            params = (self.media_type, self.url, self.id)

        database.query(query, params)
        return self
    
    def delete(self):
        query = "DELETE FROM media WHERE id = %s"
        params = (self.id,)
        database.query(query, params)