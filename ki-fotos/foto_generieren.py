"""Fotorealistische Bilder mit FLUX.2 (Black Forest Labs) erzeugen.

Beispiel:
    python foto_generieren.py "Berge bei Sonnenaufgang über einem See"
    python foto_generieren.py --modell klein-9b --format 3:2 --anzahl 4 "Leuchtturm im Sturm"
"""

import argparse
from pathlib import Path

import torch
from diffusers import Flux2KleinPipeline, Flux2Pipeline

# name: (Hugging-Face-ID, Pipeline, Schritte, Guidance)
MODELLE = {
    # ~8 GB VRAM, Apache 2.0 (auch kommerziell nutzbar), sehr schnell
    "klein-4b": ("black-forest-labs/FLUX.2-klein-4B", Flux2KleinPipeline, 4, 1.0),
    # bessere Qualität, mehr VRAM, nur nicht-kommerziell
    "klein-9b": ("black-forest-labs/FLUX.2-klein-9B", Flux2KleinPipeline, 4, 1.0),
    # beste Qualität (32B), braucht sehr viel VRAM, nur nicht-kommerziell
    "dev": ("black-forest-labs/FLUX.2-dev", Flux2Pipeline, 50, 4.0),
}

FORMATE = {
    "1:1": (1024, 1024),
    "3:2": (1216, 832),
    "2:3": (832, 1216),
    "16:9": (1344, 768),
    "9:16": (768, 1344),
}

FOTO_ZUSATZ = (
    ", professional photograph, shot on a full-frame camera, natural lighting, "
    "sharp focus, highly detailed, realistic colors"
)


def main():
    parser = argparse.ArgumentParser(description="Fotos mit FLUX.2 erzeugen")
    parser.add_argument("prompt", help="Bildbeschreibung (Englisch liefert meist die besten Ergebnisse)")
    parser.add_argument("--modell", choices=MODELLE, default="klein-4b")
    parser.add_argument("--format", choices=FORMATE, default="16:9")
    parser.add_argument("--anzahl", type=int, default=1, help="Anzahl der Bilder")
    parser.add_argument("--seed", type=int, default=None, help="Für reproduzierbare Ergebnisse")
    parser.add_argument("--ohne-foto-stil", action="store_true", help="Keinen Foto-Zusatz an den Prompt hängen")
    parser.add_argument("--ausgabe", default="ausgabe", help="Zielordner")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("Keine NVIDIA-Grafikkarte (CUDA) gefunden – FLUX.2 braucht eine GPU.")

    model_id, pipeline_cls, schritte, guidance = MODELLE[args.modell]
    pipe = pipeline_cls.from_pretrained(model_id, torch_dtype=torch.bfloat16)
    # Lagert Modellteile in den Arbeitsspeicher aus, wenn die GPU zu klein ist
    pipe.enable_model_cpu_offload()

    breite, hoehe = FORMATE[args.format]
    prompt = args.prompt if args.ohne_foto_stil else args.prompt + FOTO_ZUSATZ
    generator = torch.Generator("cpu").manual_seed(args.seed) if args.seed is not None else None

    bilder = pipe(
        prompt=prompt,
        width=breite,
        height=hoehe,
        num_inference_steps=schritte,
        guidance_scale=guidance,
        num_images_per_prompt=args.anzahl,
        generator=generator,
    ).images

    ausgabe = Path(args.ausgabe)
    ausgabe.mkdir(parents=True, exist_ok=True)
    start = len(list(ausgabe.glob("foto_*.png")))
    for i, bild in enumerate(bilder, start=start + 1):
        pfad = ausgabe / f"foto_{i:04d}.png"
        bild.save(pfad)
        print(f"Gespeichert: {pfad}")


if __name__ == "__main__":
    main()
