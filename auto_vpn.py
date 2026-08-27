import json
import re
import requests
import urllib.parse

SOURCES = [
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/vless",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/freefq/free/master/v2"
]

def clean_tag(text):
    """Очищает названия серверов от кавычек, переносов и управляющих символов"""
    if not text:
        return "Server"
    text = urllib.parse.unquote(text)
    # Удаляем все символы, кроме букв, цифр, пробелов и дефисов
    text = re.sub(r'[^\w\s\-\.]', '', text, flags=re.UNICODE)
    return text.strip()[:20] or "Server"

def parse_vless(url_str, index):
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme != "vless":
            return None
            
        params = urllib.parse.parse_qs(parsed.query)
        raw_fragment = parsed.fragment or f"Server-{index}"
        tag_name = clean_tag(raw_fragment)
        
        security = params.get("security", ["none"])[0]
        net_type = params.get("type", ["tcp"])[0]
        sni = params.get("sni", [""])[0] or parsed.hostname
        
        outbound = {
            "type": "vless",
            "tag": f"S{index}-{tag_name}",
            "server": parsed.hostname,
            "server_port": int(parsed.port or 443),
            "uuid": parsed.username
        }
        
        if security in ["tls", "reality"]:
            tls_config = {
                "enabled": True,
                "server_name": sni,
                "insecure": True
            }
            if security == "reality":
                pbk = params.get("pbk", [""])[0]
                sid = params.get("sid", [""])[0]
                if pbk:
                    tls_config["reality"] = {
                        "enabled": True,
                        "public_key": pbk,
                        "short_id": sid
                    }
            outbound["tls"] = tls_config

        if net_type == "ws":
            outbound["transport"] = {
                "type": "ws",
                "path": params.get("path", ["/"])[0]
            }
        elif net_type == "grpc":
            outbound["transport"] = {
                "type": "grpc",
                "service_name": params.get("serviceName", [""])[0]
            }

        flow = params.get("flow", [""])[0]
        if flow:
            outbound["flow"] = flow

        return outbound
    except Exception:
        return None

def generate_happ_config():
    collected_servers = []
    server_tags = []
    count = 1

    for src in SOURCES:
        try:
            res = requests.get(src, timeout=10)
            if res.status_code == 200:
                lines = res.text.strip().splitlines()
                for line in lines:
                    line = line.strip()
                    if line.startswith("vless://") and count <= 20:
                        node = parse_vless(line, count)
                        if node and node.get("server"):
                            collected_servers.append(node)
                            server_tags.append(node["tag"])
                            count += 1
        except Exception as e:
            print(f"Ошибка источника: {e}")

    # Если не удалось получить серверы — добавляем заглушку
    if not server_tags:
        server_tags = ["direct"]

    # Строго валидный JSON-ОБЪЕКТ (словаревая структура Sing-Box)
    happ_config = {
        "log": {
            "level": "warn"
        },
        "dns": {
            "servers": [
                {"tag": "dns-remote", "address": "8.8.8.8"},
                {"tag": "dns-direct", "address": "223.5.5.5", "detour": "direct"}
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
        "outbounds": [
            {
                "type": "selector",
                "tag": "select",
                "outbounds": server_tags,
                "default": server_tags[0]
            },
            {
                "type": "direct",
                "tag": "direct"
            }
        ] + collected_servers,
        "route": {
            "auto_detect_interface": True
        }
    }

    # Запись в файл с отключением не-ASCII символов (гарантирует отсутствие поломанных кодировок)
    with open("happ_config.json", "w", encoding="utf-8") as f:
        json.dump(happ_config, f, indent=2, ensure_ascii=True)

if __name__ == "__main__":
    generate_happ_config()
