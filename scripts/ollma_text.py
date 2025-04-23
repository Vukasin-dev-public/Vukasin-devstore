import faiss
import numpy as np
import ollama

def text_to_embedding_ollama(text):
    model_name = "llama2" 
    response = ollama.embed(model=model_name, input=text)
    
    # Extract the embeddings from the response dictionary
    if 'embeddings' in response:
        embedding = response['embeddings'][0]  # Assuming the embedding is in the first element
        #print(f"embedding: ")
        return np.array(embedding)
        
    else:
        print("Error: 'embeddings' key not found in the response.")
        return None

sentences = [
    
    "Tamer",
    "b",
    "Tamer"
]

# Get embeddings for all sentences
embeddings = [text_to_embedding_ollama(sentence) for sentence in sentences]

# Filter out None values (in case of errors)
embeddings = [embedding for embedding in embeddings if embedding is not None]

print(f"embeddings:{len(embeddings[0])}")
print(f"embeddings:{(embeddings[0])}")
print(f"embeddings:{(embeddings[1])}")
print(f"embeddings:{(embeddings[2])}")
# If embeddings exist, proceed with FAISS
if embeddings:
    embeddings_np = np.array(embeddings).astype('float32')

    # Using FAISS for similarity search
    dimension = embeddings_np.shape[1]  # Dimension of the embedding vectors
    index = faiss.IndexFlatL2(dimension)  # Index for L2 distance
    print(f"dimension:{dimension}")
    print(f"index:{index.ntotal}")
    # Add embeddings to the index
    index.add(embeddings_np)

    # Perform a search with one of the embeddings to find the most similar ones
    D, I = index.search(embeddings_np, 3)  # 3 nearest neighbors


    print("Indices of the closest sentences:", I)
    print("Distances to the closest sentences:", D)
else:
    print("No valid embeddings found.")



