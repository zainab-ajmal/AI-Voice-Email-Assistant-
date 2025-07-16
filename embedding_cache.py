from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from db import tokens_collection
from gmail_metadata import get_user_metadata

model = SentenceTransformer('all-MiniLM-L6-v2')

def build_user_embedding_cache(user_email):
    data = get_user_metadata(user_email)
    threads = data.get("recent_threads", [])
    
    texts = []
    metadata = []
    
    for thread in threads:
        combined = f"{thread.get('subject', '')} {thread.get('snippet', '')}"
        texts.append(combined)
        metadata.append({
            "subject": thread.get('subject', ''),
            "from": thread.get('from', ''),
            "date": thread.get('date', '')
        })
    
    embeddings = model.encode(texts, convert_to_numpy=True)
    
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    
    print(f"✅ Cached {len(texts)} embeddings for user {user_email}")
    
    return index, metadata
