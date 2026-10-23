(function () {
  "use strict";

  // Öffentlicher Publishable Key aus der Umzu-Konfiguration. Kein Geheimnis.
  var SUPABASE_URL = "https://xlclrnholnyhjzxkdgby.supabase.co";
  var SUPABASE_KEY = "sb_publishable_1fHUlfjGF_idfYOwpn8giw_iIP3up4B";
  var UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  function $(id) {
    return document.getElementById(id);
  }

  function eventIdAusPfad() {
    var pfad = (location.pathname || "/").replace(/\/+$/, "") || "/";
    var teile = pfad.split("/");
    if (teile[1] !== "event") return null;
    if (teile.length === 3 && UUID.test(teile[2])) return teile[2].toLowerCase();
    return "";
  }

  function text(id, inhalt) {
    var el = $(id);
    if (!inhalt) {
      el.textContent = "";
      el.hidden = true;
      return;
    }
    el.textContent = inhalt;
    el.hidden = false;
  }

  function seiteWeg() {
    text("titel", "Diese Seite gibt es nicht.");
    text("hinweis", "");
    text("wann", "");
    text("ort", "");
    text("adresse", "");
    text("meldung", "");
    $("bild").hidden = true;
    $("bild").removeAttribute("src");
    $("store").hidden = true;
    $("startseite").hidden = false;
    document.title = "umzu";
  }

  function eventWeg(satz) {
    text("titel", satz);
    text("hinweis", "");
    text("wann", "");
    text("ort", "");
    text("adresse", "");
    text("meldung", "");
    $("bild").hidden = true;
    $("bild").removeAttribute("src");
    $("store").hidden = false;
    $("startseite").hidden = true;
    document.title = "umzu";
  }

  function grossbuchstabe(wert) {
    if (!wert) return "";
    return wert.charAt(0).toUpperCase() + wert.slice(1);
  }

  function teile(datum, optionen) {
    var map = {};
    new Intl.DateTimeFormat("de-DE", optionen).formatToParts(datum).forEach(function (teil) {
      if (teil.type !== "literal") map[teil.type] = teil.value;
    });
    return map;
  }

  function datumLang(datum) {
    var map = teile(datum, {
      timeZone: "Europe/Berlin",
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric"
    });
    return grossbuchstabe(map.weekday) + ", " + map.day + ". " + map.month + " " + map.year;
  }

  function uhrzeit(datum) {
    var map = teile(datum, {
      timeZone: "Europe/Berlin",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23"
    });
    return map.hour + ":" + map.minute;
  }

  function tag(datum) {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: "Europe/Berlin",
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    }).format(datum);
  }

  function zeitText(startIso, endeIso) {
    var start = new Date(startIso);
    if (isNaN(start.getTime())) return "";
    var ende = endeIso ? new Date(endeIso) : null;
    if (!ende || isNaN(ende.getTime()) || ende.getTime() === start.getTime()) {
      return datumLang(start) + ", " + uhrzeit(start) + " Uhr";
    }
    if (tag(start) === tag(ende)) {
      return datumLang(start) + ", " + uhrzeit(start) + " bis " + uhrzeit(ende) + " Uhr";
    }
    return datumLang(start) + ", " + uhrzeit(start) + " Uhr bis " + datumLang(ende) + ", " + uhrzeit(ende) + " Uhr";
  }

  function istVorbei(event) {
    var start = Date.parse(event.startdatum);
    var ende = event.enddatum ? Date.parse(event.enddatum) : start;
    if (isNaN(start)) return false;
    if (isNaN(ende)) ende = start;
    return Math.max(start, ende) < Date.now();
  }

  function httpsBild(wert) {
    if (typeof wert !== "string" || !wert) return "";
    try {
      var url = new URL(wert);
      if (url.protocol !== "https:") return "";
      return url.href;
    } catch (fehler) {
      return "";
    }
  }

  function zeigeEvent(event) {
    var titel = typeof event.titel === "string" ? event.titel.trim() : "";
    var name = typeof event.ortname === "string" ? event.ortname.trim() : "";
    var adresse = typeof event.adresse === "string" ? event.adresse.trim() : "";
    var bildUrl = httpsBild(event.bild);
    var img = $("bild");

    text("meldung", "");
    text("titel", titel || "Event");
    text("wann", zeitText(event.startdatum, event.enddatum));
    text("hinweis", istVorbei(event) ? "Dieses Event ist vorbei." : "");
    if (name && adresse && adresse.toLowerCase() !== name.toLowerCase()) {
      text("ort", name);
      text("adresse", adresse);
    } else {
      text("ort", name || adresse);
      text("adresse", "");
    }

    if (bildUrl) {
      img.alt = titel || "Event";
      img.onerror = function () {
        img.hidden = true;
      };
      img.src = bildUrl;
      img.hidden = false;
    } else {
      img.hidden = true;
      img.removeAttribute("src");
    }

    $("store").hidden = false;
    $("startseite").hidden = true;
    document.title = (titel || "Event") + " | umzu";
  }

  function api(pfad, optionen) {
    var kopf = {
      apikey: SUPABASE_KEY,
      Authorization: "Bearer " + SUPABASE_KEY,
      Accept: "application/json"
    };
    if (optionen.body) kopf["Content-Type"] = "application/json";
    return fetch(SUPABASE_URL + pfad, {
      method: optionen.method || "GET",
      headers: kopf,
      body: optionen.body || undefined,
      credentials: "omit",
      cache: "no-store"
    }).then(function (antwort) {
      if (!antwort.ok) throw new Error("http");
      return antwort.json();
    });
  }

  function laden(id) {
    return api("/rest/v1/rpc/event_hauptkarte", {
      method: "POST",
      body: JSON.stringify({ gesuchte_id: id })
    }).then(function (hauptId) {
      if (typeof hauptId !== "string" || !UUID.test(hauptId)) return null;
      var query = "/rest/v1/events?id=eq." + encodeURIComponent(hauptId) +
        "&veroeffentlicht=eq.true&select=id,titel,startdatum,enddatum,ortname,adresse,bild&limit=1";
      return api(query, { method: "GET" });
    }).then(function (zeilen) {
      if (!zeilen) return null;
      if (!zeilen.length) return null;
      return zeilen[0];
    });
  }

  var id = eventIdAusPfad();
  if (id === null) {
    seiteWeg();
    return;
  }
  if (!id) {
    eventWeg("Dieses Event gibt es leider nicht mehr.");
    return;
  }

  laden(id).then(function (event) {
    if (!event) {
      eventWeg("Dieses Event gibt es leider nicht mehr.");
      return;
    }
    zeigeEvent(event);
  }).catch(function () {
    eventWeg("Die Angaben lassen sich gerade nicht laden.");
  });
})();
