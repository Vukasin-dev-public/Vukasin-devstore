from __future__ import annotations
from func.models.database import database
from typing import List
from datetime import datetime


class UserEmbedding:
    def __init__(self, id: int, user_id: str, embedding: List[float], created_at: datetime = None, updated_at: datetime = None):
        self.id = id
        self.user_id = user_id
        self.embedding = embedding
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    def __repr__(self):
        return f"UserEmbedding(id={self.id}, user_id={self.user_id}, embedding={self.embedding})"

    @classmethod
    def create(cls, user_id: str, embedding: List[float]):
        """
        Create a new user embedding record.
        """
        created_at = datetime.now()
        updated_at = datetime.now()
        query = "INSERT INTO user_embeddings (user_id, embedding, created_at, updated_at) VALUES (%s, %s, %s, %s) RETURNING id "
       # params = (user_id, embedding, created_at, updated_at)
        params = (user_id, embedding, datetime.now(), datetime.now())
        result = database.query(query, params)
        print(f"Executing query: {query}")
        print(f"With parameters: {params}")
        if not result:
            raise ValueError("Failed to insert user embedding into the database")
        return cls(
            id=result[0]['id'],  # Retrieve the auto-generated SERIAL id
            user_id=user_id,
            embedding=embedding,
            created_at=created_at,
            updated_at=updated_at
        )

    @classmethod
    def get(cls, user_id: str):
        """
        Retrieve a user embedding by user_id.
        """
       
        query = "SELECT * FROM user_embeddings WHERE user_id = %s"
        result = database.select(query, (user_id,), limit=1)
          
        if result:
            result = result
          
            return cls(
                id=result['id'],
                user_id=result['user_id'],
                embedding=result['embedding'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        return None

    def to_dict(self):
        """
        Convert the user embedding object to a dictionary.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def save(self, insert: bool = False):
        """
        Save the user embedding to the database.
        """
        if insert:
            query = """
                INSERT INTO user_embeddings (user_id, embedding, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO NOTHING
                RETURNING id
            """
            params = (self.user_id, self.embedding, self.created_at, self.updated_at)
            result = database.query(query, params)
            self.id = result[0]['id']  # Update the id with the auto-generated SERIAL id
        else:
            query = """
                UPDATE user_embeddings
                SET embedding = %s, updated_at = %s
                WHERE user_id = %s
            """
            params = (self.embedding, self.updated_at, self.user_id)

        database.query(query, params)
        return self

    def delete(self):
        """
        Delete the user embedding from the database.
        """
        query = "DELETE FROM user_embeddings WHERE user_id = %s"
        params = (self.user_id,)
        database.query(query, params)

    @classmethod
    def all(cls):
        """
        Retrieve all user embeddings from the database.
        """
        query = "SELECT * FROM user_embeddings"
        results = database.select(query)

        return [
            cls(
                id=result['id'],
                user_id=result['user_id'],
                embedding=result['embedding'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
            for result in results
        ]