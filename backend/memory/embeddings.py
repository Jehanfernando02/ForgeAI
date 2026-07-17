import os
import chromadb
from chromadb.api.types import Documents, Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    A custom embedding function for ChromaDB that uses Google's gemini-embedding-2 model.
    Inheriting from chromadb.EmbeddingFunction allows ChromaDB to automatically
    generate embeddings for documents during additions and queries.
    """
    def __init__(self, model_name: str = "models/gemini-embedding-2"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=api_key
        )

    def __call__(self, input: Documents) -> Embeddings:
        """
        Embed a list of documents.
        
        Args:
            input: A list of strings to embed.
            
        Returns:
            A list of vector embeddings (lists of floats).
        """
        return self.embeddings.embed_documents(list(input))


def get_embeddings_client(model_name: str = "models/gemini-embedding-2") -> GoogleGenerativeAIEmbeddings:
    """Initialize and return the GoogleGenerativeAIEmbeddings client."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    return GoogleGenerativeAIEmbeddings(
        model=model_name,
        google_api_key=api_key
    )


def embed_text(text: str, model_name: str = "models/gemini-embedding-2") -> list[float]:
    """Generate embedding vector for a single document text."""
    client = get_embeddings_client(model_name)
    return client.embed_documents([text])[0]


def embed_query(query: str, model_name: str = "models/gemini-embedding-2") -> list[float]:
    """Generate embedding vector for a search query."""
    client = get_embeddings_client(model_name)
    return client.embed_query(query)
