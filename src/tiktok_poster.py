import os
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


def load_cookies(cookies_json: str) -> list:
    try:
        return json.loads(cookies_json)
    except Exception:
        return []


def post_to_tiktok(video_path: str, caption: str, cookies_json: str) -> bool:
    """
    Faz upload de um vídeo no TikTok com a legenda fornecida.
    Retorna True se postado com sucesso.
    """
    cookies = load_cookies(cookies_json)
    if not cookies:
        print("ERRO: Nenhum cookie do TikTok encontrado.")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        # Carrega cookies de sessão
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            print("Acessando TikTok Studio...")
            page.goto("https://www.tiktok.com/tiktokstudio/upload", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)

            # Verifica se está logado
            if "login" in page.url.lower():
                print("ERRO: Sessão expirada. Renove os cookies do TikTok.")
                browser.close()
                return False

            print("Fazendo upload do vídeo...")
            # Aguarda o input de arquivo aparecer
            file_input = page.locator("input[type='file']").first
            file_input.set_input_files(video_path)

            # Aguarda o vídeo carregar (barra de progresso some)
            print("Aguardando processamento do vídeo...")
            page.wait_for_selector(
                "div[class*='upload-progress']",
                state="hidden",
                timeout=120000
            )
            time.sleep(3)

            # Preenche a legenda
            print("Preenchendo legenda...")
            caption_box = page.locator(
                "div[contenteditable='true']"
            ).first
            caption_box.click()
            # Limpa conteúdo existente e digita a legenda
            caption_box.press("Control+a")
            caption_box.type(caption, delay=30)

            time.sleep(2)

            # Clica em Postar
            print("Postando...")
            post_btn = page.locator(
                "button:has-text('Postar'), button:has-text('Post')"
            ).first
            post_btn.click()

            # Aguarda confirmação
            page.wait_for_selector(
                "div[class*='success'], div[class*='modal-success']",
                timeout=30000
            )

            print("Vídeo postado com sucesso!")
            browser.close()
            return True

        except PlaywrightTimeout as e:
            print(f"Timeout durante o post: {e}")
            # Tira screenshot para debug
            try:
                page.screenshot(path="debug_screenshot.png")
                print("Screenshot salvo em debug_screenshot.png")
            except Exception:
                pass
            browser.close()
            return False
        except Exception as e:
            print(f"Erro ao postar: {e}")
            try:
                page.screenshot(path="debug_screenshot.png")
            except Exception:
                pass
            browser.close()
            return False


def save_cookies_from_browser(output_path: str = "tiktok_cookies.json"):
    """
    Abre um browser para você fazer login manual no TikTok
    e salva os cookies automaticamente. Rode isso localmente uma vez.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",  # Usa Chrome instalado (interface visual)
            args=["--start-maximized"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        page.goto("https://www.tiktok.com/login")
        print("\n" + "="*50)
        print("FAÇA LOGIN NO TIKTOK NO BROWSER QUE ABRIU")
        print("Após logar, aguarde... os cookies serão salvos automaticamente.")
        print("Você tem 5 minutos.")
        print("="*50 + "\n")

        # Aguarda o usuário logar (URL muda do /login) — 5 minutos
        try:
            page.wait_for_url(
                lambda url: "login" not in url and "tiktok.com" in url,
                timeout=300000
            )
        except PlaywrightTimeout:
            print("Tempo esgotado. Tente novamente.")
            browser.close()
            return

        time.sleep(3)
        cookies = context.cookies()

        with open(output_path, "w") as f:
            json.dump(cookies, f, indent=2)

        print(f"\nCookies salvos em: {output_path}")
        print("Cole o conteúdo desse arquivo no GitHub Secret 'TIKTOK_COOKIES'")
        browser.close()
