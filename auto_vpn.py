import json
import requests
import urllib.parse

# Источники рабочих конфигураций
SOURCES = [
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/vless",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/hysteria2",
]

def parse_vless(url_str):
    """Парсинг VLESS-ссылки в формат объекта Sing-box"""
    try:
        parsed = urllib.parse.urlparse(url_str)
        params = urllib.parse.parse_qs(parsed.query)
        fragment = urllib.parse.unquote(parsed.fragment) or "VLESS Server"
        
        outbound = {
            "type": "vless",
            "tag": fragment,
            "server": parsed.hostname,
            "server_port": parsed.port or 443,
            "uuid": parsed.username,
            "network": params.get("type", ["tcp"])[0],
            "tls": {
                "enabled": params.get("security", ["none"])[0] in ["tls", "reality"],
                "server_name": params.get("sni", [""])[0] or parsed.hostname,
                "insecure": True
            }
        }
        
        if params.get("security", ["none"])[0] == "reality":
            outbound["tls"]["reality"] = {
                "enabled": True,
                "public_key": params.get("pbk", [""])[0],
                "short_id": params.get("sid", [""])[0]
            }
            
        if params.get("type", [""])[0] == "ws":
            outbound["transport"] = {
                "type": "ws",
                "path": params.get("path", ["/"])[0]
            }
            
        return outbound
    except Exception:
        return None

def build_singbox_config():
    outbounds = []
    
    # Резервный прямой выход
    outbounds.append({"type": "direct", "tag": "direct"})
    
    server_tags = []
    count = 0
    
    for src in SOURCES:
        try:
            res = requests.get(src, timeout=10)
            if res.status_code == 200:
                lines = res.text.strip().splitlines()
                for line in lines:
                    line = line.strip()
                    if line.startswith("vless://") and count < 20:
                        node = parse_vless(line)
                        if node:
                            outbounds.append(node)
                            server_tags.append(node["tag"])
                            count += 1
        except Exception as e:
            print(f"Ошибка загрузки {src}: {e}")

    # Создаем селектор вывода (для удобного переключения в Happ)
    if server_tags:
        outbounds.insert(0, {
            "type": "selector",
            "tag": "select",
            "outbounds": server_tags + ["direct"],
            "default": server_tags[0]
        })

    config = {
        "outbounds": outbounds
    }

    # Сохраняем в JSON
    with open("happ_singbox.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    build_singbox_config()
