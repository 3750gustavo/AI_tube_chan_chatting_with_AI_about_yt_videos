import customtkinter as ctk
import os
import json
from tkinter import filedialog, messagebox
from AI_Generator import ChatbotAPI, APIHandler
from user_input_validator import UserInputValidator
from memory_manager import MemoryManager
from youtube_transcript_module import YouTubeTranscriptDownloader

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

        # App state
        self.current_character = None
        self.user_name = "User"

        self.setup_ui()
        self.load_characters()

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

        # Chat display area
        self.chat_display = ctk.CTkTextbox(
            main_frame,
            wrap="word",
            state="disabled"
        )
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=5)

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

            # Replace {user} placeholder with actual user name
            character_sheet = character_sheet.replace("{user}", self.user_name)

            # Update system prompt
            sys_prompt = self.chatbot_api.sys_prompt.replace("{character_sheet}", character_sheet)

            # Reset chat with new character
            self.chatbot_api.reset_chat()
            self.chatbot_api.chat_history[0]["content"] = sys_prompt

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
        """Send message to AI"""
        message = self.message_entry.get("1.0", "end-1c").strip()
        if not message:
            return

        # Clear input
        self.message_entry.delete("1.0", "end")

        # Disable send button
        self.send_button.configure(state="disabled", text="Sending...")
        self.root.update()

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

            if response:
                self.update_chat_display()
            else:
                messagebox.showerror("Error", "Failed to get response from AI")

        except Exception as e:
            messagebox.showerror("Error", f"Error sending message: {e}")
        finally:
            # Re-enable send button
            self.send_button.configure(state="normal", text="Send")

    def update_chat_display(self):
        """Update the chat display with current conversation"""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")

        # Display non-system messages
        for message in self.chatbot_api.get_all_non_system_messages():
            role = "You" if message["role"] == "user" else self.current_character or "AI"
            content = message["content"]

            # Format message
            self.chat_display.insert("end", f"{role}: {content}\n\n")

        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

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
                    "chat_history": self.chatbot_api.chat_history,
                    "youtube_messages": self.memory_manager.get_youtube_messages()
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

                # Restore chat state
                self.chatbot_api.chat_history = save_data["chat_history"]
                self.current_character = save_data.get("character")
                self.user_name = save_data.get("user_name", "User")

                # Update UI
                self.user_name_entry.delete(0, "end")
                self.user_name_entry.insert(0, self.user_name)

                if self.current_character:
                    self.character_dropdown.set(self.current_character)

                # Restore memory manager state
                youtube_messages = save_data.get("youtube_messages", {})
                self.memory_manager.youtube_messages = {int(k): v for k, v in youtube_messages.items()}

                self.update_chat_display()
                messagebox.showinfo("Success", "Chat loaded successfully!")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load chat: {e}")

    def clear_chat(self):
        """Clear the current chat"""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the chat?"):
            self.chatbot_api.reset_chat()
            self.memory_manager.clear_youtube_messages()

            # Reload character to restore system prompt
            if self.current_character:
                self.load_character(self.current_character)

            self.update_chat_display()

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AITubeChanApp()
    app.run()