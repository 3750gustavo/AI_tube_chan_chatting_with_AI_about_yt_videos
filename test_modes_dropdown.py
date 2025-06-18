import json
import pytest
from AI_Generator import ChatbotAPI, APIHandler

def test_chatbot_api_init():
    # Initialize the chatbot API
    chatbot_api = ChatbotAPI()

    # Check if the available models are loaded correctly
    available_models = chatbot_api.get_creativity_modes()
    assert len(available_models) > 0

def test_set_creativity_mode():
    # Initialize the chatbot API
    chatbot_api = ChatbotAPI()

    # Test setting a valid creativity mode
    chatbot_api.set_creativity_mode("Padrão")
    assert chatbot_api.get_current_model() == "Sao10K-70B-L3.3-Cirrus-x1"

    # Test setting an invalid creativity mode
    with pytest.raises(ValueError):
        chatbot_api.set_creativity_mode("Invalid Mode")

def test_set_creativity_mode_with_missing_hardcoded_model():
    # Initialize the chatbot API
    chatbot_api = ChatbotAPI()

    # Override the hardcoded models to include a missing model
    chatbot_api.hardcoded_models_dict = {
        "Padrão": "Sao10K-70B-L3.3-Cirrus-x1",
        "Humano": "Qwen2.5-72B-Instruct-Turbo",  # This model is no longer available
        "Profundo": "TheDrummer-Fallen-Llama-3.3-R1-70B-v1"
    }

    # Override the available models to exclude the missing model
    chatbot_api.available_models = ["Sao10K-70B-L3.3-Cirrus-x1", "TheDrummer-Fallen-Llama-3.3-R1-70B-v1"]

    # Test setting a creativity mode that corresponds to a missing hardcoded model
    with pytest.raises(ValueError):
        chatbot_api.set_creativity_mode("Humano")

def test_on_creativity_change():
    # Initialize the chatbot API
    chatbot_api = ChatbotAPI()

    # Override the hardcoded models to include a missing model
    chatbot_api.hardcoded_models_dict = {
        "Padrão": "Sao10K-70B-L3.3-Cirrus-x1",
        "Humano": "Qwen2.5-72B-Instruct-Turbo",  # This model is no longer available
        "Profundo": "TheDrummer-Fallen-Llama-3.3-R1-70B-v1"
    }

    # Override the available models to exclude the missing model
    chatbot_api.available_models = ["Sao10K-70B-L3.3-Cirrus-x1", "TheDrummer-Fallen-Llama-3.3-R1-70B-v1"]

    # Override the self.all_models_available to simulate the missing model
    chatbot_api.all_models_available = False

    # Simulate the on_creativity_change method
    try:
        chatbot_api.set_creativity_mode("Humano")
    except ValueError:
        # Get the list of available modes
        available_models = chatbot_api.get_creativity_modes()

        # Try to set the next available mode
        for available_mode in available_models:
            try:
                chatbot_api.set_creativity_mode(available_mode)
                break
            except ValueError:
                continue
        else:
            # If none of the available modes work, just print an error and exit
            print("Error: No valid creativity modes available.")
            pytest.fail("Error: No valid creativity modes available.")

    # Check that the API has fallen back to an available model
    available_models = chatbot_api.get_creativity_modes()
    assert chatbot_api.get_current_model() in available_models

# Run using: pytest .\test_modes_dropdown.py -v