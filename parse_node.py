import os
import urllib.parse

def main():
    uri = os.getenv('HY2_NODE', '').strip()
    if not uri:
        print("❌ 错误：GitHub Secrets 中没有找到 HY2_NODE 变量，请先前往仓库设置中添加！")
        exit(1)

    if uri.startswith('hy2://'):
        uri = uri.replace('hy2://', 'hysteria2://', 1)

    try:
        parsed = urllib.parse.urlparse(uri)
        server = parsed.netloc.split('@')[-1]
        auth = parsed.netloc.split('@')[0] if '@' in parsed.netloc else ''
        auth = urllib.parse.unquote(auth)
        
        queries = urllib.parse.parse_qs(parsed.query)
        sni = queries.get('sni', [''])[0]
        insecure = queries.get('insecure', ['0'])[0] in ['1', 'true', 'True'] or queries.get('allowInsecure', ['0'])[0] in ['1', 'true', 'True']
        pin = queries.get('pinSHA256', [''])[0]
        
        config = f"server: {server}\n"
        if auth:
            config += f"auth: {auth}\n"
        config += f"tls:\n  sni: {sni if sni else 'www.bing.com'}\n  insecure: {'true' if insecure else 'false'}\n"
        if pin:
            config += f"  pinSHA256: {pin}\n"
        config += "http:\n  listen: 127.0.0.1:1081\nsocks5:\n  listen: 127.0.0.1:1080\n"
        
        with open('hy2_config.yaml', 'w') as f:
            f.write(config)
        print('✅ 成功从加密变量 HY2_NODE 中解析并生成 hy2_config.yaml！')
    except Exception as e:
        print(f'❌ 解析 Hysteria2 节点链接失败，请检查节点格式。错误: {e}')
        exit(1)

if __name__ == '__main__':
    main()
