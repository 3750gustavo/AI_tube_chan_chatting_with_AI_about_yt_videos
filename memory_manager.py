import json
import re

class MemoryManager:
    """
    Manages chat message memory to optimize context window usage.
    Dynamically compresses/expands YouTube transcript messages based on available tokens.
    """
    def __init__(self, api_handler, max_tokens=30000, user_input_validator=None):
        """
        Initialize the memory manager.

        Args:
            api_handler: The API handler class used to count tokens
            max_tokens: Maximum tokens to target (default 30k to leave some headroom)
            user_input_validator: Optional UserInputValidator instance to process YouTube links
        """
        self.api_handler = api_handler
        self.max_tokens = max_tokens
        self.model = "Sao10K-70B-L3.3-Cirrus-x1"  # Default model
        self.youtube_messages = {}  # message_index -> {"link": link, "transcript": transcript}
        self.user_input_validator = user_input_validator
        print(f"[MemoryManager] Initialized with max_tokens={max_tokens}")

    def process_youtube_message(self, message_index, user_input):
        """
        Detects and processes YouTube links in user input.
        Uses UserInputValidator to properly retrieve and process transcripts.

        Args:
            message_index: Index of the message in the chat history
            user_input: The user input message to process

        Returns:
            tuple: (message_to_store, message_to_send, youtube_metadata)
        """
        if not self.user_input_validator:
            # No validator available, just return original input
            return user_input, None

        # Use the validator to process the message with potential YouTube links
        message_to_store, message_to_send, youtube_metadata = self.user_input_validator.process_message_with_link(user_input)

        if not youtube_metadata:
            # No YouTube content found
            return user_input, None

        # Extract information from metadata
        video_title = youtube_metadata.get('video_title', 'Unknown Video')
        link_version = youtube_metadata.get('link_version')
        transcript_version = youtube_metadata.get('transcript_version')

        # Register the YouTube message for memory management
        self.register_youtube_message(
            message_index,
            link_version,
            transcript_version,
            video_title
        )

        print(f"[MemoryManager] Registered YouTube content: '{video_title}'")
        return link_version, video_title

    def register_youtube_message(self, message_index, link_version, transcript_version, video_title=None):
        """
        Register a message containing a YouTube transcript.

        Args:
            message_index: Index of the message in the chat history
            link_version: Message with just "Source: link"
            transcript_version: Message with full transcript
            video_title: Title of the YouTube video
        """
        self.youtube_messages[message_index] = {
            "link_version": link_version,
            "transcript_version": transcript_version,
            "video_title": video_title
        }

        # Calculate approximate token difference between versions
        link_tokens = len(link_version) // 4  # Rough estimate
        transcript_tokens = len(transcript_version) // 4  # Rough estimate
        token_diff = transcript_tokens - link_tokens

        print(f"[MemoryManager] Registered YouTube message at index {message_index}")
        print(f"[MemoryManager] Video: '{video_title}' at index {message_index}")
        print(f"[MemoryManager] Link version: ~{link_tokens} tokens")
        print(f"[MemoryManager] Transcript version: ~{transcript_tokens} tokens")
        print(f"[MemoryManager] Token difference: ~{token_diff} tokens")

    def count_tokens(self, messages):
        """Count tokens for a list of messages."""
        # Prepare chat history for token counting
        chat_history_text = "\n\n".join(message['content'] for message in messages)

        # Count tokens using the API Handler
        token_data = self.api_handler.count_tokens(self.model, chat_history_text)

        if token_data and 'total_tokens' in token_data:
            token_count = token_data['total_tokens']
            print(f"[MemoryManager] Token count from API: {token_count} tokens")
        else:
            # Fallback: estimate tokens using a simple rule (about 4 chars per token)
            token_count = len(chat_history_text) // 4
            print(f"[MemoryManager] WARNING: API token count failed, using fallback method")
            print(f"[MemoryManager] Fallback token count: {token_count} tokens")

        print(f"[MemoryManager] Current token count: {token_count}/{self.max_tokens} tokens ({(token_count/self.max_tokens)*100:.1f}%)")
        return token_count

    def optimize_context(self, chat_history):
        """
        Optimize the context window by compressing YouTube messages if needed.
        Returns an optimized copy of the chat history.

        Returns:
            list: The optimized chat history.
        """
        print(f"\n[MemoryManager] Starting context optimization...")
        print(f"[MemoryManager] YouTube messages tracked: {len(self.youtube_messages)}")

        # Make a deep copy of chat history to avoid modifying the original
        optimized_history = json.loads(json.dumps(chat_history))

        # Calculate current token count
        current_tokens = self.count_tokens(optimized_history)
        original_tokens = current_tokens

        # If we're already under the limit, return the chat history as is
        if current_tokens <= self.max_tokens:
            print(f"[MemoryManager] Context already optimized: {current_tokens}/{self.max_tokens} tokens")
            return optimized_history

        print(f"[MemoryManager] Context needs optimization: {current_tokens}/{self.max_tokens} tokens")

        # Sort YouTube messages from oldest to newest
        message_indices = sorted(self.youtube_messages.keys())
        number_of_youtube_messages = len(message_indices)
        # Check optimized history for how many youtube messages are present uncompressed
        uncompressed_youtube_messages_count = sum(1 for idx in message_indices if idx < len(optimized_history) and "transcript_version" in self.youtube_messages[idx])
        print(f"[MemoryManager] Uncompressed YouTube messages count: {uncompressed_youtube_messages_count}")

        # Prioritize single-link compression in small chats
        if len(optimized_history) <= 4 and len(self.youtube_messages) == 1:
            print("[MemoryManager] Small chat detected (4 messages) with 1 YouTube link - prioritizing compression")
            message_index = next(iter(self.youtube_messages.keys()))
            if message_index < len(optimized_history):
                link_version = self.youtube_messages[message_index]["link_version"]
                optimized_history[message_index]["content"] = link_version
                current_tokens = self.count_tokens(optimized_history)
                if current_tokens <= self.max_tokens:
                    print(f"[MemoryManager] Single link compressed successfully ({original_tokens} → {current_tokens} tokens)")
                    return optimized_history

        # if its just one message or less and chat_history has at least 8 messages, we go straight to removing the two oldest messages until we are under the limit or under 8 messages
        if number_of_youtube_messages <= 1 and len(optimized_history) >= 8:
            print(f"[MemoryManager] One or less Youtube messages detected, prioritizing removal of oldest messages")
            while True:
                optimized_history = self.remove_oldest_message_pair(optimized_history)
                current_tokens = self.count_tokens(optimized_history)
                print(f"[MemoryManager] Current token count after removal: {current_tokens}/{self.max_tokens} tokens")
                if current_tokens <= self.max_tokens:
                    print(f"[MemoryManager] Context optimized successfully after removing messages")
                    print(f"[MemoryManager] Tokens reduced: {original_tokens} → {current_tokens} (saved {original_tokens - current_tokens} tokens)")
                    return optimized_history

        # otherwise, we just try to compress youtube messages until we are under the limit or we have just one (non-compressed) message left
        while current_tokens > self.max_tokens:
            print(f"[MemoryManager] More than one YouTube message detected, attempting compression")
            # Compress messages starting with the oldest until we're under the limit
            compressed_count = 0
            # Find the newest valid YouTube message
            last_valid_youtube_index = max(
                (idx for idx in message_indices if idx < len(optimized_history) and "transcript_version" in self.youtube_messages[idx]),
                default=-1
            )
            for idx in message_indices:
                # If its the last youtube message we go straight to removing the two oldest messages until we are under the limit
                # This is to avoid removing the last youtube link as it may be relevant to the conversation
                if idx == last_valid_youtube_index:
                    print(f"[MemoryManager] Last YouTube message detected, prioritizing removal of oldest messages")
                    while True:
                        optimized_history = self.remove_oldest_message_pair(optimized_history)
                        current_tokens = self.count_tokens(optimized_history)
                        print(f"[MemoryManager] Current token count after removal: {current_tokens}/{self.max_tokens} tokens")
                        if current_tokens <= self.max_tokens:
                            print(f"[MemoryManager] Context optimized successfully after removing messages")
                            print(f"[MemoryManager] Tokens reduced: {original_tokens} → {current_tokens} (saved {original_tokens - current_tokens} tokens)")
                            return optimized_history

                if idx >= len(optimized_history):
                    continue  # Skip if index is out of bounds

                # Replace transcript version with link version if this message is tracked
                if "link_version" in self.youtube_messages[idx] and idx < len(optimized_history):
                    # Check if the current content is the transcript version or contains substantial parts of it
                    current_content = optimized_history[idx]["content"]
                    transcript_version = self.youtube_messages[idx]["transcript_version"]
                    link_version = self.youtube_messages[idx]["link_version"]

                    # Only compress if it's not already the link version
                    if current_content != link_version:
                        video_title = self.youtube_messages[idx].get("video_title", "Unknown Video")
                        print(f"[MemoryManager] Compressing message {idx} ('{video_title}')")

                        optimized_history[idx]["content"] = link_version
                        compressed_count += 1

                        # Recalculate token count
                        current_tokens = self.count_tokens(optimized_history)
                        if current_tokens <= self.max_tokens:
                            print(f"[MemoryManager] Context optimized successfully after compressing {compressed_count} messages")
                            print(f"[MemoryManager] Tokens reduced: {original_tokens} → {current_tokens} (saved {original_tokens - current_tokens} tokens)")
                            break # Exit loop immediately after reaching the token limit
                    else:
                        print(f"[MemoryManager] Message {idx} already compressed, skipping")
                else:
                    print(f"[MemoryManager] Message {idx} not tracked, skipping")


        if current_tokens > self.max_tokens:
            print(f"[MemoryManager] WARNING: Context still exceeds token limit after optimization!")
            print(f"[MemoryManager] Current: {current_tokens}/{self.max_tokens} tokens (still {current_tokens - self.max_tokens} tokens over)")

        return optimized_history

    def expand_context(self, chat_history):
        """
        Expand the context by including full transcripts where possible.
        Returns an expanded copy of the chat history.
        """
        print(f"\n[MemoryManager] Starting context expansion...")
        print(f"[MemoryManager] YouTube messages tracked: {len(self.youtube_messages)}")

        # Make a deep copy of chat history
        expanded_history = json.loads(json.dumps(chat_history))

        # Calculate current token count
        current_tokens = self.count_tokens(expanded_history)
        original_tokens = current_tokens

        # Sort YouTube messages from newest to oldest
        message_indices = sorted(self.youtube_messages.keys(), reverse=True)
        expanded_count = 0

        # Try to expand each message, starting with the newest
        for idx in message_indices:
            if idx >= len(expanded_history):
                continue  # Skip if index is out of bounds

            # Check if this message can be expanded
            if "transcript_version" in self.youtube_messages[idx]:
                video_title = self.youtube_messages[idx].get("video_title", "Unknown Video")
                print(f"[MemoryManager] Attempting to expand message {idx} ('{video_title}')")

                # Temporarily expand this message
                original_content = expanded_history[idx]["content"]
                expanded_history[idx]["content"] = self.youtube_messages[idx]["transcript_version"]

                # Check if we're still under the token limit
                new_tokens = self.count_tokens(expanded_history)

                if new_tokens > self.max_tokens:
                    # Revert the expansion
                    print(f"[MemoryManager] Cannot expand message {idx} - would exceed token limit ({new_tokens} tokens)")
                    expanded_history[idx]["content"] = original_content
                else:
                    # Keep the expansion
                    expanded_count += 1
                    print(f"[MemoryManager] Successfully expanded message {idx} ({current_tokens} → {new_tokens} tokens)")
                    current_tokens = new_tokens

        print(f"[MemoryManager] Expansion complete: {expanded_count} messages expanded")
        print(f"[MemoryManager] Token count: {original_tokens} → {current_tokens} (+{current_tokens - original_tokens} tokens)")

        return expanded_history

    def prepare_messages_for_api(self, chat_history):
        """
        Prepare messages to be sent to the API by optimizing context.
        First tries to expand transcripts, then compresses if needed.

        Returns:
            list: The prepared messages for the API call.
        """
        print(f"\n[MemoryManager] Preparing messages for API call...")

        # First try to expand messages with full transcripts
        expanded = self.expand_context(chat_history)
        expanded_tokens = self.count_tokens(expanded)

        # Then optimize if we're over the limit
        if expanded_tokens > self.max_tokens:
            print(f"[MemoryManager] Expanded context exceeds token limit, compressing...")
            optimized = self.optimize_context(expanded)
            final_tokens = self.count_tokens(optimized)
            print(f"[MemoryManager] Final context: {final_tokens}/{self.max_tokens} tokens ({(final_tokens/self.max_tokens)*100:.1f}%)")
            print(f"[MemoryManager] YouTube transcripts: {sum(1 for msg in optimized if any(transcript in msg.get('content', '') for transcript in ['transcrição completa do vídeo', 'responda a mensagem do usuário considerando o conteúdo do vídeo']))} included")
            print(f"[MemoryManager] YouTube links only: {sum(1 for msg in optimized if 'Source:' in msg.get('content', '') and 'youtube' in msg.get('content', ''))}")
            return optimized

        print(f"[MemoryManager] Final context: {expanded_tokens}/{self.max_tokens} tokens ({(expanded_tokens/self.max_tokens)*100:.1f}%)")
        print(f"[MemoryManager] YouTube transcripts: {sum(1 for msg in expanded if any(transcript in msg.get('content', '') for transcript in ['transcrição completa do vídeo', 'responda a mensagem do usuário considerando o conteúdo do vídeo']))} included")
        print(f"[MemoryManager] YouTube links only: {sum(1 for msg in expanded if 'Source:' in msg.get('content', '') and 'youtube' in msg.get('content', ''))}")

        return expanded

    def extract_youtube_url(self, message):
        """Extract YouTube URL from a message."""
        url_pattern = r'\b((?:https?://)?(?:www\.)?youtube\.com/watch\?v=[a-zA-Z0-9_-]+|(?:https?://)?youtu\.be/[a-zA-Z0-9_-]+)\b'
        match = re.search(url_pattern, message)
        if match:
            return match.group(0)
        return None

    def scan_chat_for_youtube_messages(self, chat_history):
        """
        Scans chat history to identify and register YouTube messages that contain both link and transcript versions.
        This helps restore memory manager state when loading a saved session.

        Args:
            chat_history: List of chat messages to scan
        """
        print("[MemoryManager] Scanning chat history for YouTube content...")

        # Look for patterns that suggest YouTube content
        for idx, message in enumerate(chat_history):
            if message['role'] != 'user':
                continue

            content = message.get('content', '')

            # Extract YouTube URL if present
            youtube_url = self.extract_youtube_url(content)

            if youtube_url:
                # Check if this message contains a transcript
                transcript_markers = [
                    'transcrição completa do vídeo',
                    'responda a mensagem do usuário considerando o conteúdo do vídeo'
                ]

                has_transcript = any(marker in content for marker in transcript_markers)

                if has_transcript:
                    # Extract the link version (shorter version with just the URL)
                    # This is an estimate - the actual link version might be different
                    link_version = f"Source: {youtube_url}"

                    # Get video title if possible (from content)
                    title_match = re.search(r'título: "(.*?)"', content)
                    video_title = title_match.group(1) if title_match else "Unknown Video"

                    print(f"[MemoryManager] Found YouTube message at index {idx}: {video_title}")

                    # Register this as a YouTube message with both versions
                    self.register_youtube_message(
                        idx,
                        link_version,
                        content,
                        video_title
                    )

        print(f"[MemoryManager] Scan complete. Found {len(self.youtube_messages)} YouTube messages.")

    def remove_oldest_message_pair(self, chat_history):
        """Removes the oldest message pair (user message and its corresponding assistant response) from memory.

        Args:
            chat_history (list): List of chat messages to do an cleanup on

        Returns:
            list: The updated chat history with the oldest message pair removed.
        """
        try:
            # Find the first user message
            user_message_index = next((i for i, msg in enumerate(chat_history) if msg['role'] == 'user'), None)
            if user_message_index is not None:
                user_was_saying = chat_history[user_message_index]['content']
                # Remove the user message
                chat_history.pop(user_message_index)
                # Find the corresponding assistant message (now at user_message_index)
                assistant_message_index = next((i for i in range(user_message_index, len(chat_history)) if chat_history[i]['role'] == 'assistant'), None)
                if assistant_message_index is not None:
                    assistant_was_saying = chat_history[assistant_message_index]['content']
                    # Remove the assistant message
                    chat_history.pop(assistant_message_index)
                print("[MemoryManager] Removed oldest message pair where:")
                print(f"  User: {user_was_saying[:15]}...")
                print(f"  Assistant: {assistant_was_saying[:15]}...")

                # Update YouTube message indices after removal
                self.update_youtube_message_indices_offset(user_message_index)

        except Exception as e:
            print(f"[MemoryManager] Something went wrong while removing the oldest message pair: {e}")
        return chat_history

    def update_youtube_message_indices_offset(self, removed_index):
        """Updates the indices of YouTube messages after one is removed by adjusting all their indices.
        Since messages are removed in pairs, we just subtract 2 from all indices and pop any negative ones.
        This function is called after removing the oldest message pair.
        Args:
            removed_index (int): The index of the removed message.
        """
        # Create a list of current indices to avoid modifying the dict while iterating
        indices = list(self.youtube_messages.keys())

        # Create a list of (old_index, new_index) adjustments
        adjustments = []
        for idx in indices:
            if idx > removed_index:
                new_index = idx - 2
                adjustments.append((idx, new_index))
            elif idx == removed_index:
                adjustments.append((idx, None))  # Mark for removal

        # Apply adjustments in reverse order to prevent index shifting conflicts
        for old_idx, new_idx in sorted(adjustments, key=lambda x: -x[0]):
            if new_idx is not None:
                if new_idx in self.youtube_messages:
                    # Handle collision by appending to existing content (merge if needed)
                    self.youtube_messages[new_idx].update(self.youtube_messages[old_idx])
                else:
                    self.youtube_messages[new_idx] = self.youtube_messages.pop(old_idx)
            else:
                self.youtube_messages.pop(old_idx, None)

        # Shift all remaining indices down by 2
        self.youtube_messages = {(k - 2): v for k, v in self.youtube_messages.items()}

        # Remove any invalid indices that might have gone negative
        self.youtube_messages = {k: v for k, v in self.youtube_messages.items() if k >= 0}

    def get_youtube_messages(self):
        """Returns the stored YouTube messages."""
        return self.youtube_messages

    def get_youtube_messages_count(self):
        """Returns the count of stored YouTube messages."""
        return len(self.youtube_messages)

    def get_youtube_message(self, message_index):
        """Returns the YouTube message at the specified index."""
        return self.youtube_messages.get(message_index, None)

    def clear_youtube_messages(self):
        """Clears all stored YouTube metadata."""
        previous_count = len(self.youtube_messages)
        self.youtube_messages = {}
        print(f"[MemoryManager] Reset YouTube messages: {previous_count} videos removed from memory")