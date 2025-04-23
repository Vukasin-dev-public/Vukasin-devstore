import faiss
import numpy as np
from sentence_transformers import SentenceTransformer  #import sentence_transformers
  # Import your Post model

model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L6-v2')


def text_to_embedding(text):
    embedding = model.encode(text)
    return embedding

def store_embeddings(embeddings):
    dimension = len(embeddings[0])  
    index = faiss.IndexFlatL2(dimension)  
    embeddings_np = np.array(embeddings).astype('float32')  
    index.add(embeddings_np) 
    return index


def find_most_similar(query_embedding, index, sentences):
    D, I = index.search(np.array([query_embedding]), 1)  
    return sentences[I[0][0]]  

def generate_embedding_for_post(post):
    from func.models.post import Post
    post_text = f"{post.title} {post.content} {post.interest}"  # Combine title and content
    embedding = text_to_embedding(post_text)  # Generate embedding

    # Store embedding in FAISS
    index = store_embeddings([embedding])  # Store a single embedding

    return index, embedding
def generate_embedding_for_user(user):
    
    """
    Generate and store embeddings for a single user.
    
    """
    user_text = f"{user.bio} {','.join(user.tags)}"  # Combine bio and tags
    embedding = text_to_embedding(user_text)  # Generate embedding

    # Store embedding in FAISS
    index = store_embeddings([embedding])  # Store a single embedding

    return index, embedding
'''sentences = [
    "I go to school.",
    "I am school boy",
    "I have a breakfast.",
    "I have a lunch.",
    "I like her.",
    "I like a dog.",
    "He is angry.",
    "she is pretty.",
    "Why don't you have breakfast?"
]



embeddings = [text_to_embedding(sentence) for sentence in sentences]

# FAISS
index = store_embeddings(embeddings)


query = input("insert your query: ")
query_embedding = text_to_embedding(query)


most_similar_sentence = find_most_similar(query_embedding, index, sentences)
print(f"اmost similar sentence {most_similar_sentence}")'''