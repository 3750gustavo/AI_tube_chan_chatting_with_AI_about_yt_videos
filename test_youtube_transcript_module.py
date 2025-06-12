import unittest
from unittest.mock import patch, Mock, MagicMock
from youtube_transcript_module import YouTubeTranscriptDownloader
import requests

class TestYouTubeTranscriptDownloader(unittest.TestCase):
    def setUp(self):
        self.downloader = YouTubeTranscriptDownloader()

    # Test get_video_id method
    def test_get_video_id_valid_urls(self):
        test_cases = [
            ("https://www.youtube.com/watch?v=-F38ApPZ5q8", "-F38ApPZ5q8"),
            ("https://youtu.be/DQmfRx5TD1o", "DQmfRx5TD1o"),
            ("https://www.youtube.com/watch?v=DQmfRx5TD1o&feature=youtu.be", "DQmfRx5TD1o"),
            ("https://tinyurl.com/358tnn3v", "DQmfRx5TD1o"),
            ("https://www.youtube.com/embed/DQmfRx5TD1o?rel=0", "DQmfRx5TD1o"),
        ]
        for url, expected_id in test_cases:
            with self.subTest(url=url):
                self.assertEqual(self.downloader.get_video_id(url), expected_id)

    def test_get_video_id_invalid_urls(self):
        invalid_urls = [
            "https://www.youtube.com/",
            "https://youtu.be/",
            "https://www.youtube.com/watch",
            "https://www.youtube.com/watch?v=",
            "https://example.com/watch?v=DQmfRx5TD1o",
            "https://tinyurl.com/invalid",
        ]
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertIsNone(self.downloader.get_video_id(url))

    # Test get_video_title method
    @patch('requests.get')
    def test_get_video_title_success(self, mock_get):
        mock_response = Mock()
        mock_response.text = '<title>Perk Machines and Paychecks The Illusion of Progress in Life - YouTube</title>'
        mock_get.return_value = mock_response
        title = self.downloader.get_video_title("-F38ApPZ5q8")
        self.assertEqual(title, "Perk Machines and Paychecks The Illusion of Progress in Life")

    @patch('requests.get')
    def test_get_video_title_request_exception(self, mock_get):
        mock_get.side_effect = requests.RequestException("Connection error")
        title = self.downloader.get_video_title("invalid_id")
        self.assertEqual(title, "Desconhecido")

    @patch('requests.get')
    def test_get_video_title_no_title_found(self, mock_get):
        mock_response = Mock()
        mock_response.text = "<html><body>No title here</body></html>"
        mock_get.return_value = mock_response
        title = self.downloader.get_video_title("invalid_id")
        self.assertEqual(title, "Desconhecido")

    # Test download_transcript method
    def test_download_transcript_en_exists(self):
        transcript = self.downloader.download_transcript("-F38ApPZ5q8")
        self.assertTrue(len(transcript) > 100)  # Ensure substantial transcript content

    def test_download_transcript_pt_exists(self):
        transcript = self.downloader.download_transcript("DQmfRx5TD1o")
        self.assertTrue(len(transcript) > 100)

    @patch('youtube_transcript_api.YouTubeTranscriptApi.list_transcripts')
    def test_download_transcript_no_transcript(self, mock_list_transcripts):
        mock_list_transcripts.side_effect = Exception("No transcript found")
        transcript = self.downloader.download_transcript("invalid_id")
        self.assertEqual(transcript, "")

    # Test save_transcript method
    @patch('youtube_transcript_module.open', new_callable=MagicMock)
    @patch('youtube_transcript_module.YouTubeTranscriptDownloader.get_video_title')
    def test_save_transcript_success(self, mock_get_title, mock_open):
        mock_get_title.return_value = "Test Title"
        result = self.downloader.save_transcript("test_id", "Transcript content")
        self.assertEqual(result, "Test Title.txt")
        mock_open.assert_called_once_with("Test Title.txt", "w", encoding="utf-8")

    def test_save_transcript_empty_content(self):
        result = self.downloader.save_transcript("test_id", "")
        self.assertIsNone(result)

    @patch('youtube_transcript_module.open', side_effect=IOError("Write error"))
    @patch('youtube_transcript_module.YouTubeTranscriptDownloader.get_video_title')
    def test_save_transcript_write_error(self, mock_get_title, mock_open):
        mock_get_title.return_value = "Test Title"
        result = self.downloader.save_transcript("test_id", "Transcript content")
        self.assertIsNone(result)

    # Negative test cases
    def test_download_invalid_video_id(self):
        transcript = self.downloader.download_transcript("invalid_id_123")
        self.assertEqual(transcript, "")

    @patch('youtube_transcript_api.YouTubeTranscriptApi.list_transcripts')
    def test_download_transcript_language_not_found(self, mock_list_transcripts):
        mock_list_transcripts.return_value.find_generated_transcript.side_effect = Exception("Language not available")
        transcript = self.downloader.download_transcript("test_id")
        self.assertEqual(transcript, "")

# Run using: pytest .\test_youtube_transcript_module.py -v