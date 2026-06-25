import os
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# Script stealth avançado — evita detecção de automação
STEALTH_SCRIPT = """
// Remove webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Plugins reais
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
        ];
        plugins.item = (i) => plugins[i];
        plugins.namedItem = (name) => plugins.find(p => p.name === name);
        plugins.refresh = () => {};
        Object.defineProperty(plugins, 'length', { value: plugins.length });
        return plugins;
    }
});

// Linguagens
Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });

// Chrome runtime
window.chrome = {
    runtime: {
        connect: () => {},
        sendMessage: () => {},
        onMessage: { addListener: () => {}, removeListener: () => {} },
        id: 'random-extension-id',
    },
    loadTimes: () => ({}),
    csi: () => ({}),
    app: {},
};

// Permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);

// Hardware concurrency realista
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

// Platform
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });

// WebGL vendor
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
};

// Screen
Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
"""


def load_cookies(cookies_json: str) -> list:
    try:
        return json.loads(cookies_json)
    except Exception:
        return []


def _is_logged_in(page) -> bool:
    """Verifica se o TikTok reconheceu a sessão (por conteúdo da página)."""
    try:
        # Detecta página/modal de login por texto visível
        page_text = page.inner_text("body")
        login_indicators = [
            "Entrar no TikTok",
            "Log in to TikTok",
            "Usar código QR",
            "Use QR code",
            "Continuar com Facebook",
            "Continue with Facebook",
        ]
        for indicator in login_indicators:
            if indicator in page_text:
                print(f"Detectado indicador de login: '{indicator}'")
                return False

        # Se o input de upload ou área de drop existir, está logado
        upload_area = page.locator(
            "input[type='file'], "
            "div[class*='upload-drag'], "
            "div[class*='upload-wrapper'], "
            "div[data-e2e='upload-container']"
        )
        if upload_area.count() > 0:
            return True

        # Ambíguo — assume logado se não encontrou sinais de login
        return True

    except Exception as e:
        print(f"Erro ao verificar login: {e}")
        return False


def _dismiss_popups(page) -> None:
    """Dispensa overlays de tutorial/joyride e popups que bloqueiam cliques."""
    try:
        # Tenta clicar em botões de dispensa comuns
        dismiss_texts = ["Entendi", "Got it", "OK", "Skip", "Pular", "Close", "×", "✕"]
        for text in dismiss_texts:
            btn = page.locator(f"button:has-text('{text}')").first
            if btn.count() > 0:
                try:
                    btn.click(timeout=3000)
                    print(f"Popup dispensado via botão '{text}'")
                    time.sleep(1)
                    return
                except Exception:
                    continue

        # Se overlay de joyride ainda existir, remove via JS
        overlay_count = page.locator("div.react-joyride__overlay, div[data-test-id='overlay']").count()
        if overlay_count > 0:
            page.evaluate("""
                const overlays = document.querySelectorAll('.react-joyride__overlay, [data-test-id="overlay"], #react-joyride-portal');
                overlays.forEach(el => el.remove());
            """)
            print("Overlay de joyride removido via JS")
            time.sleep(0.5)
    except Exception as e:
        print(f"Aviso ao dispensar popup: {e}")


