"""Service de lecture/écriture de la configuration de mise en page des templates PDF."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "template_layout.json"

DEFAULT_LAYOUT: dict = {
    "header_left": ["logo", "sender"],
    "header_right": ["recipient", "citydate"],
    "spacing": {
        "page_margin": "2cm 2.5cm",
        "header_mb": 14,
        "section_mb": 12,
        "cell_padding_v": 4,
        "cell_padding_h": 10,
        "line_height": 1.55,
        "font_size": 10,
    },
}


def get_layout() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_LAYOUT.copy()


def save_layout(layout: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
