"""Web-Oberfläche: Foto hochladen -> passende, noch aktive Kleinanzeigen.

Start:  python app.py   ->  http://localhost:5000
"""

import os

from flask import Flask, render_template, request

from suche import rueckwaertssuche

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15 MB


def _claude_client():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic
    return anthropic.Anthropic()


@app.get("/")
def start():
    return render_template("index.html", ki=bool(os.environ.get("ANTHROPIC_API_KEY")))


@app.post("/suche")
def suche():
    ki = bool(os.environ.get("ANTHROPIC_API_KEY"))
    datei = request.files.get("bild")
    if not datei or not datei.filename:
        return render_template("index.html", ki=ki, fehler="Bitte ein Foto auswählen.")

    begriffe = [b.strip() for b in request.form.get("begriffe", "").split(",")]
    try:
        radius = int(request.form.get("radius") or 0)
    except ValueError:
        radius = 0

    try:
        ergebnis = rueckwaertssuche(
            datei.read(),
            eigene_begriffe=begriffe,
            plz=request.form.get("plz", "").strip(),
            radius=radius,
            reservierte_ausblenden=bool(request.form.get("ohne_reserviert")),
            ki_bildvergleich=bool(request.form.get("ki_vergleich")),
            client=_claude_client(),
        )
    except Exception as e:
        return render_template("index.html", ki=ki, fehler=str(e))

    return render_template("index.html", ki=ki, ergebnis=ergebnis)


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
