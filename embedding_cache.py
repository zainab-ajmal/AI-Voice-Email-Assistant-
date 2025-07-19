import os
import pickle
import numpy as np
import faiss
from fastapi import APIRouter, Body
from sentence_transformers import SentenceTransformer

from db import tokens_collection
from gmail_metadata import get_user_metadata

router = APIRouter()
model = SentenceTransformer("all-mpnet-base-v2")


CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def build_user_embedding_cache(user_email: str):
    """Build FAISS index and metadata for user's email threads."""
    data = get_user_metadata(user_email)
    threads = data.get("recent_threads", [])

    texts = []
    metadata = []

    for thread in threads:
        combined = f"{thread.get('subject', '')} {thread.get('snippet', '')} from {thread.get('from', '')} dated {thread.get('date', '')}"
        texts.append(combined)
        metadata.append({
            "subject": thread.get("subject", ""),
            "from": thread.get("from", ""),
            "date": thread.get("date", "")
        })

    embeddings = model.encode(texts, convert_to_numpy=True)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    # Save index and metadata
    index_path = os.path.join(CACHE_DIR, f"{user_email.replace('@', '_')}_index.faiss")
    meta_path = os.path.join(CACHE_DIR, f"{user_email.replace('@', '_')}_metadata.pkl")

    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)

    print(f"✅ Cached {len(texts)} embeddings for user {user_email}")
    return index, metadata


def load_index_and_metadata(user_email: str):
    """Load saved FAISS index and metadata from disk."""
    index_path = os.path.join(CACHE_DIR, f"{user_email.replace('@', '_')}_index.faiss")
    meta_path = os.path.join(CACHE_DIR, f"{user_email.replace('@', '_')}_metadata.pkl")

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        raise FileNotFoundError("Embedding cache not found. Please build cache first.")

    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        metadata = pickle.load(f)

    return index, metadata


def retrieve_similar_emails(user_email: str, query: str, top_k: int = 3):
    """Search embedding cache using semantic similarity."""
    index, metadata = load_index_and_metadata(user_email)
    query_vector = model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_vector, top_k)

    results = []
    for i in indices[0]:
        if i < len(metadata):
            results.append(metadata[i])

    return results



