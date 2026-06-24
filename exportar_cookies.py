"""
RODE ESSE SCRIPT UMA VEZ NO SEU PC para fazer login no TikTok e salvar os cookies.
Depois cole o conteúdo do arquivo gerado no GitHub Secret chamado TIKTOK_COOKIES.

Uso:
    pip install playwright
    playwright install chromium
    python exportar_cookies.py
"""

from src.tiktok_poster import save_cookies_from_browser

if __name__ == "__main__":
    save_cookies_from_browser("tiktok_cookies.json")
