# Kleinanzeigen Bildsuche

Wie die Google-Rückwärtssuche, nur für Kleinanzeigen: Foto hochladen, und die App zeigt passende Anzeigen, **die noch online sind**.

## So funktioniert's

1. **Erkennen:** Claude schaut sich das Foto an und erzeugt 3–5 Suchbegriffe (z. B. „Gazelle Hollandrad grün“).
2. **Suchen:** Für jeden Begriff wird die Kleinanzeigen-Suche abgefragt (optional mit PLZ und Umkreis).
3. **Online-Prüfung:** Jede gefundene Anzeige wird einzeln aufgerufen. Gelöschte oder abgelaufene Anzeigen werden aussortiert, reservierte markiert (oder auf Wunsch ausgeblendet).
4. **Bildvergleich:** Die Vorschaubilder werden mit deinem Foto verglichen:
   - Wahrnehmungs-Hash → erkennt **dasselbe Foto** (z. B. weiterverkauftes oder geklautes Rad, Fake-Anzeigen mit kopierten Bildern)
   - KI-Bildvergleich → bewertet, wie gut der Artikel passt (0–100 %)

Die Ergebnisse sind nach Ähnlichkeit sortiert.

## Installation

```bash
cd kleinanzeigen-suche
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Für die automatische Bilderkennung brauchst du einen API-Schlüssel von https://console.anthropic.com:

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # Windows: set ANTHROPIC_API_KEY=sk-ant-...
```

Ohne Schlüssel funktioniert die App auch – dann gibst du die Suchbegriffe selbst ein, und es wird nur der Hash-Vergleich (gleiches Foto) genutzt.

## Starten

```bash
python app.py
```

Dann http://localhost:5000 öffnen. Foto per Klick, Drag & Drop oder **Strg+V** (Einfügen aus der Zwischenablage) hinzufügen.

## Hinweise

- Die App liest die öffentliche Kleinanzeigen-Website. Wenn Kleinanzeigen das Seitenlayout ändert, muss evtl. `anzeigen_parsen()` in `suche.py` angepasst werden.
- Sie läuft am besten lokal auf deinem Rechner. Viele schnelle Anfragen können dazu führen, dass Kleinanzeigen dich vorübergehend blockiert – die App fragt deshalb nacheinander bzw. gedrosselt ab (max. 40 Anzeigen pro Suche).
- Kosten: Eine Suche mit KI-Bildvergleich kostet einige Cent API-Guthaben. Den Haken bei „KI-Bildvergleich“ kannst du abwählen.
- Tests: `pip install pytest && python -m pytest tests`
