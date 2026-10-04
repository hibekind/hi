# KI-Fotos mit FLUX.2

Erzeugt fotorealistische Bilder lokal mit [FLUX.2](https://github.com/black-forest-labs/flux2) von Black Forest Labs.

## Voraussetzungen

- NVIDIA-Grafikkarte mit mindestens ~8 GB VRAM (für `klein-4b`)
- Python 3.10+
- Ein Hugging-Face-Konto (für `klein-9b` und `dev` musst du auf der Modellseite die Lizenz akzeptieren und dich mit `hf auth login` anmelden)

## Installation

```bash
cd ki-fotos
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Benutzung

```bash
# Landschaftsfoto im 16:9-Format
python foto_generieren.py "Alpine mountains at sunrise, mist over a turquoise lake, pine trees"

# 4 Varianten mit dem besseren Modell, Hochformat
python foto_generieren.py --modell klein-9b --format 2:3 --anzahl 4 "Lighthouse on a cliff during a storm"
```

Die Bilder landen im Ordner `ausgabe/`.

## Modelle

| `--modell` | VRAM | Qualität | Lizenz |
|---|---|---|---|
| `klein-4b` (Standard) | ~8 GB | gut, sehr schnell | Apache 2.0 – auch kommerziell |
| `klein-9b` | ~20 GB | sehr gut | nur nicht-kommerziell |
| `dev` | 24 GB+ (sehr langsam mit Auslagerung) | beste | nur nicht-kommerziell |

## Tipps

- Englische Prompts funktionieren am besten.
- Beschreibe Licht, Tageszeit, Kamera und Objektiv (z. B. „golden hour, 35mm lens“).
- Mit `--seed 42` bekommst du bei gleichem Prompt dasselbe Bild wieder.
