import requests
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json

class RAGManager:
    """
    RAG (Retrieval-Augmented Generation) Manager for semantic similarity and context retrieval.
    """
    def __init__(self, model="intfloat-multilingual-e5-base"):
        """
        Initialize the RAG Manager.

        Args:
            model (str): The model name to use for generating embeddings (default: "intfloat-multilingual-e5-base").
        """
        with open("config.json", "r") as f:
            config = json.load(f)
        self.api_key = config["API_KEY"]
        self.model = model
        self.base_url = "https://api.totalgpt.ai/v1/embeddings"

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
        response = requests.post(self.base_url, headers=headers, json=data)
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

    def get_relevant_context(self, user_input, context_strings, threshold=0.75):
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

        # Filter and sort chunks based on similarity scores
        relevant_chunks = [
            {"chunk": chunk, "score": score}
            for chunk, score in zip(context_chunks, similarity_scores)
            if score >= threshold
        ]
        relevant_chunks.sort(key=lambda x: x["score"], reverse=True)

        # Join relevant chunks into a single string
        relevant_context = " ".join(chunk["chunk"] for chunk in relevant_chunks)

        return relevant_context

if __name__ == "__main__":
    # Example usage
    rag_manager = RAGManager()

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