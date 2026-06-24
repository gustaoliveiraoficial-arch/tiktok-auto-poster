"""
TikTok Auto Poster
==================
Pega o primeiro vídeo da pasta queue/, posta no TikTok e move para posted/.
O nome do arquivo (sem extensão) é usado como legenda.

Rode via GitHub Actions nos horários agendados.
"""

import os
import sys
import shutil
from pathlib import Path
from src.tiktok_poster import post_to_tiktok

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


def get_caption_from_filename(video_path: Path) -> str:
    """Usa o nome do arquivo como legenda (sem a extensão)."""
    return video_path.stem


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

    # Legenda = nome do arquivo
    caption = get_caption_from_filename(video)
    print(f"Legenda: {caption}")

    # Cookies do TikTok (vem do GitHub Secret)
    cookies_json = os.environ.get("TIKTOK_COOKIES", "")
    if not cookies_json:
        print("ERRO: Secret TIKTOK_COOKIES não configurado.")
        sys.exit(1)

    # Posta no TikTok
    success = post_to_tiktok(
        video_path=str(video.resolve()),
        caption=caption,
        cookies_json=cookies_json
    )

    if success:
        # Move para posted/
        dest = POSTED_DIR / video.name
        shutil.move(str(video), str(dest))
        print(f"Movido para posted/: {video.name}")
        print("Postagem concluída com sucesso!")
    else:
        print("FALHA ao postar. O vídeo permanece na fila.")
        sys.exit(1)


if __name__ == "__main__":
    main()