def post_to_tiktok(video_path: str, caption: str, cookies_json: str) -> bool:
    """
    Faz upload de um vídeo no TikTok com a legenda fornecida.
    Retorna True se postado com sucesso.
    """
    cookies = load_cookies(cookies_json)
    if not cookies:
        print("ERRO: Nenhum cookie do TikTok encontrado.")
        return False

    # Verifica sessionid
    session = [c for c in cookies if c["name"] in ("sessionid", "sessionid_ss", "sid_tt")]
    if not session:
        print("ERRO: sessionid não encontrado nos cookies.")
        return False

    print(f"Cookie de sessão encontrado: {session[0]['name']}")

    with sync_playwright() as p:
        # headless=False + DISPLAY=:99 (xvfb) evita detecção de browser headless pelo TikTok
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1280,900",
                "--disable-extensions",
                "--no-first-run",
                "--disable-infobars",
                "--hide-scrollbars",
                "--mute-audio",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1",
            },
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
        )

        # Aplica script stealth antes de qualquer página carregar
        context.add_init_script(STEALTH_SCRIPT)

        # Carrega cookies de sessão
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            # Passo 1: Carrega página principal para ativar cookies
            print("Carregando TikTok principal...")
            page.goto("https://www.tiktok.com", timeout=45000, wait_until="domcontentloaded")
            time.sleep(3)
            print(f"URL atual: {page.url}")

            # Passo 2: Tenta TikTok Studio upload
            print("Acessando TikTok Studio Upload...")
            page.goto("https://www.tiktok.com/tiktokstudio/upload", timeout=45000, wait_until="domcontentloaded")
            time.sleep(4)
            print(f"URL Studio: {page.url}")

            # Verifica login por URL
            if "login" in page.url.lower():
                print("ERRO: Redirecionado para login. Sessão expirada.")
                page.screenshot(path="debug_screenshot.png")
                browser.close()
                return False

            # Verifica login por conteúdo
            time.sleep(2)
            if not _is_logged_in(page):
                print("AVISO: TikTok Studio detectou bot. Tentando URL alternativa...")
                page.screenshot(path="debug_screenshot_studio.png")

                # Tenta URL alternativa
                page.goto("https://www.tiktok.com/upload", timeout=45000, wait_until="domcontentloaded")
                time.sleep(4)
                print(f"URL alternativa: {page.url}")

                time.sleep(3)
                if "login" in page.url.lower() or not _is_logged_in(page):
                    print("ERRO: Ambas as URLs mostraram tela de login. Renove os cookies.")
                    page.screenshot(path="debug_screenshot.png")
                    browser.close()
                    return False

            print("Sessão válida! Prosseguindo com upload...")

            # Aguarda o input de arquivo estar no DOM (pode ser hidden por CSS — normal no TikTok Studio)
            print("Aguardando input de arquivo...")
            page.wait_for_selector("input[type='file']", state="attached", timeout=30000)
            file_input = page.locator("input[type='file'][accept*='video']").first
            file_input.set_input_files(video_path)
            print(f"Arquivo enviado: {video_path}")

            # Aguarda processamento do vídeo (barra de progresso aparecer e sumir)
            print("Aguardando processamento do vídeo...")
            try:
                page.wait_for_selector(
                    "div[class*='upload-progress'], div[class*='progress-bar']",
                    timeout=15000
                )
                page.wait_for_selector(
                    "div[class*='upload-progress'], div[class*='progress-bar']",
                    state="hidden",
                    timeout=180000
                )
            except PlaywrightTimeout:
                # Alguns layouts não mostram barra — aguarda tempo fixo
                print("Barra de progresso não detectada, aguardando 30s...")
                time.sleep(30)

            time.sleep(3)

            # Dispensa qualquer popup/overlay antes de interagir
            _dismiss_popups(page)

            # Preenche a legenda
            print("Preenchendo legenda...")
            caption_box = page.locator("div[contenteditable='true']").first

            # Aguarda a caixa de legenda ficar disponível
            caption_box.wait_for(timeout=20000)
            caption_box.click()
            time.sleep(1)

            # Limpa conteúdo existente
            caption_box.press("Control+a")
            time.sleep(0.5)
            caption_box.press("Delete")
            time.sleep(0.5)

            # Digita a legenda com velocidade humana
            caption_box.type(caption, delay=25)
            time.sleep(2)

            # Dispensa popups novamente antes de clicar em Postar
            _dismiss_popups(page)

            # Clica em Postar
            print("Clicando em Postar...")
            post_btn = page.locator(
                "button:has-text('Postar'), button:has-text('Post'), "
                "button[data-e2e='post-btn']"
            ).first

            post_btn.wait_for(timeout=15000)
            post_btn.click()

            # Aguarda confirmação de sucesso
            print("Aguardando confirmação...")
            page.wait_for_selector(
                "div[class*='success'], div[class*='modal-success'], "
                "div[data-e2e='post-success'], span:has-text('publicado'), "
                "span:has-text('posted successfully')",
                timeout=45000
            )

            print("Vídeo postado com sucesso!")
            browser.close()
            return True

        except PlaywrightTimeout as e:
            print(f"Timeout durante o post: {e}")
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
            channel="chrome",
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

        try:
            page.wait_for_url(
                lambda url: "login" not in url and "tiktok.com" in url,
                timeout=300000
            )
        except PlaywrightTimeout:
            print("Tempo esgotado. Tente novamente.")
            browser.close()
            return

        print("Login detectado. Aguardando cookies de sessão...")
        for _ in range(30):
            cookies = context.cookies()
            session_cookies = [c for c in cookies if c["name"] in (
                "sessionid", "sessionid_ss", "sid_tt", "sid_guard"
            )]
            if session_cookies:
                print(f"Cookie de sessão encontrado: {session_cookies[0]['name']}")
                break
            time.sleep(1)
        else:
            print("Aviso: sessionid não encontrado, salvando cookies disponíveis mesmo assim...")
            cookies = context.cookies()

        time.sleep(2)

        with open(output_path, "w") as f:
            json.dump(cookies, f, indent=2)

        print(f"\nCookies salvos em: {output_path}")
        print("Cole o conteúdo desse arquivo no GitHub Secret 'TIKTOK_COOKIES'")
        browser.close()
