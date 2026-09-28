(function () {
  "use strict";

 var HASH_TO_PAGE = {
   "": "start",
   "start": "start",
   "app": "nutzer",
   "veranstalter": "veranstalter",
   "investoren": "investoren",
   "test": "test"
 };

 var pages = Array.prototype.slice.call(document.querySelectorAll("[data-page]"));
  var navLinks = Array.prototype.slice.call(document.querySelectorAll("[data-nav]"));

 function currentPageFromHash() {
   var hash = (location.hash || "").replace(/^#/, "");
   return HASH_TO_PAGE.hasOwnProperty(hash) ? HASH_TO_PAGE[hash] : "start";
 }

 function showPage(pageName, opts) {
   pages.forEach(function (el) {
     el.hidden = el.getAttribute("data-page") !== pageName;
   });
   navLinks.forEach(function (el) {
     el.classList.toggle("active", el.getAttribute("data-nav") === pageName);
   });
   if (!(opts && opts.skipScroll)) {
     window.scrollTo(0, 0);
   }
 }

 function render() {
   showPage(currentPageFromHash());
 }

 window.addEventListener("hashchange", render);
  render();

 // ---- FAQ ----
 var FAQS = [
   ["Kostet die App etwas?", "Nein."],
   ["Brauche ich ein Konto?", "Nein. Mit Konto kannst du umzu auf mehreren Geräten nutzen."],
   ["Gibt es umzu für Android?", "Noch nicht."]
   ];

 var faqList = document.getElementById("faq-list");
  if (faqList) {
    FAQS.forEach(function (pair, i) {
      var item = document.createElement("div");
      item.className = "faq-item";

                 var row = document.createElement("div");
      row.className = "faq-row";

                 var q = document.createElement("span");
      q.textContent = pair[0];

                 var sign = document.createElement("span");
      sign.textContent = "+";

                 row.appendChild(q);
      row.appendChild(sign);
      item.appendChild(row);

                 var answer = document.createElement("p");
      answer.className = "faq-answer";
      answer.textContent = pair[1];
      answer.hidden = true;
      item.appendChild(answer);

                 item.addEventListener("click", function () {
                   var open = !answer.hidden;
                   answer.hidden = open;
                   sign.textContent = open ? "+" : "−";
                 });

                 faqList.appendChild(item);
    });
  }

 // ---- Veranstalter: Rollen-Chips ----
 var KONTAKT_MAIL = "hannafuehner@gmail.com";
  var selectedRolle = "Verein";
  var rollenWrap = document.getElementById("rollen");
  if (rollenWrap) {
    var chips = Array.prototype.slice.call(rollenWrap.querySelectorAll("[data-rolle]"));
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        selectedRolle = chip.getAttribute("data-rolle");
        chips.forEach(function (c) {
          var active = c === chip;
          c.style.border = "1.5px solid " + (active ? "#1F3FC3" : "rgba(28,35,64,0.15)");
          c.style.background = active ? "rgba(31,63,195,0.12)" : "#fff";
          c.style.color = active ? "#1A35A3" : "#1C2340";
        });
      });
    });
  }

 function openMailto(subject, body) {
   var a = document.createElement("a");
   a.href = "mailto:" + KONTAKT_MAIL + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
   a.rel = "noopener";
   document.body.appendChild(a);
   a.click();
   document.body.removeChild(a);
 }

 // ---- Veranstalter: Formular ----
 var fName = document.getElementById("f-name");
  var fMail = document.getElementById("f-mail");
  var fNachricht = document.getElementById("f-nachricht");
  var verSenden = document.getElementById("ver-senden");
  var verFormWrap = document.getElementById("ver-form-wrap");
  var verDanke = document.getElementById("ver-danke");
  var verNeu = document.getElementById("ver-neu");
  var zumFormular = document.getElementById("zum-formular");

 function veranstalterBereit() {
   return !!(fName && fName.value.trim() && fMail && fMail.value.includes("@") && fNachricht && fNachricht.value.trim());
 }

 function updateSendenButton() {
   if (!verSenden) return;
   var bereit = veranstalterBereit();
   verSenden.style.background = bereit ? "#1F3FC3" : "rgba(28,35,64,0.15)";
   verSenden.style.color = bereit ? "#fff" : "#464A5C";
   verSenden.dataset.bereit = bereit ? "1" : "0";
 }

 [fName, fMail, fNachricht].forEach(function (el) {
   if (el) el.addEventListener("input", updateSendenButton);
 });
  updateSendenButton();

 var fOrgEl = document.getElementById("f-org");

 if (verSenden) {
   verSenden.addEventListener("click", function () {
     if (verSenden.dataset.bereit !== "1") return;
     var body = "Rolle: " + selectedRolle + "\\n" +
       "Name: " + fName.value.trim() + "\\n" +
       "Organisation: " + (fOrgEl ? fOrgEl.value.trim() : "") + "\\n" +
       "E-Mail: " + fMail.value.trim() + "\\n\\n" +
       "Nachricht:\\n" + fNachricht.value.trim();
     openMailto("umzu – Veranstalter-Anfrage (" + selectedRolle + ")", body);
     verFormWrap.style.display = "none";
     verDanke.style.display = "block";
   });
 }

 if (verNeu) {
   verNeu.addEventListener("click", function () {
     if (fName) fName.value = "";
     if (fOrgEl) fOrgEl.value = "";
     if (fMail) fMail.value = "";
     if (fNachricht) fNachricht.value = "";
     updateSendenButton();
     verDanke.style.display = "none";
     verFormWrap.style.display = "flex";
   });
 }

 if (zumFormular) {
   zumFormular.addEventListener("click", function () {
     var el = document.getElementById("formular");
     if (el) {
       window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 70, behavior: "smooth" });
     }
   });
 }

 // ---- Mittesten ----
 var testMail = document.getElementById("test-mail");
  var testEintragen = document.getElementById("test-eintragen");
  var testForm = document.getElementById("test-form");
  var testDanke = document.getElementById("test-danke");

 if (testEintragen) {
   testEintragen.addEventListener("click", function () {
     if (testMail && testMail.value.includes("@")) {
       openMailto("umzu – Mittesten-Anmeldung", "E-Mail für die Testeinladung: " + testMail.value.trim());
       testForm.style.display = "none";
       testDanke.style.display = "inline-block";
     }
   });
 }
  if (testMail) {
    testMail.addEventListener("keydown", function (e) {
      if (e.key === "Enter") testEintragen.click();
    });
  }
})();
