import unittest
from unittest.mock import MagicMock, patch
import sys
from memory_manager import MemoryManager
from AI_Generator import APIHandler

class TestMemoryManager(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        """Recreate the log file as empty before starting the tests"""
        with open('TestMemoryManager_log.txt', 'w', encoding='utf-8') as log_file:
            pass

    def setUp(self):
        self.api_handler = APIHandler()
        self.memory_manager = MemoryManager(self.api_handler, max_tokens=1000)
        self.memory_manager.youtube_messages = {}  # Explicitly reset the YouTube messages

        # Open a file for logging print statements in append mode
        self.log_file = open('TestMemoryManager_log.txt', 'a', encoding='utf-8')

        # Add a separator with the test method name
        separator = f"\n{'-' * 80}\n{self._testMethodName}\n{'-' * 80}\n"
        self.log_file.write(separator)

        # Redirect sys.stdout to the log file
        self.original_stdout = sys.stdout
        sys.stdout = self.log_file

        # Define the real YouTube URL to use in tests
        self.youtube_url = "https://www.youtube.com/watch?v=yBUmQciTJfo"
        self.link_prefix = "Source: "

        # Calculate token sizes for link version
        self.link_version = f"{self.link_prefix}{self.youtube_url}"
        self.link_token_count = len(self.link_version) // 4

        # Default chat history and memory state for link registering for tests that needs links and transcripts
        self.chat_history = [
            {"role": "user", "content": "Sobre oq é essa musica?? Source: https://www.youtube.com/watch?v=i1csLh-0L9E"},
            {"role": "assistant", "content": "Cara, você tá querendo entrar no jogo dos poucos, né? \n\nEssa música é tipo um hino para quem quer ser um dos \"donos do mundo\". E olha, eu entendo. Ser um dos poucos que mandam na vida é um sonho, mas também é uma grande responsabilidade.\n\nA questão é: você tá preparado pra isso? Porque se você quer entrar nesse time, precisa estar disposto a pagar o preço."},
            {"role": "user", "content": "Me conta mais??"}
        ]

        self.chat_history_expanded = [
            {"role": "user", "content": "Sobre oq é essa musica??\n\nO usuário acabou de te enviar um link, segue abaixo a transcrição completa do vídeo com título: The Few &amp; The Many - S3RL, esta mesma pode conter erros de digitação ou falas misturadas caso o video possua mais de um narrador. Por favor, ignore quaisquer erros de digitação e foque na mensagem geral do conteúdo ao responder o usuário.\n\nfrom the beginning of History the few\nhave always exploited the\n[Music]\n[Music]\nmany whatever it takes make sure you're\none of the few not one of the\nmany\n[Music]\nwhatever it takes\nfrom the beginning of History the few\nhave always exploited the\n[Music]\nmany\n[Music]\n[Music]\nwhatever it takes make sure you're one\nof the few not one of the\nmany\nw\n[Music]\nready\n\n Agora, por favor, responda a mensagem do usuário considerando o conteúdo do vídeo acima, lembre-se de por personalidade e emoção em suas respostas!"},
            {"role": "assistant", "content": "Cara, você tá querendo entrar no jogo dos poucos, né? \n\nEssa música é tipo um hino para quem quer ser um dos \"donos do mundo\". E olha, eu entendo. Ser um dos poucos que mandam na vida é um sonho, mas também é uma grande responsabilidade.\n\nA questão é: você tá preparado pra isso? Porque se você quer entrar nesse time, precisa estar disposto a pagar o preço."},
            {"role": "user", "content": "Me conta mais??"}
        ]

        # Token counts (I verified them using the test_tokenizer.py)
        self.chat_history_api_token_count = 132
        self.chat_history_fallback_token_count = 113
        self.chat_history_expanded_token_count = 337
        self.chat_history_expanded_fallback_token_count = 313

        self.memory_state = [
            {"youtube_messages": {
                0: {
                    "link_version": "Sobre oq é essa musica?? Source: https://www.youtube.com/watch?v=i1csLh-0L9E",
                    "transcript_version": "Sobre oq é essa musica??\n\nO usuário acabou de te enviar um link, segue abaixo a transcrição completa do vídeo com título: The Few &amp; The Many - S3RL, esta mesma pode conter erros de digitação ou falas misturadas caso o video possua mais de um narrador. Por favor, ignore quaisquer erros de digitação e foque na mensagem geral do conteúdo ao responder o usuário.\n\nfrom the beginning of History the few\nhave always exploited the\n[Music]\n[Music]\nmany whatever it takes make sure you're\none of the few not one of the\nmany\n[Music]\nwhatever it takes\nfrom the beginning of History the few\nhave always exploited the\n[Music]\nmany\n[Music]\n[Music]\nwhatever it takes make sure you're one\nof the few not one of the\nmany\nw\n[Music]\nready\n\n Agora, por favor, responda a mensagem do usuário considerando o conteúdo do vídeo acima, lembre-se de por personalidade e emoção em suas respostas!",
                    "video_title": "The Few &amp; The Many - S3RL"
                }
            }
        }
        ]

    def tearDown(self):
        """Clean up after each test"""
        # Clear the memory manager's YouTube messages
        self.memory_manager.clear_youtube_messages()
        # Add a separator after each test
        separator = f"\n{'=' * 80}\nEnd of {self._testMethodName}\n{'=' * 80}\n"
        self.log_file.write(separator)
        # Close the log file
        self.log_file.close()
        # Restore stdout
        sys.stdout = self.original_stdout

    def test_init(self):
        """Test initialization of MemoryManager"""
        self.assertEqual(self.memory_manager.max_tokens, 1000)
        self.assertEqual(self.memory_manager.model, "Sao10K-70B-L3.3-Cirrus-x1")
        self.assertEqual(self.memory_manager.youtube_messages, {})
        self.assertEqual(self.memory_manager.api_handler, self.api_handler)

    def test_register_youtube_message(self):
        """Test registering a YouTube message"""
        message_index = 0
        link_version = "O que acha?? Source: https://youtube.com/watch?v=abcdef"
        transcript_version = "O que acha?? [Full transcript here]"
        video_title = "Test Video"

        self.memory_manager.register_youtube_message(
            message_index,
            link_version,
            transcript_version,
            video_title
        )

        expected = {
            message_index: {
                "link_version": link_version,
                "transcript_version": transcript_version,
                "video_title": video_title
            }
        }
        self.assertEqual(self.memory_manager.youtube_messages, expected)

    def test_count_tokens(self):
        """Test token counting"""
        messages = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm fine, thank you!"},
            {"role": "user", "content": "What can you do?"}
        ]

        # convert messages into freeform string without roles
        messages_str = "\n\n".join(message['content'] for message in messages)
        expected_tokens_api = 18
        expected_tokens_fallback = len(messages_str) // 4 # 14

        tokens = self.memory_manager.count_tokens(messages)
        self.assertEqual(tokens, expected_tokens_api)

        # Test fallback when API returns no token_count
        with patch.object(self.api_handler, 'count_tokens', return_value={}):
            tokens = self.memory_manager.count_tokens(messages)
            self.assertEqual(tokens, expected_tokens_fallback)

    def test_optimize_context_under_limit(self):
        """Test optimize_context when we know the full transcript fits inside context window"""

        optimized = self.memory_manager.prepare_messages_for_api(self.chat_history) #expands then calls optimize_context
        self.assertEqual(optimized[1]["content"], self.chat_history[1]["content"])
        # The transcript should be unchanged as it fits within the token limit
        self.assertEqual(optimized, self.chat_history)

    def test_optimize_context_over_limit(self):
        """Test optimize_context when over token limit and just one link"""
        # Register a YouTube message""""
        # Create a chat history that exceeds token limit slightly
        long_chat = self.chat_history_expanded.copy()
        # edit the assistant message to be longer
        long_chat[1]["content"] *= 8 # now the total context is 1030 tokens

        self.assertEqual(self.memory_manager.count_tokens(long_chat), 1030)

        link_version = self.memory_state[0]["youtube_messages"][0]["link_version"]
        transcript_version = self.memory_state[0]["youtube_messages"][0]["transcript_version"]
        video_title = self.memory_state[0]["youtube_messages"][0]["video_title"]

        # Register the YouTube message
        self.memory_manager.register_youtube_message(0, link_version, transcript_version, video_title)

        # Optimize the context
        optimized = self.memory_manager.prepare_messages_for_api(long_chat) #expands then calls optimize_context
        # The original user message should be replaced with the link version to save tokens
        self.assertEqual(optimized[0]["content"], link_version, "it failed to replace the user message with the link version")
        # The assistant message should remain unchanged
        self.assertEqual(optimized[1]["content"], long_chat[1]["content"])
        # the token count should now be 825 tokens
        self.assertEqual(self.memory_manager.count_tokens(optimized), 825)

    def test_expand_context(self):
        """Test expand_context functionality"""
        # Register a YouTube message
        link_version = "Source: https://youtube.com/watch?v=abcdef"
        transcript_version = "This is a short transcript that should fit within token limits."
        self.memory_manager.register_youtube_message(0, link_version, transcript_version, "Test Video")

        chat_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": link_version}
        ]

        # The expandor should replace the link with the transcript version
        expanded = self.memory_manager.expand_context(chat_history)
        self.assertEqual(expanded[0]["content"], transcript_version)

    def test_expand_context_over_limit(self):
        """Test expand_context when expansion would exceed token limit"""
        # Create a memory manager with a very low token limit
        self.memory_manager = MemoryManager(self.api_handler, max_tokens=400)  # Just enough for links but not transcripts

        # Register a YouTube message with a long transcript
        link_version = "Hello, can you summarize this? Source: https://youtube.com/watch?v=abcdef"
        long_transcript = "This is a long transcript that exceeds the token limit. " * 50  # Make it long
        # Register the message
        self.memory_manager.register_youtube_message(0, link_version, long_transcript, "Long Video")

        chat_history = [
            {"role": "user", "content": link_version},
            {"role": "assistant", "content": "Of course! Its about..."},
            {"role": "user", "content": "Tell me more"}
        ]

        # The expandor should not expand this message as it would exceed the token limit
        expanded = self.memory_manager.expand_context(chat_history)
        self.assertEqual(expanded[0]["content"], link_version)  # Should remain unchanged

    def test_prepare_messages_for_api(self):
        """Test prepare_messages_for_api workflow using realistic YouTube formatting"""
        # Use the real YouTube URL
        youtube_url = "https://www.youtube.com/watch?v=yBUmQciTJfo"
        user_message = "Can you summarize this video? " + youtube_url

        # Format messages like UserInputValidator would
        message_without_link = "Can you summarize this video?"
        video_title = "Test Video Title"

        # Create link version like UserInputValidator does
        link_version = f"{message_without_link} Source: {youtube_url}"

        # Create transcript version like UserInputValidator does - with the same Portuguese text
        transcript_content = "This is the transcript content of the video. " * 5
        instructions = f"\n\nO usuário acabou de te enviar um link, segue abaixo a transcrição completa do vídeo com título: {video_title}, esta mesma pode conter erros de digitação ou falas misturadas caso o video possua mais de um narrador. Por favor, ignore quaisquer erros de digitação e foque na mensagem geral do conteúdo ao responder o usuário.\n\n{transcript_content}\n\n Agora, por favor, responda a mensagem do usuário considerando o conteúdo do vídeo acima, lembre-se de por personalidade e emoção em suas respostas!"
        transcript_version = f"{message_without_link}{instructions}"

        # Register messages with realistic formatting
        self.memory_manager.register_youtube_message(0, link_version, transcript_version, video_title)

        # Create another version for the second message
        message_without_link = "Tell me now about this one"
        youtube_url2 = "https://www.youtube.com/watch?v=yBUmQciTJfo&t=10s"
        link_version2 = f"{message_without_link} Source: {youtube_url2}"
        transcript_version2 = f"{message_without_link}{instructions}"
        self.memory_manager.register_youtube_message(2, link_version2, transcript_version2, "Video 2")

        chat_history = [
            {"role": "user", "content": link_version},
            {"role": "assistant", "content": "Of course! Its about..."},
            {"role": "user", "content": link_version2},
            {"role": "assistant", "content": "Oh, this one is about..."}
        ]

        # Test expansion with adequate token limit
        prepared = self.memory_manager.prepare_messages_for_api(chat_history)
        self.assertEqual(prepared[0]["content"], transcript_version)
        self.assertEqual(prepared[2]["content"], transcript_version2)

        # ensure the assistant messages are unchanged
        self.assertEqual(prepared[1]["content"], chat_history[1]["content"])
        self.assertEqual(prepared[3]["content"], chat_history[3]["content"])

        # Calculate token estimates for setting proper limits
        link_tokens = len(link_version) // 4
        transcript_tokens = len(transcript_version) // 4

        # Create a memory manager with a token limit that will force compression
        memory_manager_low_limit = MemoryManager(self.api_handler, max_tokens=100)  # Just enough for links but not transcripts

        # Create longer transcripts for low token limit test
        long_instructions = instructions * 2  # Make it even longer
        long_transcript1 = f"{message_without_link}{long_instructions}"
        long_transcript2 = long_transcript1

        memory_manager_low_limit.register_youtube_message(0, link_version, long_transcript1, video_title)
        memory_manager_low_limit.register_youtube_message(2, link_version2, long_transcript2, "Video 2")

        # Test compression with low token limit
        prepared_low_limit = memory_manager_low_limit.prepare_messages_for_api(chat_history)

        # Ensure the assistant messages are unchanged
        self.assertEqual(prepared_low_limit[1]["content"], chat_history[1]["content"])
        self.assertEqual(prepared_low_limit[3]["content"], chat_history[3]["content"])

        # Check that the oldest (0) and the newest (2) messages are compressed
        self.assertEqual(prepared_low_limit[0]["content"], link_version)
        self.assertEqual(prepared_low_limit[2]["content"], link_version2)

        # Verify that some compression happened
        compressed_count = sum(1 for idx in [0, 2] if "Source:" in prepared_low_limit[idx]["content"])
        self.assertGreater(compressed_count, 0, "At least one message should be compressed to link version")

        # Additional verification - make sure token count is within limits
        token_count = memory_manager_low_limit.count_tokens(prepared_low_limit)
        self.assertLessEqual(token_count, memory_manager_low_limit.max_tokens)

    def test_prepare_messages_compresses_oldest_link_first(self):
        """Test prepare_messages_for_api prioritizes compressing oldest links when tokens are limited"""

        # Set max_tokens to fit transcript2 but not transcript1
        self.memory_manager = MemoryManager(self.api_handler, max_tokens=450)

        # Register two YouTube messages with different transcript lengths
        link1 = "Source: https://youtube.com/watch?v=123"
        # ~300 tokens
        transcript1 = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum ac dignissim arcu." * 15
        link2 = "Source: https://youtube.com/watch?v=456"
        # ~400 tokens
        transcript2 = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum ac dignissim arcu." * 20

        self.memory_manager.register_youtube_message(0, link1, transcript1, "Video1")
        self.memory_manager.register_youtube_message(2, link2, transcript2, "Video2")

        chat_history = [
            {"role": "user", "content": link1},
            {"role": "assistant", "content": "About Video1..."},
            {"role": "user", "content": link2},
            {"role": "assistant", "content": "About Video2..."}
        ]

        prepared = self.memory_manager.prepare_messages_for_api(chat_history)

        # Assert that the assistant messages are unchanged
        self.assertEqual(prepared[1]["content"], chat_history[1]["content"])
        self.assertEqual(prepared[3]["content"], chat_history[3]["content"])

        # check if user oldest message is compressed comparing if they are now NOT over 100 tokens
        self.assertLess(len(prepared[0]["content"]), 100, "Oldest link should be compressed to save tokens")
        # second user message should be around 400 tokens
        self.assertGreater(len(prepared[2]["content"]), 390, "Newest link should remain expanded")

        # Oldest link (0) should be compressed to save tokens
        self.assertEqual(prepared[0]["content"], link1)
        # Newest link (2) should remain expanded
        self.assertEqual(prepared[2]["content"], transcript2)

    def test_extract_youtube_url(self):
        """Test YouTube URL extraction"""
        test_cases = [
            ("Check this video: https://www.youtube.com/watch?v=abcdef", "https://www.youtube.com/watch?v=abcdef"),
            ("Short URL: https://youtu.be/abcdef", "https://youtu.be/abcdef"),
            ("No URL here", None),
            ("Invalid URL: https://notube.com/watch?v=abcdef", None)
        ]

        for input_message, expected_output in test_cases:
            self.assertEqual(self.memory_manager.extract_youtube_url(input_message), expected_output)

    def test_clear_youtube_messages(self):
        """Test clearing YouTube message registry"""
        self.memory_manager.register_youtube_message(0, "link", "transcript", "Video1")
        self.memory_manager.register_youtube_message(1, "link2", "transcript2", "Video2")
        self.memory_manager.clear_youtube_messages()
        self.assertEqual(len(self.memory_manager.youtube_messages), 0)

    def test_remove_oldest_message_pair(self):
        """Test removing the oldest message pair from chat history"""
        self.memory_manager = MemoryManager(self.api_handler, max_tokens=2048)

        # Register some YouTube messages
        self.memory_manager.register_youtube_message(0, "Source: https://youtube.com/watch?v=123", "Transcript 1", "Video1")
        self.memory_manager.register_youtube_message(2, "Source: https://youtube.com/watch?v=456", "Transcript 2", "Video2")
        self.memory_manager.register_youtube_message(4, "Source: https://youtube.com/watch?v=789", "Transcript 3", "Video3")

        chat_history = [
            {"role": "user", "content": "Message 1 Source: https://youtube.com/watch?v=123"},
            {"role": "assistant", "content": "Response to Message 1"},
            {"role": "user", "content": "Message 2 Source: https://youtube.com/watch?v=456"},
            {"role": "assistant", "content": "Response to Message 2"},
            {"role": "user", "content": "Message 3 Source: https://youtube.com/watch?v=789"},
            {"role": "assistant", "content": "Response to Message 3"}
        ]

        # Token count before removal
        initial_token_count = self.memory_manager.count_tokens(chat_history)

        # Remove the oldest message pair
        updated_chat_history = self.memory_manager.remove_oldest_message_pair(chat_history)

        # Token count after removal
        final_token_count = self.memory_manager.count_tokens(updated_chat_history)

        # Check if the oldest message pair was removed
        self.assertEqual(len(updated_chat_history), 4)  # Should remove 2 messages

        # It should now take less space
        self.assertLess(final_token_count, initial_token_count)

    def test_update_youtube_message_indices_offset(self):
        """Test updating YouTube message indices after removing a message pair"""
        self.memory_manager = MemoryManager(self.api_handler, max_tokens=2048)

        # Register some YouTube messages
        self.memory_manager.register_youtube_message(0, "Source: https://youtube.com/watch?v=123", "Transcript 1", "Video1")
        self.memory_manager.register_youtube_message(2, "Source: https://youtube.com/watch?v=456", "Transcript 2", "Video2")
        self.memory_manager.register_youtube_message(4, "Source: https://youtube.com/watch?v=789", "Transcript 3", "Video3")

        youtube_messages_before_removal = self.memory_manager.get_youtube_messages()
        # assert the 3 indices are 0, 2 and 4
        self.assertEqual(sorted(list(youtube_messages_before_removal.keys())), [0, 2, 4])

        chat_history = [
            {"role": "user", "content": "Message 1 Source: https://youtube.com/watch?v=123"},
            {"role": "assistant", "content": "Response to Message 1"},
            {"role": "user", "content": "Message 2 Source: https://youtube.com/watch?v=456"},
            {"role": "assistant", "content": "Response to Message 2"},
            {"role": "user", "content": "Message 3 Source: https://youtube.com/watch?v=789"},
            {"role": "assistant", "content": "Response to Message 3"}
        ]

        # Remove the oldest message pair
        updated_chat_history = self.memory_manager.remove_oldest_message_pair(chat_history)

        # It should go from 3 to 2 youtube messages
        self.assertEqual(self.memory_manager.get_youtube_messages_count(), 2)
        # Check if the indices were correctly shifted from 2 to 0 and 4 to 2
        youtube_messages = self.memory_manager.get_youtube_messages()
        self.assertEqual(sorted(youtube_messages.keys()), [0, 2])

    def test_9_messages_single_youtube_link(self):
        """
        Verify that with chat history with:
          - at 9 messages
          - single YouTube link

          1. the oldest message pair is removed
          2. while keeping the YouTube link expanded.
        """
        # Create a memory manager with a token limit that forces removal
        self.memory_manager = MemoryManager(self.api_handler, max_tokens=400)  # Token limit set to 400

        # Register a YouTube message
        link_version = "Source: https://youtube.com/watch?v=123"
        transcript_version = "transcrição completa do vídeo: This is a long transcript. " * 20  # ~250 tokens
        self.memory_manager.register_youtube_message(7, link_version, transcript_version, "Video1")

        # Create a chat history with 9 messages (sys + 1 YouTube link + 7 regular)
        chat_history = [ # 41 tokens while compressed (~291 tokens uncompressed)
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Response 3"},
            {"role": "user", "content": link_version}, # message 07
            {"role": "assistant", "content": "Response 4"}
        ]

        # Assert it starts with 9 messages
        self.assertEqual(len(chat_history), 9, "Should start with 9 messages")

        # expand the context to replace the link with the transcript
        chat_history = self.memory_manager.expand_context(chat_history)
        # it should be over 41 since it will expand the link
        assert self.memory_manager.count_tokens(chat_history) > 41

        # reduce max_tokens to force removal of just one message pair and then optimize it
        self.memory_manager.max_tokens = 283
        optimized = self.memory_manager.prepare_messages_for_api(chat_history)

        # Verify the oldest message pair was removed and that sys message was kept
        self.assertEqual(optimized[0]["role"], "system", "System message should be kept")
        self.assertEqual(len(optimized), 7, "Should have 7 messages since two were removed")

        # Verify the YouTube link remains expanded (since two messages were removed, its now at index 5)
        self.assertEqual(optimized[5]["content"], transcript_version)
        # Verify token count is now at 283 or less
        self.assertLessEqual(self.memory_manager.count_tokens(optimized), 283)

# Run using: pytest .\test_memory_manager.py -v
if __name__ == '__main__':
    unittest.main()