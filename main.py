import customtkinter as ctk
import os
import json
import threading
import queue
from tkinter import filedialog, messagebox
from AI_Generator import ChatbotAPI, APIHandler
from user_input_validator import UserInputValidator
from memory_manager import MemoryManager
from youtube_transcript_module import YouTubeTranscriptDownloader
import atexit

class AITubeChanApp:
    def __init__(self):
        # Initialize the main window
        self.root = ctk.CTk()
        self.root.title("AI Tube Chan")
        self.root.geometry("1000x700")

        # Initialize components
        self.chatbot_api = ChatbotAPI()
        self.youtube_downloader = YouTubeTranscriptDownloader()
        self.user_input_validator = UserInputValidator(self.youtube_downloader)
        self.api_handler = APIHandler()
        self.memory_manager = MemoryManager(self.api_handler, user_input_validator=self.user_input_validator)

        # Threading setup
        self.response_queue = queue.Queue()
        self.is_processing = False

        # App state
        self.current_character = None
        self.user_name = "User"
        self.auto_save_file = "autosave_session.json"

        # Register auto-save on exit
        atexit.register(self.auto_save_session)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.setup_ui()
        self.load_characters()
        self.load_auto_save_session()

        # Start checking for AI responses
        self.check_ai_response()

    def setup_ui(self):
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Top frame for controls
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill="x", padx=10, pady=(10, 5))

        # Character selection
        ctk.CTkLabel(top_frame, text="Character:").pack(side="left", padx=(10, 5))
        self.character_dropdown = ctk.CTkComboBox(
            top_frame,
            command=self.on_character_change,
            width=200
        )
        self.character_dropdown.pack(side="left", padx=5)

        # User name input
        ctk.CTkLabel(top_frame, text="Your Name:").pack(side="left", padx=(20, 5))
        self.user_name_entry = ctk.CTkEntry(top_frame, width=100)
        self.user_name_entry.pack(side="left", padx=5)
        self.user_name_entry.insert(0, self.user_name)
        self.user_name_entry.bind("<KeyRelease>", self.on_user_name_change)

        # Creativity mode
        ctk.CTkLabel(top_frame, text="Mode:").pack(side="left", padx=(20, 5))
        self.creativity_dropdown = ctk.CTkComboBox(
            top_frame,
            values=self.chatbot_api.get_creativity_modes(),
            command=self.on_creativity_change,
            width=100
        )
        self.creativity_dropdown.pack(side="left", padx=5)
        self.creativity_dropdown.set("Padrão")

        # Buttons frame
        buttons_frame = ctk.CTkFrame(top_frame)
        buttons_frame.pack(side="right", padx=10)

        ctk.CTkButton(
            buttons_frame,
            text="Save Chat",
            command=self.save_chat,
            width=80
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            buttons_frame,
            text="Load Chat",
            command=self.load_chat,
            width=80
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            buttons_frame,
            text="Clear Chat",
            command=self.clear_chat,
            width=80
        ).pack(side="left", padx=2)

        # Chat display area with scrollable frame
        chat_frame = ctk.CTkFrame(main_frame)
        chat_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.chat_scroll = ctk.CTkScrollableFrame(chat_frame)
        self.chat_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Input frame
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", padx=10, pady=(5, 10))

        # Message input
        self.message_entry = ctk.CTkTextbox(input_frame, height=60)
        self.message_entry.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)

        # Send button
        self.send_button = ctk.CTkButton(
            input_frame,
            text="Send",
            command=self.send_message,
            width=80,
            height=60
        )
        self.send_button.pack(side="right", padx=(5, 10), pady=10)

        # Bind Enter key
        self.message_entry.bind("<Control-Return>", lambda e: self.send_message())

    def add_message_bubble(self, message, is_user=True):
        """Add a message bubble to the chat display"""
        # Create bubble frame
        bubble_frame = ctk.CTkFrame(self.chat_scroll)

        if is_user:
            # User message - right aligned, blue
            bubble_frame.pack(fill="x", padx=(50, 10), pady=(5, 10), anchor="e")
            bubble_frame.configure(fg_color=("#3B82F6", "#1E40AF"))  # Blue colors for light/dark mode
        else:
            # AI message - left aligned, gray
            bubble_frame.pack(fill="x", padx=(10, 50), pady=(5, 10), anchor="w")
            bubble_frame.configure(fg_color=("#E5E7EB", "#374151"))  # Gray colors for light/dark mode

        # Message text
        message_label = ctk.CTkLabel(
            bubble_frame,
            text=message,
            wraplength=400,
            justify="left",
            font=ctk.CTkFont(size=14)
        )
        message_label.pack(padx=15, pady=10)

        # Auto-scroll to bottom
        self.root.after(100, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    def load_characters(self):
        """Load character files from the characters folder"""
        characters_folder = "characters"
        character_files = []

        if os.path.exists(characters_folder):
            for file in os.listdir(characters_folder):
                if file.endswith('.txt'):
                    character_files.append(file[:-4])  # Remove .txt extension

        if character_files:
            self.character_dropdown.configure(values=character_files)
            self.character_dropdown.set(character_files[0])
            self.load_character(character_files[0])
        else:
            messagebox.showwarning("No Characters", "No character files found in 'characters' folder!")

    def load_character(self, character_name):
        """Load character sheet from file"""
        try:
            with open(f"characters/{character_name}.txt", 'r', encoding='utf-8') as f:
                character_sheet = f.read().strip()

            # Validate character sheet is not empty
            if not character_sheet:
                messagebox.showerror("Error", f"Character file '{character_name}.txt' is empty!")
                return

            # Get current user name
            self.user_name = self.user_name_entry.get().strip() or "User"

            # Reset chat with new character
            self.chatbot_api.reset_chat()

            # Use the new set_sys_prompt method to handle all replacements
            self.chatbot_api.set_sys_prompt(character_sheet, self.user_name)

            self.current_character = character_name
            self.update_chat_display()

            print(f"Loaded character: {character_name}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load character: {e}")

    def on_character_change(self, character_name):
        """Handle character selection change"""
        self.load_character(character_name)

    def on_user_name_change(self, event):
        """Handle user name change"""
        new_name = self.user_name_entry.get().strip()
        if new_name and new_name != self.user_name:
            self.user_name = new_name
            # Reload current character to update {user} placeholders
            if self.current_character:
                self.load_character(self.current_character)

    def on_creativity_change(self, mode):
        """Handle creativity mode change"""
        self.chatbot_api.set_creativity_mode(mode)

    def send_message(self):
        """Send message to AI using threading"""
        message = self.message_entry.get("1.0", "end-1c").strip()
        if not message or self.is_processing:
            return

        # Add user message bubble immediately
        self.add_message_bubble(message, is_user=True)

        # Clear input
        self.message_entry.delete("1.0", "end")

        # Update UI state
        self.is_processing = True
        self.send_button.configure(state="disabled", text="Sending...")
        self.message_entry.configure(state="disabled")

        # Start AI processing in a separate thread
        thread = threading.Thread(target=self.process_ai_message, args=(message,), daemon=True)
        thread.start()

    def process_ai_message(self, message):
        """Process AI message in a separate thread"""
        try:
            # Process message (handle YouTube links)
            message_to_store, message_to_send, youtube_metadata = self.user_input_validator.process_message_with_link(message)

            if youtube_metadata:
                # Register with memory manager
                message_index = len(self.chatbot_api.chat_history)
                self.memory_manager.register_youtube_message(
                    message_index,
                    youtube_metadata["link_version"],
                    youtube_metadata["transcript_version"],
                    youtube_metadata["video_title"]
                )

            # Prepare messages for API
            optimized_history = self.memory_manager.prepare_messages_for_api(self.chatbot_api.chat_history)

            # Add current message to optimized history
            optimized_history.append({"role": "user", "content": message_to_send or message_to_store})

            # Send to API
            response = self.chatbot_api.send_message(
                message_to_send or message,
                store_message=message_to_store,
                custom_history=optimized_history
            )

            # Put result in queue for main thread to process
            if response:
                self.response_queue.put(("success", response))
            else:
                self.response_queue.put(("error", "Failed to get response from AI"))

        except Exception as e:
            self.response_queue.put(("error", f"Error sending message: {e}"))

    def check_ai_response(self):
        """Check for AI responses and update UI (runs in main thread)"""
        try:
            while True:
                response_type, response_data = self.response_queue.get_nowait()

                if response_type == "success":
                    # Add AI response bubble
                    self.add_message_bubble(response_data, is_user=False)
                    # Auto-save session after successful message
                    self.auto_save_session()
                elif response_type == "error":
                    messagebox.showerror("Error", response_data)

                # Reset UI state
                self.is_processing = False
                self.send_button.configure(state="normal", text="Send")
                self.message_entry.configure(state="normal")

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.check_ai_response)

    def update_chat_display(self):
        """Update the chat display with current conversation"""
        # Clear existing messages
        for widget in self.chat_scroll.winfo_children():
            widget.destroy()

        # Display non-system messages with message bubbles
        for message in self.chatbot_api.get_all_non_system_messages():
            role = message["role"]
            content = message["content"]

            if role == "user":
                self.add_message_bubble(content, is_user=True)
            elif role == "assistant":
                self.add_message_bubble(content, is_user=False)

    def auto_save_session(self):
        """Auto-save current session"""
        if not self.chatbot_api.get_all_non_system_messages():
            return  # Nothing to save

        try:
            save_data = {
                "character": self.current_character,
                "user_name": self.user_name,
                "creativity_mode": self.creativity_dropdown.get(),
                "chat_history": self.chatbot_api.chat_history,
                "youtube_messages": self.memory_manager.get_youtube_messages(),
                "version": "1.0"  # For future compatibility
            }

            with open(self.auto_save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            print(f"Session auto-saved to {self.auto_save_file}")

        except Exception as e:
            print(f"Failed to auto-save session: {e}")

    def load_auto_save_session(self):
        """Load auto-saved session if it exists"""
        if not os.path.exists(self.auto_save_file):
            return

        try:
            with open(self.auto_save_file, 'r', encoding='utf-8') as f:
                save_data = json.load(f)

            # Only load if there's actual chat content
            if not save_data.get("chat_history") or len(save_data["chat_history"]) <= 1:
                return

            self.load_session_data(save_data)
            print(f"Auto-saved session loaded from {self.auto_save_file}")

        except Exception as e:
            print(f"Failed to load auto-saved session: {e}")

    def load_session_data(self, save_data):
        """Load session data from save file"""
        # Restore app state
        self.current_character = save_data.get("character")
        self.user_name = save_data.get("user_name", "User")
        creativity_mode = save_data.get("creativity_mode", "Padrão")

        # Update UI
        self.user_name_entry.delete(0, "end")
        self.user_name_entry.insert(0, self.user_name)
        self.creativity_dropdown.set(creativity_mode)

        if self.current_character:
            self.character_dropdown.set(self.current_character)

        # Set creativity mode
        self.chatbot_api.set_creativity_mode(creativity_mode)

        # Restore memory manager state
        youtube_messages = save_data.get("youtube_messages", {})
        self.memory_manager.youtube_messages = {int(k): v for k, v in youtube_messages.items()}

        # Restore chat history
        self.chatbot_api.chat_history = save_data["chat_history"]

        # Reload character to ensure proper user name replacement in system prompt
        if self.current_character:
            # Store non-system messages temporarily
            non_system_messages = self.chatbot_api.get_all_non_system_messages()
            # Reload character (resets chat and updates system prompt)
            self.load_character(self.current_character)
            # Restore non-system messages
            self.chatbot_api.chat_history.extend(non_system_messages)

        self.update_chat_display()

    def save_chat(self):
        """Save current chat session"""
        if not self.chatbot_api.get_all_non_system_messages():
            messagebox.showwarning("Nothing to Save", "No conversation to save!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                save_data = {
                    "character": self.current_character,
                    "user_name": self.user_name,
                    "creativity_mode": self.creativity_dropdown.get(),
                    "chat_history": self.chatbot_api.chat_history,
                    "youtube_messages": self.memory_manager.get_youtube_messages(),
                    "version": "1.0"
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)

                messagebox.showinfo("Success", "Chat saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save chat: {e}")

    def load_chat(self):
        """Load a saved chat session"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)

                self.load_session_data(save_data)
                messagebox.showinfo("Success", "Chat loaded successfully!")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load chat: {e}")

    def clear_chat(self):
        """Clear the current chat"""
        if self.is_processing:
            messagebox.showwarning("Processing", "Please wait for the current message to finish processing.")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to clear the chat?"):
            self.chatbot_api.reset_chat()
            self.memory_manager.clear_youtube_messages()

            # Reload character to restore system prompt
            if self.current_character:
                self.load_character(self.current_character)

            self.update_chat_display()

            # Clear auto-save file
            if os.path.exists(self.auto_save_file):
                os.remove(self.auto_save_file)

    def on_closing(self):
        """Handle application closing"""
        self.auto_save_session()
        self.root.destroy()

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AITubeChanApp()
    app.run()