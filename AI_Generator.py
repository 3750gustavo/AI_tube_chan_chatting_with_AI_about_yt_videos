import json, requests
from tkinter import messagebox
from functools import wraps
import re

# loads the LLM api key from the config file
with open("config.json", "r") as f:
    config = json.load(f)

def read_file_contents(file_path, mode='r', encoding='utf-8'):
    """Used to read the system prompt file.

    Args:
        file_path (str): Path to the file to be read.
        mode (str): Mode in which to open the file. Defaults to 'r'.
        encoding (str): File encoding. Defaults to 'utf-8'.

    Returns:
    str: The content of the file as a string, or an empty string if the file is not found.
    """
    try:
        with open(file_path, mode, encoding=encoding) as file:
            content = file.read()
            return content.strip()  # Return empty string if file is empty
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return ""
    except UnicodeDecodeError:
        print(f"Error decoding file: {file_path}. Please ensure it's saved with UTF-8 encoding.")
        return ""
    except Exception as e:
        print(f"An error occurred while reading the file: {file_path}. Error: {e}")
        return ""

sys_prompt = read_file_contents("sys_prompt.txt")
if sys_prompt == "":
    print("Error reading files. Please check the file paths and try again. Exiting...")
    messagebox.showerror(
        "CRITICAL ERROR",
        "FUCKING IDIOT: sys_prompt.txt is missing!\n"
        "1. DOWNLOAD IT FROM THE REPO\n"
        "2. PLACE IT IN THE SAME DIRECTORY AS THIS SCRIPT\n"
        "3. RESTART THE APP\n\n"
        "THIS ISN'T ROCKET SCIENCE, GRANDMA COULD DO IT"
    )
    exit(1)

def handle_api_errors(parse_response=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = None  # Initialize response to None
            try:
                response = func(*args, **kwargs)
                if response is None:
                    return None

                response.raise_for_status()

                if parse_response:
                    data = response.json()
                    if "choices" in data and data["choices"]:
                        return data["choices"][0]["message"]["content"].strip()
                    return "Error: Unexpected response structure"

                return response
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}")
                if response is not None and response.text:
                    print(f"Error response body: {response.text}")
                return None
            except json.JSONDecodeError as e:
                print(f"Failed to parse API response: {e}")
                if response is not None and response.text:
                    print(f"Error response body: {response.text}")
                return None
            except Exception as e:
                print(f"Unexpected error: {e}")
                return None
            finally:
                APIHandler.close_session(response)
        return wrapper
    return decorator

