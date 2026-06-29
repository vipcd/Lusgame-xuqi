



 Settings → Secrets and variables → Actions 中添加：

**`ACCOUNTS_BATCH`** — 每行一个账号，格式：

```
email,password
email,password,tg_bot_token,tg_chat_id
```

- 2列：只登录，不发 TG 通知
- 4列：登录后通过 TG Bot 推送结果

## 手动触发

Actions 页面点击 "Run workflow" 即可手动执行。

