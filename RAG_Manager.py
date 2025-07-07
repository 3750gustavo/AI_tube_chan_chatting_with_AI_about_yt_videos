import requests
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json

class RAGManager:
    """
    RAG (Retrieval-Augmented Generation) Manager for semantic similarity and context retrieval.
    """
    def __init__(self, model="intfloat-multilingual-e5-base", debug=False):
        """
        Initialize the RAG Manager.

        Args:
            model (str): The model name to use for generating embeddings (default: "intfloat-multilingual-e5-base").
        """
        with open("config.json", "r") as f:
            config = json.load(f)
        self.api_key = config["API_KEY"]
        self.model = model
        self.base_url = config["BASE_URL"].rstrip('/')
        self.USES_V1 = self.base_url.startswith("https://api.totalgpt.ai")  # Auto-detect TotalGPT
        self.embeddings_endpoint = f"{self.base_url}/v1/embeddings" if self.USES_V1 else f"{self.base_url}/embeddings"
        self.debug = debug

    def _get_embeddings(self, texts):
        """
        Get embeddings for a list of texts using the specified API and model.

        Args:
            texts (list): List of text strings to generate embeddings for.

        Returns:
            list: List of embeddings corresponding to the input texts.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "input": texts,
            "model": self.model
        }
        response = requests.post(self.embeddings_endpoint, headers=headers, json=data)
        if response.status_code == 200:
            return [item["embedding"] for item in response.json()["data"]]
        else:
            raise Exception(f"Error getting embeddings: {response.text}")

    def _break_into_chunks(self, texts, max_tokens=512):
        """
        Break texts into smaller chunks to avoid exceeding the token limit.

        Args:
            texts (list): List of text strings to break into chunks.
            max_tokens (int): Maximum number of tokens allowed per chunk (default: 512).

        Returns:
            list: List of text chunks.
        """
        chunks = []
        for text in texts:
            words = text.split()
            current_chunk = []
            current_token_count = 0
            for word in words:
                current_chunk.append(word)
                current_token_count += 1
                if current_token_count >= max_tokens:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_token_count = 0
            if current_chunk:
                chunks.append(" ".join(current_chunk))
        return chunks

    def normalize_score(self, raw_score):
        """Normalize scores to [0.7-1.0] range for consistency with API"""
        normalized = (raw_score - 0.7) / 0.3
        return max(0, min(normalized, 1.0))  # Clamp values

    def get_relevant_context(self, user_input, context_strings, threshold=0.333):  # Default now 33.3% of normalized range
        """
        Retrieve relevant context based on semantic similarity with the user input.

        Args:
            user_input (str): The user's input query.
            context_strings (list): List of context strings to compare against.
            threshold (float): Minimum similarity score to consider a match (default: 0.75).

        Returns:
            list: List of relevant context strings sorted by similarity score.
        """
        # Break context strings into smaller chunks
        context_chunks = self._break_into_chunks(context_strings)

        # Get embeddings for user input and context chunks
        user_embedding = self._get_embeddings([user_input])[0]
        context_embeddings = self._get_embeddings(context_chunks)

        # Calculate cosine similarity scores
        similarity_scores = cosine_similarity([user_embedding], context_embeddings)[0]

        # Normalize scores to API range
        normalized_scores = [self.normalize_score(score) for score in similarity_scores]

        # Filter and sort chunks based on normalized scores
        relevant_chunks = [
            {"chunk": chunk, "score": norm_score}
            for chunk, raw_score, norm_score in zip(context_chunks, similarity_scores, normalized_scores)
            if norm_score >= threshold  # Use normalized threshold (0.333 = 0.75 raw)
        ]
        relevant_chunks.sort(key=lambda x: x["score"], reverse=True)

        # Join relevant chunks into a single string
        relevant_context = "Relevant Context:\n"
        if not relevant_chunks:
            relevant_context += "No relevant context found."
        else:
            relevant_context += " ".join(chunk["chunk"] for chunk in relevant_chunks)

        # Debugging output
        if self.debug:
            print("Debugging Information:")
            print(f"Model: {self.model}")
            print(f"User Input: {user_input}")
            print(f"Context Chunks and their respective Scores (pre-normalized):")
            for chunk, raw_score, norm_score in zip(context_chunks, similarity_scores, normalized_scores):
                print(f"  Chunk: {chunk[:50]}... | Raw Score: {raw_score:.4f} | Normalized Score: {norm_score:.4f}")
            print(f"Threshold for relevance: {threshold}")
            print(f"Relevant Chunks (after filtering and sorting):")
            for chunk in relevant_chunks:
                print(f"  Chunk: {chunk['chunk'][:50]}... | Score: {chunk['score']:.4f}")

        # Return the relevant context as a single string
        return relevant_context.strip()

if __name__ == "__main__":
    # Example usage
    rag_manager = RAGManager(debug=True)  # Set debug=True for testing

    user_input = "What is the capital of France?"
    context_strings = [ # Will return all sentences, except the last one
        "Paris is the capital of France.",
        "France is a country in Europe.",
        "The Eiffel Tower is located in Paris.",
        "Berlin is the capital of Germany.",
        "I love pudim!!"
    ]

    relevant_context = rag_manager.get_relevant_context(user_input, context_strings)
    print("Relevant Context:")
    print(relevant_context)