class APIHandler:
    BASE_URL = config['BASE_URL'].rstrip('/')  # Remove trailing slash if present
    USES_V1 = True  # Set to True by default, change to False if fails to fetch models at boot
    embeddings_models = []  # Dedicated list for embedding models
    non_embedding_models = []  # Main list for non-embedding models

    @classmethod
    def load_api_key(cls):
        cls.HEADERS = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['API_KEY']}"
        }

    @classmethod
    def fetch_models(cls):
        """
        Fetches available models from the API and returns a list of model IDs.
        Populates embeddings_models if any model with "embedding" or "intfloat" (non-case sensitive) in its name is found.
        """
        cls.load_api_key()
        if cls.USES_V1:  # Default path
            try:
                response = requests.get(f"{cls.BASE_URL}/v1/models", headers=cls.HEADERS)
                response.raise_for_status()
                data = response.json()

                # Check if the response is a list or a dict with 'data' key
                if isinstance(data, list):
                    models = [model.get('id', model.get('name', '')) for model in data if isinstance(model, dict)]
                elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                    models = [model.get('id', model.get('name', '')) for model in data['data'] if isinstance(model, dict)]
                else:
                    print("Unexpected response structure")
                    # first fail, switch to not using v1
                    print("Switching to not using v1")
                    cls.USES_V1 = False
                    # we recursively call this method to try fetching models again without v1
                    return cls.fetch_models()

                # clean the model list before separating them
                models = cls.clean_model_list(models)

                # Separate models into embeddings and non-embeddings
                embedding_pattern = re.compile(r'(?i)embedding|intfloat')
                cls.embeddings_models = [model for model in models if embedding_pattern.search(model)]
                cls.non_embedding_models = [model for model in models if model not in cls.embeddings_models]
                return cls.non_embedding_models

            except requests.exceptions.RequestException as e:
                print(f"Error fetching models: {e}")
                # first fail, switch to not using v1
                cls.USES_V1 = False
                print("Switching to not using v1")
                return cls.fetch_models()

        else:  # not using v1, try alt path
            try:
                response = requests.get(f"{cls.BASE_URL}/models", headers=cls.HEADERS)
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    models = [model.get('id', model.get('name', '')) for model in data if isinstance(model, dict)]
                elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                    models = [model.get('id', model.get('name', '')) for model in data['data'] if isinstance(model, dict)]
                else:
                    print("Unexpected response structure")
                    # still fails, return empty list
                    return []

                # clean the model list before separating them
                models = cls.clean_model_list(models)

                # Separate models into embeddings and non-embeddings
                embedding_pattern = re.compile(r'(?i)embedding|intfloat')
                cls.embeddings_models = [model for model in models if embedding_pattern.search(model)]
                cls.non_embedding_models = [model for model in models if model not in cls.embeddings_models]
                return cls.non_embedding_models

            except requests.exceptions.RequestException as e:
                print(f"Error fetching models: {e}")
                # still fails, return empty list
                return []

    @classmethod
    def get_embeddings_models(cls):
        """Returns the list of embedding models if available."""
        return cls.embeddings_models if cls.embeddings_models else None

    @classmethod
    @handle_api_errors(parse_response=True)
    def generate_text(cls, data, stream=False):
        cls.load_api_key()
        if cls.USES_V1:  # Default path
            print("Using v1 path for chat completions")
            return requests.post(f"{cls.BASE_URL}/v1/completions", json=data, headers=cls.HEADERS, timeout=300, stream=stream)
        else:  # not using v1, try alt path
            print("Using non-v1 path for chat completions")
            return requests.post(f"{cls.BASE_URL}/completions", json=data, headers=cls.HEADERS, timeout=300, stream=stream)

    @classmethod
    @handle_api_errors(parse_response=True)
    def chat_completion_generate(cls, data, stream=False):
        cls.load_api_key()
        if cls.USES_V1:  # Default path
            print("Using v1 path for chat completions")
            return requests.post(f"{cls.BASE_URL}/v1/chat/completions", json=data, headers=cls.HEADERS, timeout=300, stream=stream)
        else:  # not using v1, try alt path
            print("Using non-v1 path for chat completions")
            #print(f"POST Body: {json.dumps(data, indent=4)}")  # Print the post body
            # Note: This is the OAI compatible path that Gemini uses
            return requests.post(f"{cls.BASE_URL}/chat/completions", json=data, headers=cls.HEADERS, timeout=300, stream=stream)

    @staticmethod
    def close_session(response):
        if response and hasattr(response, 'close'):
            response.close()

    @classmethod
    def count_tokens(cls, model, prompt):
        cls.load_api_key()
        url = f"{cls.BASE_URL}/utils/token_counter"
        data = {
            "model": model,
            "prompt": prompt
        }
        try:
            response = requests.post(url, json=data, headers=cls.HEADERS, timeout=300)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse API response: {e}")
            return None

    @classmethod
    def clean_model_list(cls, model_list):
        """Fixes the fact some APIs incorrectly return model names with "models/" prefix
        but expect the model ID to be passed without it. (Gemini OAI compatible path)
        Args:
            model_list (list): The list of model names to clean.
        Returns:
            list: The cleaned list of model names or the original list if no cleaning is needed.
        """
        if not isinstance(model_list, list):
            print("Model list is not a list.")
            return model_list

        # Check if all models start with "models/"
        all_start_with_prefix = all(isinstance(model, str) and model.startswith("models/") for model in model_list)

        if all_start_with_prefix:
            # Remove "models/" prefix from all models
            cleaned_list = [model.replace("models/", "") for model in model_list]
            return cleaned_list
        else:
            # No cleaning needed, return original list
            return model_list

