from flask import Blueprint, request, jsonify
from func.models.user_embedding import UserEmbedding
from scripts.ollama import store_embeddings, text_to_embedding
import numpy as np

friend_bp = Blueprint('friend', __name__)

@friend_bp.route('/friend-candidate', methods=['POST'])
def get_friend_candidate():
    """
    API to find the most similar user embedding and return the user_id.
    """
    from func.models.user import User
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400

    # Fetch the embedding for the given user_id
    user_embedding = UserEmbedding.get(user_id=user_id)
    if not user_embedding:
        return jsonify({'error': 'User embedding not found'}), 404

    # Fetch all embeddings from the database
    all_embeddings = UserEmbedding.all()

    # Prepare embeddings and user IDs for comparison
    embeddings = []
    user_ids = []
    for embedding_record in all_embeddings:
        if embedding_record.user_id != user_id:  # Exclude the current user
            embeddings.append(embedding_record.embedding)
            user_ids.append(embedding_record.user_id)

    if not embeddings:
        return jsonify({'error': 'No other embeddings found'}), 404

    # Convert embeddings to a NumPy array
    embeddings_np = np.array(embeddings).astype('float32')

    # Store embeddings in FAISS
    index = store_embeddings(embeddings_np)

    # Find the most similar embedding
    query_embedding = np.array(user_embedding.embedding).astype('float32')
    D, I = index.search(np.array([query_embedding]), 1)  # Search for the most similar embedding

    # Get the most similar user_id
    most_similar_user_id = user_ids[I[0][0]]
    user = User.get(id=user_id)
    if not user:
        raise ValueError("User not found")
    return jsonify({'friend_candidate': most_similar_user_id, 'name': user.username,'bio':user.bio}), 200