"""Rückwärts-Bildsuche für Kleinanzeigen.

Ablauf:
  1. Claude erkennt auf dem Foto, was es ist, und schlägt Suchbegriffe vor.
  2. Für jeden Suchbegriff wird die Kleinanzeigen-Suche abgefragt.
  3. Jede gefundene Anzeige wird einzeln aufgerufen, um zu prüfen, ob sie noch online ist.
  4. Die Vorschaubilder werden mit dem hochgeladenen Foto verglichen
     (Wahrnehmungs-Hash für identische Fotos + optional Claude für ähnliche Artikel).
"""

import base64
import io
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import urljoin

import imagehash
import requests
from bs4 import BeautifulSoup
from PIL import Image
from pydantic import BaseModel

BASIS_URL = "https://www.kleinanzeigen.de"
MODELL = "claude-opus-5-5"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}

# Texte, die auf einer Anzeigenseite stehen, wenn sie nicht mehr online ist
OFFLINE_HINWEISE = (
    "nicht mehr verfügbar",
    "wurde gelöscht",
    "wurde bereits gelöscht",
    "anzeige ist nicht mehr",
    "diese anzeige existiert nicht",
)

# Ab diesem Hash-Abstand gilt ein Bild als "dasselbe Foto"
GLEICHES_FOTO_ABSTAND = 10


@dataclass
class Anzeige:
    id: str
    titel: str
    url: str
    preis: str = ""
    ort: str = ""
    datum: str = ""
    bild_url: str = ""
    reserviert: bool = False
    online: bool | None = None
    hash_abstand: int | None = None
    ki_score: int | None = None
    ki_grund: str = ""
    suchbegriffe: list[str] = field(default_factory=list)

    @property
    def gleiches_foto(self) -> bool:
        return self.hash_abstand is not None and self.hash_abstand <= GLEICHES_FOTO_ABSTAND

    @property
    def score(self) -> int:
        """Gesamt-Ähnlichkeit 0–100 für die Sortierung."""
        if self.gleiches_foto:
            return 100
        if self.ki_score is not None:
            return self.ki_score
        if self.hash_abstand is not None:
            # 64-Bit-Hash: 0 = identisch, ~32 = zufällig
            return max(0, round(100 - self.hash_abstand * 100 / 32))
        return 0


# ---------------------------------------------------------------- 1. Erkennen


class Erkennung(BaseModel):
    produkt: str
    suchbegriffe: list[str]


def _bild_block(bild_bytes: bytes, max_kante: int = 1024) -> dict:
    """Bild verkleinern und als base64-JPEG-Block für die Claude-API verpacken."""
    img = Image.open(io.BytesIO(bild_bytes)).convert("RGB")
    img.thumbnail((max_kante, max_kante))
    puffer = io.BytesIO()
    img.save(puffer, "JPEG", quality=85)
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.standard_b64encode(puffer.getvalue()).decode(),
        },
    }


def erkennen(client, bild_bytes: bytes) -> Erkennung:
    antwort = client.messages.parse(
        model=MODELL,
        max_tokens=4000,
        output_config={"effort": "low"},
        messages=[{
            "role": "user",
            "content": [
                _bild_block(bild_bytes),
                {"type": "text", "text": (
                    "Ich suche diesen Artikel auf Kleinanzeigen (kleinanzeigen.de). "
                    "Bestimme möglichst genau, was zu sehen ist (Marke, Modell, Typ, Farbe, "
                    "Material, wenn erkennbar). Gib unter 'produkt' eine kurze Beschreibung "
                    "auf Deutsch und unter 'suchbegriffe' 3 bis 5 deutsche Suchanfragen, so "
                    "wie Verkäufer ihre Anzeigen betiteln würden: von sehr spezifisch "
                    "(Marke + Modell) bis allgemein (Kategorie + auffälligstes Merkmal). "
                    "Jede Suchanfrage höchstens 4 Wörter."
                )},
            ],
        }],
        output_format=Erkennung,
    )
    if antwort.stop_reason == "refusal" or antwort.parsed_output is None:
        raise RuntimeError("Die KI konnte das Bild nicht auswerten. Bitte Suchbegriffe selbst eingeben.")
    return antwort.parsed_output


