"""Lunes Host auto login - CloakBrowser + capsolver Turnstile"""
import os, sys, time, requests

LOGIN_URL = "https://betadash.lunes.host/login"
SITEKEY = "0x4AAAAAAA6Rk8huct44_xr7"
CAPSOLVER_API = "https://api.capsolver.com"

def tg_send(text, token="", chat_id=""):
    token, chat_id = (token or "").strip(), (chat_id or "").strip()
    if not token or not chat_id: return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, timeout=15)
    except Exception as e: print(f"TG send failed: {e}")

def build_accounts():
    batch = (os.getenv("ACCOUNTS_BATCH") or "").strip()
    if not batch: raise RuntimeError("Missing ACCOUNTS_BATCH")
    accounts = []
    for raw in batch.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"): continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2:
            accounts.append({"email": parts[0], "password": parts[1],
                "tg_token": parts[2] if len(parts) > 2 else "",
                "tg_chat": parts[3] if len(parts) > 3 else ""})
    return accounts

def solve_turnstile(api_key, website_url, sitekey):
    """Use capsolver to solve Turnstile"""
    # Create task
    resp = requests.post(f"{CAPSOLVER_API}/createTask", json={
        "clientKey": api_key,
        "task": {
            "type": "AntiTurnstileTaskProxyLess",
            "websiteURL": website_url,
            "websiteKey": sitekey,
            "metadata": {"type": "turnstile"}
        }
    }, timeout=30)
    data = resp.json()
    print(f"createTask: {data}")
    if data.get("errorId", 1) != 0:
        print(f"capsolver error: {data.get('errorDescription', 'unknown')}")
        return None
    task_id = data["taskId"]

    # Poll for result
    for i in range(60):
        time.sleep(3)
        resp = requests.post(f"{CAPSOLVER_API}/getTaskResult", json={
            "clientKey": api_key,
            "taskId": task_id
        }, timeout=30)
        data = resp.json()
        if data.get("status") == "ready":
            token = data["solution"]["token"]
            print(f"Turnstile solved! ({(i+1)*3}s) token={token[:30]}...")
            return token
        elif data.get("errorId", 0) != 0:
            print(f"capsolver error: {data.get('errorDescription')}")
            return None
        if i % 5 == 0:
            print(f"  waiting... ({(i+1)*3}s)")
    print("capsolver timeout")
    return None

def login_one(api_key, email, password):
    from cloakbrowser import launch
    proxy = os.getenv("PROXY_URL", "")
    print(f"Proxy: {proxy}")
    kwargs = {"humanize": True, "headless": True}
    if proxy:
        kwargs["proxy"] = proxy
    browser = launch(**kwargs)
    try:
        page = browser.new_page()
        print(f"Opening login: {email}")
        page.goto(LOGIN_URL, timeout=60000)
        time.sleep(5)
        print(f"Page: {page.url}")

        page.wait_for_selector("#email", state="visible", timeout=30000)
        page.fill("#email", email)
        page.fill("#password", password)
        print("Credentials filled")

        # Solve Turnstile via capsolver
        print("Solving Turnstile via capsolver...")
        token = solve_turnstile(api_key, LOGIN_URL, SITEKEY)
        if not token:
            print("Failed to solve Turnstile")
            page.screenshot(path=f"ts-fail-{email.split('@')[0]}.png")
            return False

        # Inject the token into the hidden field
        page.evaluate(f'''
            document.querySelector('[name="cf-turnstile-response"]').value = "{token}";
        ''')
        print("Token injected")

        # Submit
        page.click('button[type="submit"]')
        print("Submitted")

        for i in range(20):
            time.sleep(2)
            if "/login" not in page.url:
                print(f"Redirected: {page.url}")
                break
        else:
            print(f"Still on: {page.url}")

        page.screenshot(path=f"after-{email.split('@')[0]}.png")

        if "/login" not in page.url:
            print("Login success!")
            for sid in ["51160", "60685"]:
                try:
                    page.goto(f"https://betadash.lunes.host/servers/{sid}", timeout=30000)
                    time.sleep(3)
                    print(f"  Visited server {sid}")
                except Exception as e: print(f"  Server {sid}: {e}")
            try: page.goto("https://betadash.lunes.host/logout", timeout=15000)
            except: pass
            return True
        else:
            # Check for error messages
            try:
                body = page.locator("body").text_content() or ""
                print(f"Page text: {body[:300]}")
            except: pass
            print("Login FAILED")
            return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()
        return False
    finally:
        browser.close()

def main():
    api_key = os.getenv("CAPSOLVER_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing CAPSOLVER_KEY")
    accounts = build_accounts()
    ok, fail = 0, 0
    results = []
    for i, acc in enumerate(accounts, 1):
        email = acc["email"]
        print(f"\n{"="*50}\n[{i}/{len(accounts)}] {email}\n{"="*50}")
        success = login_one(api_key, email, acc["password"])
        if success: ok += 1; results.append(f"OK {email}")
        else: fail += 1; results.append(f"FAIL {email}")
        tg_send(f"{'✅' if success else '❌'} Lunes {'登录成功' if success else '登录失败'}\n{email}",
            acc.get("tg_token",""), acc.get("tg_chat",""))
        if i < len(accounts): time.sleep(5)
    summary = f"Lunes 续期: {ok}/{len(accounts)} 成功\n" + "\n".join(results)
    print(f"\n{summary}")
    for acc in accounts:
        if acc.get("tg_token") and acc.get("tg_chat"):
            tg_send(summary, acc["tg_token"], acc["tg_chat"]); break
    if fail == len(accounts): sys.exit(1)

if __name__ == "__main__":
    main()
