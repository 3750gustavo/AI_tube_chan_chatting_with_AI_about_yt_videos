import re
from youtube_transcript_module import YouTubeTranscriptDownloader

class UserInputValidator:
    def __init__(self, youtube_downloader=None):
        # Inicializa o validador de entrada com um downloader de transcritos do YouTube
        self.youtube_downloader = youtube_downloader or YouTubeTranscriptDownloader()

    def process_message_with_link(self, message_text):
        """
        Verifica se a mensagem contém um link. Se sim, retorna uma tupla com:
        (mensagem_armazenada, mensagem_enviada, metadados_do_youtube)

        Os metadados serão None se nenhum link do YouTube foi encontrado.

        Args:
            message_text (str): Texto da mensagem do usuário

        Returns:
            Tuple(str, str, dict): Mensagem original (para armazenar), mensagem modificada (para enviar ao LLM)
                                e metadados do YouTube se aplicável
        """
        # Expressão regular para detectar URLs em qualquer formato
        url_pattern = r'\b(https?://[a-zA-Z0-9-._~:/?#[\]@!$&\'()*+,;%=]+|www\.[a-zA-Z0-9-._~:/?#[\]@!$&\'()*+,;%=]+)\b'
        match = re.search(url_pattern, message_text)  # Retorna None se não encontrar URL
        message_to_store = message_text
        message_to_send = message_text
        youtube_metadata = None

        if match:
            url = match.group(0).strip()  # Remove espaços em volta da URL
            # Verifica se a URL pertence ao YouTube e extrai o ID do vídeo
            video_id = self.youtube_downloader.get_video_id(url)  # Retorna None se inválida
            if video_id:
                # Obtém título e transcrição do vídeo
                video_title = self.youtube_downloader.get_video_title(video_id)
                transcript = self.youtube_downloader.download_transcript(video_id)
                if transcript:
                    # Separa a mensagem em partes antes e depois da URL
                    split_message = message_text.split(url)
                    before_link = split_message[0].strip()
                    after_link = split_message[1].strip() if len(split_message) > 1 else ""
                    message_without_link = f"{before_link} {after_link}".strip()

                    # Cria versão somente com link (para otimização de memória)
                    link_version = f"{message_without_link} Fonte: {url}"

                    # Cria versão com transcrição (contexto completo)
                    instructions = f"\n\nO usuário acabou de te enviar um link, segue abaixo a transcrição completa do vídeo com título: {video_title}, esta mesma pode conter erros de digitação ou falas misturadas caso o video possua mais de um narrador. Por favor, ignore quaisquer erros de digitação e foque na mensagem geral do conteúdo ao responder o usuário.\n\n{transcript}\n\n Agora, por favor, responda a mensagem do usuário considerando o conteúdo do vídeo acima, lembre-se de por personalidade e emoção em suas respostas!"
                    transcript_version = f"{message_without_link}{instructions}"

                    # Armazena as versões e metadados
                    message_to_store = link_version
                    message_to_send = transcript_version
                    youtube_metadata = {
                        "url": url,
                        "video_id": video_id,
                        "video_title": video_title,
                        "link_version": link_version,
                        "transcript_version": transcript_version
                    }

                    print(
                        f"Link do YouTube detectado!\n"
                        f"URL: {url}\n"
                        f"ID do vídeo: {video_id}\n"
                        f"Título: {video_title}\n"
                        f"Transcrição (primeiros 100 caracteres): {transcript[:100]}... (tamanho total: {len(transcript)} caracteres)\n"
                        f"Mensagem armazenada: {message_to_store}\n"
                        f"Mensagem enviada: {message_to_send[:100]}...\n"
                    )

        return message_to_store, message_to_send, youtube_metadata