# ---------------------------------------------------------------- 2. Suchen


def _text(el) -> str:
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def anzeigen_parsen(html: str) -> list[Anzeige]:
    """Anzeigen aus einer Kleinanzeigen-Suchergebnisseite lesen."""
    soup = BeautifulSoup(html, "html.parser")
    ergebnis = []
    for art in soup.select("article.aditem[data-adid]"):
        href = art.get("data-href") or ""
        link = art.select_one("h2 a, a.ellipsis")
        if not href and link:
            href = link.get("href", "")
        if not href:
            continue
        titel = _text(link) or _text(art.select_one("h2"))

        bild_url = ""
        box = art.select_one(".imagebox")
        img = art.select_one(".imagebox img, img")
        if img is not None:
            bild_url = img.get("src") or img.get("data-src") or ""
        if not bild_url and box is not None:
            bild_url = box.get("data-imgsrc", "")

        badges = _text(art.select_one(".aditem-main--middle")) + " " + titel
        ergebnis.append(Anzeige(
            id=art["data-adid"],
            titel=titel,
            url=urljoin(BASIS_URL, href),
            preis=_text(art.select_one(".aditem-main--middle--price-shipping--price, .aditem-main--middle--price")),
            ort=_text(art.select_one(".aditem-main--top--left")),
            datum=_text(art.select_one(".aditem-main--top--right")),
            bild_url=bild_url,
            reserviert="reserviert" in badges.lower(),
        ))
    return ergebnis


