import json, requests
from tkinter import messagebox
from functools import wraps

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
                return None
            except json.JSONDecodeError as e:
                print(f"Failed to parse API response: {e}")
                return None
            except Exception as e:
                print(f"Unexpected error: {e}")
                return None
            finally:
                APIHandler.close_session(response)
        return wrapper
    return decorator

class APIHandler:
    BASE_URL = config['BASE_URL']

    @classmethod
    def load_api_key(cls):
        cls.HEADERS = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['API_KEY']}"
        }

    @classmethod
    def fetch_models(cls):
        cls.load_api_key()
        try:
            response = requests.get(f"{cls.BASE_URL}/v1/models", headers=cls.HEADERS)
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                return [model.get('id', model.get('name', '')) for model in data if isinstance(model, dict)]
            elif isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                return [model.get('id', model.get('name', '')) for model in data['data'] if isinstance(model, dict)]
            else:
                print("Unexpected response structure")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Error fetching models: {e}")
            return []

    @classmethod
    @handle_api_errors(parse_response=True)
    def generate_text(cls, data, stream=False):
        cls.load_api_key()
        return requests.post(f"{cls.BASE_URL}/v1/completions", json=data, headers=cls.HEADERS, timeout=300, stream=stream)

    @classmethod
    @handle_api_errors(parse_response=True)
    def chat_completion_generate(cls, data, stream=False):
        cls.load_api_key()
        return requests.post(f"{cls.BASE_URL}/v1/chat/completions", json=data, headers=cls.HEADERS, timeout=300, stream=stream)

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

class ChatbotAPI:
    def __init__(self):
        if not isinstance(sys_prompt, str):
            raise ValueError("sys_prompt must be a non-empty string")
        self.sys_prompt = sys_prompt
        self.chat_history = []

        # Initialize with the system prompt only if the history is empty
        if not self.chat_history:
            self.chat_history.append({"role": "system", "content": self.sys_prompt})

        # Default starting model
        self.current_model = "Sao10K-70B-L3.3-Cirrus-x1"

    @property
    def chat_history(self):
        return self._chat_history

    @chat_history.setter
    def chat_history(self, new_history):
        self._chat_history = new_history
        # Ensure there's always a system prompt
        if not new_history or new_history[0].get("role") != "system":
            self._chat_history.insert(0, {"role": "system", "content": self.sys_prompt})

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
        """
        return ["Padrão", "Humano", "Profundo"]

    def set_creativity_mode(self, creativity_mode):
        """Updates the current model based on the provided creativity mode.
        Args:
            creativity_mode (str): The creativity mode to set. Should be one of "Padrão", "Humano", or "Profundo".
        """
        if creativity_mode == "Padrão":
            self.current_model = "Sao10K-70B-L3.3-Cirrus-x1"
            print("Setting model to Padrão: Sao10K-70B-L3.3-Cirrus-x1")
        elif creativity_mode == "Humano":
            self.current_model = "Sao10K-72B-Qwen2.5-Kunou-v1-FP8-Dynamic"
            print("Setting model to Humano: Sao10K-72B-Qwen2.5-Kunou-v1-FP8-Dynamic")
        elif creativity_mode == "Profundo":
            self.current_model = "TheDrummer-Fallen-Llama-3.3-R1-70B-v1"
            print("Setting model to Profundo: TheDrummer-Fallen-Llama-3.3-R1-70B-v1")
        else:
            raise ValueError(f"Unknown creativity mode: {creativity_mode}")

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
        messages_to_send = custom_history if custom_history is not None else self.chat_history

        # prints the messages to send for debug
        for message in messages_to_send:
            print(f"\n{message['role']}: {message['content']}")

        # Add the user message to chat history if it's not already there and not using custom history
        if message_text and store_message and custom_history is None:
            self.chat_history.append({"role": "user", "content": store_message})

        data = {
            "model": self.current_model,
            "messages": messages_to_send,
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95,
            "top_k": 40,
            "repetition_penalty": 1.05,
            "stream": False,
            "seed": -1
        }

        # Send the request to the API
        response = APIHandler.chat_completion_generate(data)
        if response is None or (isinstance(response, str) and response.strip() == ""):
            print("No response from API or empty response.")
            return None

        # If we're using custom_history, we still want to update the real chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response