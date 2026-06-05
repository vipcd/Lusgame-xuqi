"""Lunes Host 自动登录 - Playwright + inline stealth JS"""
import os, sys, time, requests

LOGIN_URL = "https://betadash.lunes.host/login"

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
window.chrome = {runtime: {}};
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) =>
    params.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : origQuery(params);
"""

def tg_send(text, token="", chat_id=""):
    token, chat_id = (token or "").strip(), (chat_id or "").strip()
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=15,
        )
    except Exception as e:
        print(f"TG send failed: {e}")

def build_accounts():
    batch = (os.getenv("ACCOUNTS_BATCH") or "").strip()
    if not batch:
        raise RuntimeError("Missing ACCOUNTS_BATCH")
    accounts = []
    for raw in batch.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            accounts.append({
                "email": parts[0], "password": parts[1],
                "tg_token": parts[2] if len(parts) > 2 else "",
                "tg_chat": parts[3] if len(parts) > 3 else "",
            })
    return accounts

def login_one(email, password):
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.114 Safari/537.36",
            locale="en-US",
        )
        context.add_init_script(STEALTH_JS)
        page = context.new_page()
        
        try:
            print(f"Opening login: {email}")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            
            page.wait_for_selector("#email", state="visible", timeout=25000)
            page.fill("#email", email)
            page.fill("#password", password)
            
            # Wait for Turnstile
            print("Waiting for Turnstile...")
            for i in range(25):
                time.sleep(2)
                val = page.evaluate('document.querySelector("[name=cf-turnstile-response]")?.value || ""')
                if val:
                    print(f"Turnstile solved! ({i*2}s)")
                    break
            else:
                print("Turnstile timeout")
            
            page.click('button[type="submit"]')
            time.sleep(8)
            
            url = page.url
            print(f"URL: {url}")
            
            if "/login" not in url:
                print("Login success!")
                for sid in ["51160", "60685"]:
                    try:
                        page.goto(f"https://betadash.lunes.host/servers/{sid}", timeout=30000)
                        time.sleep(3)
                        print(f"  Visited server {sid}")
                    except Exception as e:
                        print(f"  Server {sid}: {e}")
                try:
                    page.goto("https://betadash.lunes.host/logout", timeout=15000)
                except:
                    pass
                return True
            else:
                try:
                    flash = page.locator(".flash-message").text_content()
                    print(f"Error: {flash}")
                except:
                    pass
                page.screenshot(path=f"fail-{int(time.time())}.png")
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False
        finally:
            context.close()
            browser.close()

def main():
    accounts = build_accounts()
    ok, fail = 0, 0
    results = []
    for i, acc in enumerate(accounts, 1):
        email = acc["email"]
        print(f"\n{'='*50}\n[{i}/{len(accounts)}] {email}\n{'='*50}")
        success = login_one(email, acc["password"])
        if success:
            ok += 1
            results.append(f"OK {email}")
        else:
            fail += 1
            results.append(f"FAIL {email}")
        tg_send(f"{'✅' if success else '❌'} Lunes {'登录成功' if success else '登录失败'}\n{email}", acc.get("tg_token",""), acc.get("tg_chat",""))
        if i < len(accounts):
            time.sleep(5)
    summary = f"Lunes 续期: {ok}/{len(accounts)} 成功\n" + "\n".join(results)
    print(f"\n{summary}")
    for acc in accounts:
        if acc.get("tg_token") and acc.get("tg_chat"):
            tg_send(summary, acc["tg_token"], acc["tg_chat"])
            break
    if fail == len(accounts):
        sys.exit(1)

if __name__ == "__main__":
    main()
