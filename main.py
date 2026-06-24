"""
TikTok Auto Poster
==================
Pega o primeiro vídeo da pasta queue/, analisa o conteúdo com IA,
gera uma legenda viral, posta no TikTok e move para posted/.

Rode via GitHub Actions nos horários agendados.
"""

import os
import sys
import shutil
from pathlib import Path
from src.tiktok_poster import post_to_tiktok
from src.caption_generator import analyze_and_generate_caption

QUEUE_DIR = Path("queue")
POSTED_DIR = Path("posted")
SUPPORTED_FORMATS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def get_next_video() -> Path | None:
    """Retorna o próximo vídeo da fila (ordem alfabética)."""
    videos = sorted([
        f for f in QUEUE_DIR.iterdir()
        if f.suffix.lower() in SUPPORTED_FORMATS
    ])
    return videos[0] if videos else None


def main():
    print("=" * 50)
    print("TikTok Auto Poster — iniciando")
    print("=" * 50)

    # Verifica se há vídeos na fila
    video = get_next_video()
    if video is None:
        print("Fila vazia — nenhum vídeo para postar agora.")
        sys.exit(0)

    print(f"Próximo vídeo: {video.name}")

    # Verifica secrets
    cookies_json = os.environ.get("TIKTOK_COOKIES", "")
    if not cookies_json:
        print("ERRO: Secret TIKTOK_COOKIES não configurado.")
        sys.exit(1)

    if not os.environ.get("GROQ_API_KEY"):
        print("ERRO: Secret GROQ_API_KEY não configurado.")
        sys.exit(1)

    # Analisa o vídeo e gera legenda com IA
    print("Analisando vídeo e gerando legenda...")
    caption = analyze_and_generate_caption(str(video.resolve()))
    print(f"\nLegenda final:\n{caption}\n")

    # Posta no TikTok
    print("Postando no TikTok...")
    success = post_to_tiktok(
        video_path=str(video.resolve()),
        caption=caption,
        cookies_json=cookies_json
    )

    if success:
        dest = POSTED_DIR / video.name
        shutil.move(str(video), str(dest))
        print(f"Movido para posted/: {video.name}")
        print("Postagem concluída com sucesso!")
    else:
        print("FALHA ao postar. O vídeo permanece na fila.")
        sys.exit(1)


if __name__ == "__main__":
    main()