class ChatbotAPI:
    def __init__(self):
        if not isinstance(sys_prompt, str):
            raise ValueError("sys_prompt must be a non-empty string")
        self.sys_prompt = sys_prompt
        self.chat_history = []
        self.is_totalgpt = APIHandler.BASE_URL.startswith("https://api.totalgpt.ai")
        self.is_gemini = APIHandler.BASE_URL.startswith("https://generativelanguage.googleapis.com")
        self.available_models = APIHandler.fetch_models() or []
        print(f"Available models: {self.available_models}")
        self.hardcoded_models_dict = {
            "Padrão": "Sao10K-70B-L3.3-Cirrus-x1",
            "Humano": "Sao10K-72B-Qwen2.5-Kunou-v1-FP8-Dynamic",
            "Profundo": "TheDrummer-Fallen-Llama-3.3-R1-70B-v1"
        }
        # assume all models are available in TotalGPT
        self.all_models_available = True

        # Initialize with the system prompt only if the history is empty
        if not self.chat_history:
            self.chat_history.append({"role": "system", "content": self.sys_prompt})

        # If not using TotalGPT, fetch available models
        if not self.is_totalgpt:
            if self.available_models:
                self.current_model = self.available_models[0]
            else:
                print("Critical Error: No models available in the API, closing the app.")
                messagebox.showerror(
                    "CRITICAL ERROR",
                    "No models available in the API. Please check your API key and try again."
                )
                exit(1)
        # If using TotalGPT, check for hardcoded models
        else:
            # check if all 3 creativity hardcoded models are still being offered by TotalGPT
            for model_name, model_id in self.hardcoded_models_dict.items():
                if model_id not in self.available_models:
                    print(f"Warning: {model_name} model is not available in TotalGPT.")
                    self.all_models_available = False

            # If all hardcoded models are available, set the current model to the first one
            if self.all_models_available:
                self.current_model = self.hardcoded_models_dict["Padrão"]
            else:  # otherwise, do the same as non-TotalGPT APIs
                if self.available_models:
                    self.current_model = self.available_models[0]
                else:
                    print("Critical Error: No models available in the API, closing the app.")
                    messagebox.showerror(
                        "CRITICAL ERROR",
                        "No models available in the API. Please check your API key and try again."
                    )
                    exit(1)

    @property
    def chat_history(self):
        return self._chat_history

    @chat_history.setter
    def chat_history(self, new_history):
        self._chat_history = new_history
        # Ensure there's always a system prompt
        if not new_history or new_history[0].get("role") != "system":
            self._chat_history.insert(0, {"role": "system", "content": self.sys_prompt})

    def get_sys_prompt(self):
        """Returns the system prompt."""
        return self.sys_prompt

    def set_sys_prompt(self, char_sheet, user_name):
        """Replaces the sys prompt with the base sys prompt with the {character_sheet} and {user} placeholders updated.

        1. First loads the base sys prompt from the file (sys_prompt.txt).
        2. Then replaces all instances of {user} from char_sheet and the sys_prompt with the user_name string.
        3. Finally, replace {character_sheet} from sys_prompt with the fixed char_sheet string. (the one with user replaced)
        4. edit the entry 0 of the chat history with the new sys prompt (make sure it exists and its role is "system").
        Args:
            char_sheet (str): The character sheet text to be inserted in the system prompt.
            user_name (str): The name of the user to be used in both the character sheet and system prompt.
        """
        if not isinstance(char_sheet, str) or not isinstance(user_name, str):
            raise ValueError("Both char_sheet and user_name must be strings")

        # Load the base system prompt
        base_sys_prompt = read_file_contents("sys_prompt.txt")
        if not base_sys_prompt:
            raise ValueError("Base system prompt is empty or could not be read")

        # Replace placeholders in the character sheet
        char_sheet = char_sheet.replace("{user}", user_name)

        # Replace placeholders in the system prompt
        updated_sys_prompt = base_sys_prompt.replace("{character_sheet}", char_sheet).replace("{user}", user_name)

        # Update the chat history with the new system prompt
        self.chat_history[0] = {"role": "system", "content": updated_sys_prompt}
        self.sys_prompt = updated_sys_prompt

    def get_current_model(self):
        """Returns the current model being used."""
        return self.current_model

    def get_last_n_messages(self, n):
        """Returns the last n messages from the chat history."""
        if n <= 0:
            return []
        return self.chat_history[-n:]

    def get_all_non_system_messages(self):
        """Returns all messages in the chat history except for the system prompt."""
        return [msg for msg in self.chat_history if msg['role'] != 'system']

    def get_session(self):
        """Returns the current chat session for saving."""
        return self.chat_history

    def reset_chat(self):
        """Resets the chat history and re-appends the system prompt."""
        self.chat_history = []
        # no need to re-append the system prompt here, as it's handled in the setter,
        # appending here would cause it to be duplicated in the chat history

    def get_creativity_modes(self):
        """
        Returns the following 3 creativity modes:
        * Padrão: Sao10K-70B-L3.3-Cirrus-x1
        * Humano: Sao10K-72B-Qwen2.5-Kunou-v1-FP8-Dynamic
        * Profundo: TheDrummer-Fallen-Llama-3.3-R1-70B-v1
        or
        Returns all models available in the API if not using TotalGPT or any model is missing.
        """
        # Perfect case (totalgpt and all models available)
        if self.is_totalgpt and self.all_models_available:
            return ["Padrão", "Humano", "Profundo"]
        # otherwise, return all available models
        else:
            return self.available_models

    def set_creativity_mode(self, creativity_mode):
        """Updates the current model based on the provided creativity mode.
        Args:
            creativity_mode (str): The creativity mode to set. Should be one of "Padrão", "Humano", or "Profundo".
            unless not using TotalGPT or any model is missing, in which case it accepts any stringid for the model.
        Raises:
            ValueError: If the creativity mode is not recognized or if the model is not available in the API.
        """
        # first check for best case scenario (totalgpt and all models available)
        if self.is_totalgpt and self.all_models_available:
            hardcoded_model = self.hardcoded_models_dict.get(creativity_mode)
            if hardcoded_model and hardcoded_model in self.available_models:
                self.current_model = hardcoded_model
                print(f"Setting model to {creativity_mode}: {hardcoded_model}")
            else:
                raise ValueError(f"Model for mode '{creativity_mode}' not available")
        # otherwise, check if the model is available in the API
        else:
            if creativity_mode in self.available_models:
                self.current_model = creativity_mode
                print(f"Setting model to {creativity_mode}")
            else:
                raise ValueError(f"Unknown model name or model not available in the API: {creativity_mode}")

    def send_message(self, message_text, store_message=None, custom_history=None):
        """Sends a message to the LLM API and returns the response using chat completion.

        Args:
            message_text (str): The message to be sent. If None, will use custom_history.
            store_message (str): The message to store in the chat history (optional).
            custom_history (list): Optional custom chat history to use for this request.

        Returns:
            str or None: The response from the LLM API if successful, None otherwise.
        """
        # Use custom history if provided, otherwise use the instance's chat history
        messages_to_send = custom_history if custom_history is not None else self.chat_history.copy()

        # Add the user message to the messages being sent if not using custom history
        if message_text and custom_history is None:
            messages_to_send.append({"role": "user", "content": store_message or message_text})

        # prints the messages to send for debug
        for message in messages_to_send:
            print(f"\n{message['role']}: {message['content']}")

        # Prepare the base data to send to the API
        base_data = {
            "model": self.current_model,
            "messages": messages_to_send,
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95,
            "stream": False
        }

        # Add non-Gemini specific parameters if needed
        if not self.is_gemini:
            base_data.update({
                "top_k": 40,
                "repetition_penalty": 1.05,
                "seed": -1
            })

        # Send the request to the API
        response = APIHandler.chat_completion_generate(base_data)
        if response is None or (isinstance(response, str) and response.strip() == ""):
            print("No response from API or empty response.")
            return None

        # Add messages to chat history only if not using custom history
        if custom_history is None:
            # Add user message if not already added
            if message_text and store_message:
                self.chat_history.append({"role": "user", "content": store_message})
            # Add assistant response
            self.chat_history.append({"role": "assistant", "content": response})
        else:
            # When using custom history, still add the user message and response to the actual history
            if store_message:
                self.chat_history.append({"role": "user", "content": store_message})
            self.chat_history.append({"role": "assistant", "content": response})

        return response

    def update_message(self, old_text: str, new_text: str) -> bool:
        """Updates the first occurrence of a message in the chat history.

        Args:
            old_text (str): The exact content of the message to replace
            new_text (str): The new content to replace it with

        Returns:
            bool: True if a message was updated, False otherwise
        """
        for message in self.chat_history:
            if message["content"] == old_text:
                message["content"] = new_text
                return True
        return False