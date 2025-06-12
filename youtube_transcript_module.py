from youtube_transcript_api import YouTubeTranscriptApi
from tenacity import retry, stop_after_attempt, wait_exponential
from youtube_transcript_api.formatters import TextFormatter
import requests
import re
import os
from typing import Optional, List, Tuple

class YouTubeTranscriptDownloader:
    """
    Uma classe para baixar e gerenciar legendas de vídeos do YouTube.

    Atributos:
        None
    """

    def get_video_id(self, youtube_url: str) -> Optional[str]:
        """
        Extrai o ID do vídeo de uma URL do YouTube, incluindo URLs encurtadas.

        Args:
            youtube_url (str): A URL do YouTube.

        Retorna:
            Optional[str]: O ID do vídeo extraído ou None se não encontrado.
        """
        # Resolve URL encurtada para sua forma original
        try:
            response = requests.head(youtube_url, allow_redirects=True)
            youtube_url = response.url
        except requests.RequestException as e:
            print(f"Erro ao resolver URL: {e}")
            return None

        # Expressão regular melhorada para capturar formatos comuns de URLs do YouTube, incluindo youtu.be e strings de consulta
        pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:.*?v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(pattern, youtube_url)
        return match.group(1) if match else None

    def get_video_title(self, video_id: str) -> str:
        """
        Obtém o título do vídeo do YouTube.

        Args:
            video_id (str): O ID do vídeo do YouTube.

        Retorna:
            str: O título do vídeo ou "Desconhecido" se não encontrado.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            matches = re.findall(r'<title>(.*?)</title>', response.text)
            return matches[0].replace(" - YouTube", "") if matches else "Desconhecido"
        except requests.RequestException as e:
            print(f"Erro ao buscar título do vídeo: {e}")
            return "Desconhecido"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def download_transcript(self, video_id: str) -> str:
        """
        Baixa a legenda e retorna como uma string.

        Args:
            video_id (str): O ID do vídeo do YouTube.

        Retorna:
            str: A legenda em texto ou uma string vazia se ocorrer um erro.
        """
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_generated_transcript(['en', 'pt'])

            if transcript is None:
                print(f"Aviso: Nenhuma legenda encontrada para o vídeo {video_id} nos idiomas ['en', 'pt'].")
                return ""

            formatter = TextFormatter()
            transcript_text = formatter.format_transcript(transcript.fetch())

            # Remove horários e nomes de falantes
            transcript_text = re.sub(r'\[\d+:\d+:\d+\]', '', transcript_text)
            transcript_text = re.sub(r'<\w+>', '', transcript_text)
            return transcript_text
        except Exception as e:
            print(f"Erro inesperado ao baixar legenda para {video_id}: {e}")
            return ""

    def save_transcript(self, video_id: str, transcript_text: str) -> Optional[str]:
        """
        Salva a legenda em um arquivo.

        Args:
            video_id (str): O ID do vídeo do YouTube.
            transcript_text (str): O texto da legenda para salvar.

        Retorna:
            Optional[str]: O nome do arquivo se bem-sucedido, None caso contrário.
        """
        if not transcript_text:
            print("Nenhum conteúdo de legenda para salvar.")
            return None

        video_title = self.get_video_title(video_id)
        file_name = f"{video_title}.txt"
        file_name = re.sub(r'[\\/*?:"<>|]', '', file_name)  # Remove caracteres inválidos

        try:
            with open(file_name, 'w', encoding='utf-8') as file:
                file.write(transcript_text)
            print(f'Legenda salva em: "{file_name}"')
            return file_name
        except Exception as e:
            print(f"Erro ao salvar legenda: {e}")
            return None

if __name__ == "__main__":
    """
    Exemplo de uso da classe YouTubeTranscriptDownloader.
    """
    downloader = YouTubeTranscriptDownloader()

    # Exemplo de uso
    youtube_url = input("Insira o link do vídeo do YouTube: ")
    video_id = downloader.get_video_id(youtube_url)

    if video_id:
        transcript_text = downloader.download_transcript(video_id)
        if transcript_text:
            downloader.save_transcript(video_id, transcript_text)
        else:
            print("Não foi possível baixar a legenda.")
    else:
        print("URL do YouTube inválida.")