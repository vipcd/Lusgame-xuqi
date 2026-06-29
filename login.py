"""
Lunes Host 自动登录续期脚本 - 火狐内核 + CF Token 哨兵版
"""
import os
import sys
import time
import re
import requests
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"

def tg_send(text, token="", chat_id=""):
    token, chat_id = (token or "").strip(), (chat_id or "").strip()
    if not token or not chat_id or token.lower() == "none" or chat_id.lower() == "none": 
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, 
            timeout=15
        )
    except Exception as e: 
        print(f"TG 发送失败: {e}")

def keepalive(email, password):
    results = []
    success = False
    
    with sync_playwright() as p:
        print("  正在通过 Hysteria2 节点建立安全浏览器隧道...")
        try:
            # 🌟 升级：改用极难别被 CF 识破特征的 Firefox 引擎启动
            browser = p.firefox.launch(
                headless=False,
                proxy={"server": "http://127.0.0.1:1081"} 
            )
        except Exception as b_err:
            print(f"  ❌ 浏览器启动失败: {b_err}")
            return False, [f"browser launch failed: {b_err}"]

        context = browser.new_context(
            user_agent=UA,
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            print("  正在打开 Lunes 登录页面...")
            page.goto("https://betadash.lunes.host/login", timeout=45000)
            page.wait_for_timeout(4000)
            
            p_len = len(password)
            p_preview = password[0] + "*" * (p_len - 2) + password[-1] if p_len > 2 else "**"
            print(f"  🔍 [安全诊断] 读取到的账号: {email}")
            print(f"  🔍 [安全诊断] 读取到的密码长度: {p_len} 位 | 密文预览: {p_preview}")
            
            email_input = page.locator("input[type='email']").first
            pass_input = page.locator("input[type='password']").first
            
            print("  正在模拟输入账号和密码...")
            email_input.focus()
            email_input.press_sequentially(email, delay=100)
            page.wait_for_timeout(500)
            
            pass_input.focus()
            pass_input.press_sequentially(password, delay=100)
            page.wait_for_timeout(1000)
            
            # 🌟🌟 核心突破：拦截抢跑！死循环监控 Cloudflare 验证状态
            print("  ⏳ [哨兵防御] 正在监控 Cloudflare Turnstile 验证生成状态...")
            token_passed = False
            for i in range(20):  # 最多耐心等待 20 秒
                token = page.evaluate("() => { const el = document.querySelector('[name=\"cf-turnstile-response\"]') || document.querySelector('[name=\"g-recaptcha-response\"]'); return el ? el.value : ''; }")
                if token and len(token) > 15:
                    print(f"  ✅ [大获全胜] Cloudflare 成功放行！检测到有效安全加密 Token (长度: {len(token)})")
                    token_passed = True
                    break
                
                # 针对极其少见的硬风控 Managed 挑战（需要手动点复选框），做一次自动化模拟框架击活
                if i == 5:
                    print("  👉 检测到环境解析较慢，尝试对潜在的 Cloudflare 交互框执行模拟激活...")
                    try:
                        for frame in page.frames:
                            if "challenges.cloudflare.com" in frame.url:
                                frame.click("body", timeout=1500)
                    except:
                        pass
                        
                page.wait_for_timeout(1000)

            if not token_passed:
                print("  ⚠️ 警告：等了 20 秒网站仍未下发验证 Token，可能当前代理节点纯净度较低。尝试强行提交...")

            submit_btn = page.locator("button[type='submit']").first
            print("  正在点击登录按钮...")
            submit_btn.click()
            
            print("  等待页面跳转中...")
            page.wait_for_timeout(10000)
            
            content = page.content()
            current_url = page.url
            
            if "profile-header" in content or "servers online" in content or "servers" in current_url:
                print("  🎉 🎉 🎉 成功突破防护，登录进入控制台！")
                results.append("dashboard OK")
                
                server_ids = ["51160", "60685"] 
                links = page.locator("a[href*='/servers/']").all()
                discovered_ids = []
                for link in links:
                    href = link.get_attribute("href") or ""
                    match = re.search(r'/servers/(\d+)', href)
                    if match:
                        discovered_ids.append(match.group(1))
                
                if discovered_ids:
                    server_ids = list(set(discovered_ids))
                    print(f"  🧭 自动检测到你名下的服务器 ID: {server_ids}")
                
                for sid in server_ids:
                    print(f"  正在进入服务器 {sid} 的详情页...")
                    page.goto(f"https://betadash.lunes.host/servers/{sid}", timeout=30000)
                    page.wait_for_timeout(4000)
                    
                    srv_content = page.content()
                    if "Server" in srv_content or "Status" in srv_content:
                        renew_btn = page.locator("button:has-text('Renew'), button:has-text('续期'), a:has-text('Renew')").first
                        if renew_btn.is_visible():
                            print(f"  👉 发现该服务器存在【续期】按钮，正在执行自动点击...")
                            renew_btn.click()
                            page.wait_for_timeout(2000)
                            results.append(f"server {sid} Renew Clicked")
                        else:
                            results.append(f"server {sid} Visited")
                        print(f"  ✅ 服务器 {sid} 页面访问/续期成功")
                    else:
                        results.append(f"server {sid} status unknown")
                        print(f"  ❌ 服务器 {sid} 页面加载异常")
                
                success = True
            else:
                print(f"  ❌ 依然未能通过验证。")
                print(f"  🔍 最终停留在 URL: {current_url}")
                try:
                    page.screenshot(path="login_failed.png", full_page=True)
                except:
                    pass
                results.append("login failed")
                success = False
                
        except Exception as e:
            print(f"  💥 脚本运行异常: {e}")
            results.append(f"error: {e}")
            success = False
        finally:
            browser.close()
            
    return success, results

def main():
    email = (os.getenv("LUNES_EMAIL") or "").strip()
    password = (os.getenv("LUNES_PASSWORD") or "").strip()
    tg_token = (os.getenv("TG_TOKEN") or "").strip()
    tg_chat = (os.getenv("TG_CHAT_ID") or "").strip()

    if not email or not password:
        print("❌ 错误：缺少关键环境变量。")
        sys.exit(1)

    print(f"\n{'='*50}\n正在为账号 {email} 执行保活 (火狐防抢跑模式)\n{'='*50}")
    success, detail = keepalive(email, password)
    
    status_str = "OK" if success else "FAIL"
    report = f"{'✅' if success else '❌'} Lunes 自动续期报告\n账号: {email}\n状态: {', '.join(detail)}"
    
    tg_send(report, tg_token, tg_chat)
    print(f"\n📊 Lunes 续期总览:\n{status_str} {email}: {', '.join(detail)}")
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
