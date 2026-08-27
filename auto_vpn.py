import json
import requests
import urllib.parse

# Источники рабочих VLESS-конфигураций
SOURCES = [
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/vless",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
]

def parse_vless(url_str, index):
    """Преобразует vless:// ссылку в валидный объект outbound для Sing-Box"""
    try:
        parsed = urllib.parse.urlparse(url_str)
        params = urllib.parse.parse_qs(parsed.query)
        tag_name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"Server-{index}"
        
        # Базовая структура ноды
        outbound = {
            "type": "vless",
            "tag": f"[{index}] {tag_name[:20]}",
            "server": parsed.hostname,
            "server_port": int(parsed.port or 443),
            "uuid": parsed.username,
            "network": params.get("type", ["tcp"])[0],
            "tls": {
                "enabled": params.get("security", ["none"])[0] in ["tls", "reality"],
                "server_name": params.get("sni", [""])[0] or parsed.hostname,
                "insecure": True
            }
        }
        
        # Если используется Reality
        if params.get("security", ["none"])[0] == "reality":
            outbound["tls"]["reality"] = {
                "enabled": True,
                "public_key": params.get("pbk", [""])[0],
                "short_id": params.get("sid", [""])[0]
            }
            
        # Если используется WebSocket
        if params.get("type", [""])[0] == "ws":
            outbound["transport"] = {
                "type": "ws",
                "path": params.get("path", ["/"])[0]
            }
            
        return outbound
    except Exception:
        return None

def build_singbox_config():
    collected_outbounds = []
    server_tags = []
    count = 1
    
    # Сбор серверов
    for src in SOURCES:
        try:
            res = requests.get(src, timeout=10)
            if res.status_code == 200:
                lines = res.text.strip().splitlines()
                for line in lines:
                    line = line.strip()
                    if line.startswith("vless://") and count <= 25:
                        node = parse_vless(line, count)
                        if node and node["server"]:
                            collected_outbounds.append(node)
                            server_tags.append(node["tag"])
                            count += 1
        except Exception as e:
            print(f"Ошибка загрузки источника: {e}")

    # Обязательные базовые outbounds для Sing-Box
    outbounds = [
        {
            "type": "selector",
            "tag": "select",
            "outbounds": server_tags if server_tags else ["direct"],
            "default": server_tags[0] if server_tags else "direct"
        },
        {"type": "direct", "tag": "direct"},
        {"type": "block", "tag": "block"}
    ] + collected_outbounds

    # Полный валидный JSON-каркас Sing-Box
    full_config = {
        "log": {
            "level": "warn",
            "timestamp": True
        },
        "dns": {
            "servers": [
                {"tag": "google", "address": "tls://8.8.8.8"},
                {"tag": "local", "address": "223.5.5.5", "detour": "direct"}
            ]
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 2080
            }
        ],
        "outbounds": outbounds,
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "google"}
            ],
            "auto_detect_interface": True
        }
    }

    # Запись в файл
    with open("happ_singbox.json", "w", encoding="utf-8") as f:
        json.dump(full_config, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    build_singbox_config()
