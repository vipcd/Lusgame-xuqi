# Lunes AutoLogin

每 14 天自动登录 [Lunes Host](https://betadash.lunes.host/) 保持免费实例不被 suspend。

## 原理

使用 SeleniumBase (UC Mode) 自动化浏览器登录 Lunes BetaDash 面板，绕过 Cloudflare Turnstile 验证，完成登录 → 进入服务器页 → 返回首页 → 退出。

## 配置

在仓库 Settings → Secrets and variables → Actions 中添加：

**`ACCOUNTS_BATCH`** — 每行一个账号，格式：

```
email,password
email,password,tg_bot_token,tg_chat_id
```

- 2列：只登录，不发 TG 通知
- 4列：登录后通过 TG Bot 推送结果

## 手动触发

Actions 页面点击 "Run workflow" 即可手动执行。

## 致谢

参考 [yeye296/auto_login_lunes](https://github.com/yeye296/auto_login_lunes)
