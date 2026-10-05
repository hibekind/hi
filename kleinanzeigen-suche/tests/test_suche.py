import io

import requests
from PIL import Image, ImageDraw

import suche

SUCHSEITE = """
<ul id="srchrslt-adtable">
 <li class="ad-listitem"><article class="aditem" data-adid="111" data-href="/s-anzeige/gazelle-rad/111-217-1234">
  <div class="aditem-image"><a href="/s-anzeige/gazelle-rad/111-217-1234"><div class="imagebox srpimagebox" data-imgsrc="https://img.example/111.jpg"><img src="https://img.example/111.jpg"></div></a></div>
  <div class="aditem-main"><div class="aditem-main--top"><div class="aditem-main--top--left"> 10115 Mitte (2 km)</div><div class="aditem-main--top--right"> Heute, 10:12</div></div>
  <div class="aditem-main--middle"><h2 class="text-module-begin"><a class="ellipsis" href="/s-anzeige/gazelle-rad/111-217-1234">Gazelle Hollandrad grün</a></h2>
  <div class="aditem-main--middle--price-shipping"><p class="aditem-main--middle--price-shipping--price"> 250 € VB </p></div></div></div>
 </article></li>
 <li class="ad-listitem"><article class="aditem" data-adid="222" data-href="/s-anzeige/altes-rad/222-217-1234">
  <div class="imagebox" data-imgsrc="https://img.example/222.jpg"></div>
  <div class="aditem-main--middle"><h2><a class="ellipsis" href="/s-anzeige/altes-rad/222-217-1234">Altes Rad</a></h2></div>
 </article></li>
 <li class="ad-listitem"><article class="aditem" data-adid="333" data-href="/s-anzeige/rad-reserviert/333-217-1234">
  <div class="imagebox"><img src="https://img.example/333.jpg"></div>
  <div class="aditem-main--middle"><h2><a class="ellipsis" href="/s-anzeige/rad-reserviert/333-217-1234">Reserviert • Fahrrad blau</a></h2></div>
 </article></li>
 <li class="ad-listitem"><article class="aditem" data-adid="444" data-href="/s-anzeige/rad-weg/444-217-1234">
  <div class="aditem-main--middle"><h2><a class="ellipsis" href="/s-anzeige/rad-weg/444-217-1234">Gelöschtes Rad</a></h2></div>
 </article></li>
</ul>"""


def bild(farbe, form="kreis"):
    img = Image.new("RGB", (200, 150), "white")
    d = ImageDraw.Draw(img)
    if form == "kreis":
        d.ellipse((30, 20, 170, 130), fill=farbe)
    else:
        d.rectangle((10, 60, 190, 80), fill=farbe)
        d.line((0, 0, 200, 150), fill="black", width=8)
    b = io.BytesIO(); img.save(b, "JPEG"); return b.getvalue()


ORIGINAL = bild("green")


class Antwort:
    def __init__(self, url, status=200, text="", content=b""):
        self.url, self.status_code, self.text, self.content = url, status, text, content

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.status_code)


class FakeSession:
    def __init__(self):
        self.aufrufe = []

    def get(self, url, params=None, **kw):
        self.aufrufe.append((url, params))
        if "s-suchanfrage" in url:
            return Antwort(url, text=SUCHSEITE)
        if url.endswith("111-217-1234"):
            return Antwort(url, text="<h1>Gazelle Hollandrad grün</h1>")
        if url.endswith("222-217-1234"):  # gelöscht -> Umleitung auf Suchseite
            return Antwort("https://www.kleinanzeigen.de/s-fahrrad/k0", text="Die gewünschte Anzeige ist nicht mehr verfügbar")
        if url.endswith("333-217-1234"):
            return Antwort(url, text='<h1 class="pvap-reserved-title">Reserviert</h1>')
        if url.endswith("444-217-1234"):
            return Antwort(url, status=410)
        if url == "https://img.example/111.jpg":
            return Antwort(url, content=ORIGINAL)
        if url == "https://img.example/333.jpg":
            return Antwort(url, content=bild("blue", "strich"))
        return Antwort(url, status=404)


def test_parser():
    a = suche.anzeigen_parsen(SUCHSEITE)
    assert [x.id for x in a] == ["111", "222", "333", "444"]
    assert a[0].titel == "Gazelle Hollandrad grün"
    assert a[0].preis == "250 € VB"
    assert a[0].ort == "10115 Mitte (2 km)"
    assert a[0].url == "https://www.kleinanzeigen.de/s-anzeige/gazelle-rad/111-217-1234"
    assert a[1].bild_url == "https://img.example/222.jpg"
    assert a[2].reserviert and not a[0].reserviert


def test_gesamtablauf_ohne_ki():
    s = FakeSession()
    erg = suche.rueckwaertssuche(ORIGINAL, eigene_begriffe=["hollandrad", "gazelle"], plz="10115", radius=10, session=s)
    ids = [a.id for a in erg.anzeigen]
    assert ids == ["111", "333"]          # 222 + 444 offline aussortiert
    assert erg.offline_aussortiert == 2
    assert erg.anzeigen[0].gleiches_foto
    assert erg.anzeigen[1].reserviert
    assert s.aufrufe[0][1] == {"keywords": "hollandrad", "locationStr": "10115", "radius": 10}


def test_reservierte_ausblenden():
    erg = suche.rueckwaertssuche(ORIGINAL, eigene_begriffe=["rad"], reservierte_ausblenden=True, session=FakeSession())
    assert [a.id for a in erg.anzeigen] == ["111"]


class FakeClaude:
    """Simuliert client.messages.parse für Erkennung und Bildvergleich."""
    def __init__(self):
        self.messages = self

    def parse(self, output_format, **kw):
        class R: stop_reason = "end_turn"
        if output_format is suche.Erkennung:
            R.parsed_output = suche.Erkennung(produkt="Grünes Hollandrad", suchbegriffe=["hollandrad grün"])
        else:
            R.parsed_output = suche.Bewertungen(bewertungen=[suche.Bewertung(nummer=2, score=40, grund="anderes Rad")])
        return R


def test_mit_ki():
    erg = suche.rueckwaertssuche(ORIGINAL, client=FakeClaude(), session=FakeSession())
    assert erg.produkt == "Grünes Hollandrad"
    assert erg.suchbegriffe == ["hollandrad grün"]
    assert erg.anzeigen[1].ki_score == 40 and erg.anzeigen[1].ki_grund == "anderes Rad"


def test_weboberflaeche(monkeypatch):
    import app as webapp
    original = suche.rueckwaertssuche
    monkeypatch.setattr(webapp, "rueckwaertssuche", lambda *a, **kw: original(*a, session=FakeSession(), **kw))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c = webapp.app.test_client()
    assert "Kleinanzeigen Bildsuche" in c.get("/").get_data(as_text=True)
    r = c.post("/suche", data={"bild": (io.BytesIO(ORIGINAL), "rad.jpg"), "begriffe": "hollandrad"},
               content_type="multipart/form-data")
    html = r.get_data(as_text=True)
    assert "Gleiches Foto" in html and "Gazelle Hollandrad grün" in html and "Gelöschtes Rad" not in html
