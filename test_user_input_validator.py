import pytest
from pytest_mock import mocker
import pytest
from user_input_validator import UserInputValidator

@pytest.fixture
def validator():
    return UserInputValidator()

@pytest.fixture
def valid_url():
    return "https://www.youtube.com/watch?v=Vjm8j0UCqVc"

@pytest.fixture
def invalid_url():
    return "https://example.com/not-a-youtube-url"

@pytest.fixture
def no_url_message():
    return "This is a message without any links."

def test_valid_youtube_url(validator, valid_url):
    message_to_store, message_to_send, youtube_metadata = validator.process_message_with_link(valid_url)

    assert valid_url in message_to_store
    assert "O usuário acabou de te enviar um link" in message_to_send
    assert "transcrição" in message_to_send.lower()
    assert youtube_metadata is not None
    assert youtube_metadata["url"] == valid_url
    assert "video_id" in youtube_metadata
    assert "video_title" in youtube_metadata

def test_invalid_url(validator, invalid_url):
    message_to_store, message_to_send, youtube_metadata = validator.process_message_with_link(invalid_url)

    assert message_to_store == invalid_url
    assert message_to_send == invalid_url
    assert youtube_metadata is None

def test_message_without_url(validator, no_url_message):
    message_to_store, message_to_send, youtube_metadata = validator.process_message_with_link(no_url_message)

    assert message_to_store == no_url_message
    assert message_to_send == no_url_message
    assert youtube_metadata is None

def test_url_without_transcript(validator, mocker):
    url = "https://www.youtube.com/watch?v=dummy-private-id"
    mocker.patch.object(validator.youtube_downloader, 'download_transcript', return_value=None)
    message_to_store, message_to_send, youtube_metadata = validator.process_message_with_link(url)

    assert url in message_to_store
    assert "transcrição" not in message_to_send.lower()
    assert youtube_metadata is None

def test_message_with_url(validator):
    message = "Hey, achei esse video top https://www.youtube.com/watch?v=Vjm8j0UCqVc! o que acha?"
    message_to_store, message_to_send, youtube_metadata = validator.process_message_with_link(message)

    expected_message_to_store = "Hey, achei esse video top ! o que acha? Fonte: https://www.youtube.com/watch?v=Vjm8j0UCqVc"
    assert message_to_store == expected_message_to_store
    assert youtube_metadata is not None
    assert "url" in youtube_metadata
    assert "video_id" in youtube_metadata

# Additional tests for edge cases and negative scenarios
def test_empty_message(validator):
    empty_message = ""
    message_to_store, message_to_send, youtube_metadata = validator.process_message_with_link(empty_message)

    assert message_to_store == empty_message
    assert message_to_send == empty_message
    assert youtube_metadata is None

# Run using: pytest .\test_user_input_validator.py -v