def suchen(session: requests.Session, begriff: str, plz: str = "", radius: int = 0) -> list[Anzeige]:
    params = {"keywords": begriff}
    if plz:
        params["locationStr"] = plz
        if radius:
            params["radius"] = radius
    r = session.get(f"{BASIS_URL}/s-suchanfrage.html", params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    treffer = anzeigen_parsen(r.text)
    for a in treffer:
        a.suchbegriffe.append(begriff)
    return treffer


# ---------------------------------------------------------------- 3. Online-Prüfung


def ist_online(session: requests.Session, anzeige: Anzeige) -> bool:
    """Anzeigenseite abrufen und prüfen, ob die Anzeige noch aktiv ist."""
    try:
        r = session.get(anzeige.url, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException:
        return False
    if r.status_code != 200 or anzeige.id not in r.url:
        # Gelöschte Anzeigen liefern 404/410 oder leiten auf eine Suchseite um
        return False
    seite = r.text.lower()
    if any(h in seite for h in OFFLINE_HINWEISE):
        return False
    if re.search(r'class="[^"]*pvap-reserved-title', r.text) or "reserviert •" in seite:
        anzeige.reserviert = True
    return True


# ---------------------------------------------------------------- 4. Bildvergleich


def _bild_laden(session: requests.Session, url: str) -> bytes | None:
    if not url:
        return None
    try:
        r = session.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        Image.open(io.BytesIO(r.content)).verify()
        return r.content
    except Exception:
        return None


def _phash(bild_bytes: bytes):
    return imagehash.phash(Image.open(io.BytesIO(bild_bytes)).convert("RGB"))


class Bewertung(BaseModel):
    nummer: int
    score: int
    grund: str


class Bewertungen(BaseModel):
    bewertungen: list[Bewertung]


def ki_vergleich(client, original: bytes, kandidaten: list[tuple[Anzeige, bytes]]) -> None:
    """Claude bewertet, wie gut jedes Vorschaubild zum Originalfoto passt."""
    inhalt: list[dict] = [{"type": "text", "text": "Originalfoto:"}, _bild_block(original)]
    for i, (a, b) in enumerate(kandidaten, 1):
        inhalt.append({"type": "text", "text": f"Anzeige {i}: {a.titel}"})
        inhalt.append(_bild_block(b, max_kante=400))
    inhalt.append({"type": "text", "text": (
        "Bewerte für jede Anzeige (nummer = Anzeigennummer), wie wahrscheinlich sie denselben "
        "Artikel wie das Originalfoto anbietet: score 100 = derselbe Gegenstand / dasselbe "
        "Foto, 70–90 = gleiches Modell, 30–60 = ähnlicher Artikel, unter 30 = passt nicht. "
        "'grund' in höchstens 8 Wörtern auf Deutsch."
    )})
    antwort = client.messages.parse(
        model=MODELL,
        max_tokens=8000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": inhalt}],
        output_format=Bewertungen,
    )
    if antwort.parsed_output is None:
        return
    for bw in antwort.parsed_output.bewertungen:
        if 1 <= bw.nummer <= len(kandidaten):
            a = kandidaten[bw.nummer - 1][0]
            a.ki_score = max(0, min(100, bw.score))
            a.ki_grund = bw.grund


# ---------------------------------------------------------------- Gesamtablauf


@dataclass
class Suchergebnis:
    produkt: str
    suchbegriffe: list[str]
    anzeigen: list[Anzeige]
    offline_aussortiert: int
    hinweise: list[str]


def rueckwaertssuche(
    bild_bytes: bytes,
    eigene_begriffe: list[str] | None = None,
    plz: str = "",
    radius: int = 0,
    reservierte_ausblenden: bool = False,
    ki_bildvergleich: bool = True,
    max_anzeigen: int = 40,
    client=None,
    session: requests.Session | None = None,
) -> Suchergebnis:
    session = session or requests.Session()
    hinweise: list[str] = []
    produkt = ""
    begriffe = [b for b in (eigene_begriffe or []) if b.strip()]

    if client is not None:
        erkennung = erkennen(client, bild_bytes)
        produkt = erkennung.produkt
        begriffe = begriffe + [b for b in erkennung.suchbegriffe if b not in begriffe]
    if not begriffe:
        raise ValueError("Keine Suchbegriffe – bitte ANTHROPIC_API_KEY setzen oder Begriffe eingeben.")

    # Suchen (nacheinander, um Kleinanzeigen nicht zu fluten)
    gefunden: dict[str, Anzeige] = {}
    for begriff in begriffe:
        try:
            for a in suchen(session, begriff, plz, radius):
                if a.id in gefunden:
                    gefunden[a.id].suchbegriffe.append(begriff)
                else:
                    gefunden[a.id] = a
        except requests.RequestException as e:
            hinweise.append(f"Suche nach „{begriff}“ fehlgeschlagen: {e}")
        time.sleep(0.5)

    # Anzeigen, die zu mehreren Suchbegriffen passen, zuerst prüfen
    kandidaten = sorted(gefunden.values(), key=lambda a: -len(a.suchbegriffe))[:max_anzeigen]

    # Online-Prüfung + Vorschaubilder laden (parallel, aber gedrosselt)
    original_hash = _phash(bild_bytes)
    bilder: dict[str, bytes] = {}

    def pruefen(a: Anzeige):
        a.online = ist_online(session, a)
        if a.online:
            b = _bild_laden(session, a.bild_url)
            if b:
                bilder[a.id] = b
                try:
                    a.hash_abstand = original_hash - _phash(b)
                except Exception:
                    pass

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(pruefen, kandidaten))

    online = [a for a in kandidaten if a.online]
    offline = len(kandidaten) - len(online)
    if reservierte_ausblenden:
        online = [a for a in online if not a.reserviert]

    if client is not None and ki_bildvergleich:
        mit_bild = [(a, bilder[a.id]) for a in online if a.id in bilder]
        # in Blöcken à 15 Bildern bewerten
        for i in range(0, len(mit_bild), 15):
            try:
                ki_vergleich(client, bild_bytes, mit_bild[i:i + 15])
            except Exception as e:
                hinweise.append(f"KI-Bildvergleich teilweise fehlgeschlagen: {e}")
                break

    online.sort(key=lambda a: (-a.score, a.reserviert))
    return Suchergebnis(produkt, begriffe, online, offline, hinweise)
