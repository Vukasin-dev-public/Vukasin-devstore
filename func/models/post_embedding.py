from func.models.database import database
from sqlalchemy import Column, Integer, Float, ARRAY

class PostEmbedding(database):
    __tablename__ = 'post_embeddings'

    id = Column(Integer, primary_key=True)  # FAISS index ID
    post_id = Column(Integer, nullable=False, unique=True)  # Reference to the Post
    embedding = Column(ARRAY(Float), nullable=False)  # Embedding vector