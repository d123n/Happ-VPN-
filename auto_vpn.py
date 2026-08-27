import base64
import requests

SOURCES = [
    "[https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/vless](https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/vless)",
    "[https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/hysteria2](https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/normal/hysteria2)",
    "[https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt](https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt)",
]

PREFER_PROTOCOLS = ("vless://", "hysteria2://", "hy2://", "tuic://")


def get_configs_from_source(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            content = response.text.strip()
            try:
                decoded = base64.b64decode(content).decode("utf-8")
                return decoded.splitlines()
            except Exception:
                return content.splitlines()
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
    return []


def filter_working_configs():
    all_configs = []
    for src in SOURCES:
        configs = get_configs_from_source(src)
        all_configs.extend(configs)

    working_configs = []
    for config in all_configs:
        config = config.strip()
        if config.startswith(PREFER_PROTOCOLS):
            working_configs.append(config)

    unique_configs = list(set(working_configs))
    final_list = unique_configs[:50]

    payload = "\n".join(final_list)
    encoded_sub = base64.b64encode(payload.encode("utf-8")).decode("utf-8")

    with open("happ_subscription.txt", "w", encoding="utf-8") as f:
        f.write(encoded_sub)


if __name__ == "__main__":
    filter_working_configs()
