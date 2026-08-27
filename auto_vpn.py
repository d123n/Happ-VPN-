import json
import requests
import urllib.parse

# Расширенный список источников с VLESS / Hysteria2 серверами
SOURCES = [
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/vless",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/hysteria2",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt"
]

def parse_vless(url_str, index):
    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme != "vless":
            return None
            
        params = urllib.parse.parse_qs(parsed.query)
        tag_name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else f"Server-{index}"
        
        security = params.get("security", ["none"])[0]
        net_type = params.get("type", ["tcp"])[0]
        sni = params.get("sni", [""])[0] or parsed.hostname
        
        outbound = {
            "type": "vless",
            "tag": f"[{index}] {tag_name[:20]}",
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
                    if line.startswith("vless://") and count <= 30:
                        node = parse_vless(line, count)
                        if node and node.get("server"):
                            collected_servers.append(node)
                            server_tags.append(node["tag"])
                            count += 1
        except Exception as e:
            print(f"Ошибка загрузки из {src}: {e}")

    # Fallback, если список пуст
    if not server_tags:
        print("Внимание: Источники не ответили, создается минимальная заглушка")
        server_tags = ["direct"]

    happ_config = {
        "log": {"level": "warn"},
        "dns": {
            "servers": [
                {"tag": "dns-remote", "address": "https://1.1.1.1/dns-query", "detour": "select"},
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
                "outbounds": server_tags + ["direct"],
                "default": server_tags[0]
            },
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"}
        ] + collected_servers,
        "route": {
            "rules": [
                {"protocol": "dns", "outbound": "dns-remote"}
            ],
            "auto_detect_interface": True
        }
    }

    # Гарантированное создание файла при любом исходе
    with open("happ_config.json", "w", encoding="utf-8") as f:
        json.dump(happ_config, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    generate_happ_config()
