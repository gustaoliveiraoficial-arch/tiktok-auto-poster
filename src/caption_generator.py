import os
import subprocess
import tempfile
from pathlib import Path
from groq import Groq


def extract_audio(video_path: str, output_path: str) -> bool:
    """Extrai áudio do vídeo em WAV mono 16kHz para o Whisper."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def transcribe_video(video_path: str) -> str:
    """Transcreve o conteúdo do vídeo usando Groq Whisper (grátis)."""
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    try:
        print("Extraindo áudio do vídeo...")
        if not extract_audio(video_path, audio_path):
            print("Aviso: ffmpeg falhou, tentando sem conversão...")
            audio_path = video_path

        print("Transcrevendo com Whisper...")
        with open(audio_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(Path(audio_path).name, f.read()),
                model="whisper-large-v3",
                language="pt",
                response_format="text"
            )

        return str(transcription).strip()

    finally:
        try:
            if audio_path != video_path:
                os.unlink(audio_path)
        except Exception:
            pass


def generate_caption(transcript: str) -> str:
    """
    Usa Groq LLaMA para criar uma legenda viral de alta conversão
    com 5 hashtags relevantes. Curta, forte, sem textão.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    prompt = f"""Você é um especialista em TikTok viral no Brasil.

Com base nessa transcrição de vídeo, crie uma legenda para TikTok que:
- Seja CURTA (máximo 2 frases impactantes)
- Use linguagem direta e informal brasileira
- Gere curiosidade ou urgência para assistir o vídeo
- Seja de alta conversão (faz o usuário parar o scroll)
- Termine com exatamente 5 hashtags virais relacionadas ao conteúdo
- NÃO use aspas, NÃO use emojis em excesso (máximo 1-2)

TRANSCRIÇÃO:
{transcript[:3000]}

Retorne APENAS a legenda pronta, nada mais. Formato:
[frase impactante curta]
#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=200
    )

    return response.choices[0].message.content.strip()


def analyze_and_generate_caption(video_path: str) -> str:
    """Pipeline completo: analisa o vídeo e gera a legenda."""
    try:
        transcript = transcribe_video(video_path)
        if not transcript:
            print("Transcrição vazia, usando legenda padrão...")
            return _fallback_caption()

        print(f"Transcrição obtida ({len(transcript)} chars)")
        caption = generate_caption(transcript)
        print(f"Legenda gerada: {caption}")
        return caption

    except Exception as e:
        print(f"Erro ao gerar legenda: {e}")
        return _fallback_caption()


def _fallback_caption() -> str:
    """Legenda padrão caso a análise falhe."""
    return "Isso vai mudar tudo que você sabia sobre IA 👀\n#ia #inteligenciaartificial #tecnologia #viral #tiktok"
