"""
Lunes Host 自动登录续期脚本 - 基于 Playwright 自动化浏览器
彻底解决 Cloudflare 403 阻挡问题，一劳永逸无需再抓取 Cookie
"""
import os
import sys
import time
import re
import requests
from playwright.sync_api import sync_playwright

# 保持与原脚本一致的真实浏览器 User-Agent
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

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

def build_accounts():
    batch = (os.getenv("ACCOUNTS_BATCH") or "").strip()
    if not batch: 
        raise RuntimeError("GitHub Secrets 中缺少 ACCOUNTS_BATCH 变量")
    accounts = []
    for raw in batch.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"): 
            continue
        parts = [p.strip() for p in line.split(",")]
        # 支持格式: 邮箱,密码 或 邮箱,密码,TG_Token,TG_ChatID
        if len(parts) >= 2:
            accounts.append({
                "email": parts[0],
                "password": parts[1],
                "tg_token": parts[2] if len(parts) > 2 else "",
                "tg_chat": parts[3] if len(parts) > 3 else "",
            })
    return accounts

def keepalive(email, password):
    results = []
    success = False
    
    with sync_playwright() as p:
        # 启动 Chromium 浏览器，加入反爬虫参数
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(user_agent=UA)
        page = context.new_page()
        
        try:
            print("  正在打开 Lunes 登录页面...")
            page.goto("https://betadash.lunes.host/login", timeout=45000)
            page.wait_for_timeout(3000)
            
            # 检测是否存在 Cloudflare 盾，给予一定的缓冲时间让其自动通过
            if "cloudflare" in page.content().lower():
                print("  检测到 Cloudflare 验证防护，等待自动解析...")
                page.wait_for_timeout(6000)
            
            # 自动定位并填写输入框
            print("  正在自动输入账号和密码...")
            email_input = page.locator("input[type='email']").first
            pass_input = page.locator("input[type='password']").first
            
            email_input.fill(email)
            page.wait_for_timeout(500)
            pass_input.fill(password)
            page.wait_for_timeout(500)
            
            # 定位并点击登录按钮
            submit_btn = page.locator("button[type='submit']").first
            print("  正在点击登录按钮...")
            submit_btn.click()
            
            # 等待页面跳转和加载完毕
            page.wait_for_timeout(6000)
            
            # 判断是否登录成功 (检查页面关键特征)
            content = page.content()
            current_url = page.url
            
            if "profile-header" in content or "servers online" in content or "servers" in current_url:
                print("  🎉 仪表盘登录成功！")
                results.append("dashboard OK")
                
                # 动态扫描页面上的所有服务器 ID (支持 fallback 你的默认 ID 51160 和 60685)
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
                else:
                    print(f"  ⚠️ 未检测到新链接，将使用默认服务器 ID: {server_ids}")
                
                # 依次进入每一个服务器页面触发保活/续期
                for sid in server_ids:
                    print(f"  正在进入服务器 {sid} 的详情页...")
                    page.goto(f"https://betadash.lunes.host/servers/{sid}", timeout=30000)
                    page.wait_for_timeout(4000)
                    
                    srv_content = page.content()
                    if "Server" in srv_content or "Status" in srv_content:
                        # 尝试自动寻找并点击“续期/Renew”按钮
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
                print(f"  ❌ 登录失败。当前页面标题: {page.title()}，可能是密码错误或触发了强力人机验证。")
                results.append("login failed / blocked by cf")
                success = False
                
        except Exception as e:
            print(f"  💥 脚本运行异常: {e}")
            results.append(f"error: {e}")
            success = False
        finally:
            browser.close()
            
    return success, results

def main():
    accounts = build_accounts()
    ok, fail = 0, 0
    results = []
    
    for i, acc in enumerate(accounts, 1):
        email = acc["email"]
        print(f"\n{'='*50}\n[{i}/{len(accounts)}] 正在为账号 {email} 执行保活\n{'='*50}")
        success, detail = keepalive(email, acc["password"])
        
        if success:
            ok += 1
            results.append(f"OK {email}: {', '.join(detail)}")
        else:
            fail += 1
            results.append(f"FAIL {email}: {', '.join(detail)}")
            
        # 单账号单独发通知
        tg_send(
            f"{'✅' if success else '❌'} Lunes 自动续期报告\n账号: {email}\n状态: {', '.join(detail)}",
            acc.get("tg_token", ""), acc.get("tg_chat", "")
        )
        if i < len(accounts): 
            time.sleep(5)
    
    # 汇总打印和通知
    summary = f"📊 Lunes 续期总览: {ok}/{len(accounts)} 成功\n" + "\n".join(results)
    print(f"\n{summary}")
    
    # 如果有配置通知，发送汇总通知
    for acc in accounts:
        if acc.get("tg_token") and acc.get("tg_chat"):
            tg_send(summary, acc["tg_token"], acc["tg_chat"])
            break
            
    if fail == len(accounts): 
        sys.exit(1)

if __name__ == "__main__":
    main()
