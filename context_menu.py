# context_menu.py

import tkinter as tk
import customtkinter as ctk

class ContextMenu:
    def __init__(self, master, bubble, app):
        self.master = master
        self.bubble = bubble
        self.app = app
        self.menu = tk.Menu(self.master, tearoff=0)

        self.menu.add_command(label="Copy", command=self.copy_text)
        self.menu.add_command(label="Edit", command=self.edit_text)

    def copy_text(self):
        text = self.bubble.cget("text")
        self.master.clipboard_clear()
        self.master.clipboard_append(text)

    def edit_text(self):
        # Get the current text
        text = self.bubble.cget("text")

        # Calculate the height of the textbox based on the number of lines
        lines = text.count("\n") + 1
        height = lines * 35 # Assuming 35 pixels per line

        # Replace the label with a textbox
        self.bubble.destroy()
        self.edit_entry = ctk.CTkTextbox(
            self.bubble.master,
            width=512,
            height=lines * 35,
            font=ctk.CTkFont(size=14),
            wrap='word'
        )
        self.edit_entry.insert("1.0", text)
        self.edit_entry.pack(padx=15, pady=10)

        def save_changes():
            new_text = self.edit_entry.get("1.0", "end-1c")
            self.edit_entry.destroy()
            if hasattr(self, 'save_button'):
                self.save_button.destroy()
            
            self.bubble = ctk.CTkLabel(
                self.bubble.master,
                text=new_text,
                wraplength=512,
                justify="left",
                font=ctk.CTkFont(size=14)
            )
            self.bubble.pack(padx=15, pady=10)

            # Update the chat history
            self.app.chatbot_api.update_message(text, new_text)

            # Auto-save the session
            self.app.auto_save_session()

            # Create a new context menu
            context_menu = ContextMenu(self.master, self.bubble, self.app)
            self.bubble.bind("<3>", lambda e: context_menu.show(e.x_root, e.y_root))

        # Create a button to save the changes
        self.save_button = ctk.CTkButton(self.bubble.master, text="Save", command=save_changes)
        self.save_button.pack()

    def show(self, x, y):
        self.menu.post(x, y)