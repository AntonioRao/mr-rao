/* Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
   SPDX-License-Identifier: AGPL-3.0-or-later
   Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
   GNU Affero General Public License pubblicata dalla Free Software Foundation,
   versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository. */
/* Anteprima Markdown (P1.4).
 *
 * Un renderer scritto in casa invece di una libreria. Due ragioni, e la
 * seconda e' quella vera:
 *
 *  - una dipendenza in piu' e' peso nel portable e una licenza da rispettare;
 *  - un renderer generico rende anche le immagini remote, e un `<img src>`
 *    verso l'esterno e' una chiamata di rete partita dal documento che stai
 *    anonimizzando. Mr. Rao promette che non esce niente: l'anteprima non
 *    puo' essere l'eccezione, e qui le immagini restano una didascalia.
 *
 * Il testo in ingresso e' il contenuto di un documento altrui: si scappa
 * PRIMA e si costruiscono i tag DOPO. Non esiste un percorso in cui
 * dell'HTML del documento arrivi al DOM.
 *
 * Vive in un file suo, e non dentro app.js, per poterlo provare da node
 * senza un DOM: un renderer si giudica su liste annidate e tabelle storte,
 * casi che a mano non si guardano mai.
 */
(function (globale) {
  "use strict";

  var VOCE = /^([ \t]*)([-*+]|\d{1,9}[.)])[ \t]+(.*)$/;
  var TITOLO = /^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$/;
  var RIGA_ORIZZONTALE = /^ {0,3}([-*_])[ \t]*(?:\1[ \t]*){2,}$/;
  var RECINTO = /^([ \t]*)(```|~~~)[ \t]*([\w+-]*)[ \t]*$/;
  // Si riconosce sul testo GREZZO, non su quello gia' scappato.
  //
  // Prima la riga veniva scappata per cercare `&gt;`, e poi il contenuto
  // riportato indietro a colpi di replace per poterlo rendere di nuovo. Quel
  // giro di andata e ritorno e' sbagliato e basta: un documento che contiene
  // scritto per davvero `&quot;` ne uscirebbe con un apice doppio, cioe' con
  // il testo cambiato. Il riconoscimento dei blocchi guarda il testo com'e';
  // a scappare ci pensa `inRiga`, una volta sola, alla fine.
  var CITAZIONE = /^ {0,3}>[ \t]?(.*)$/;
  var SEPARATORE_TABELLA = /^[ \t]*\|?[ \t]*:?-+:?[ \t]*(\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/;

  // Schemi che possono finire dentro un href. Tutto il resto — `javascript:`,
  // `data:`, `file:` — diventa testo: un documento convertito non ha titolo
  // per far eseguire niente, ne' per aprire percorsi locali.
  var SCHEMA_AMMESSO = /^(?:https?:\/\/|mailto:|#|\/)/i;

  var SEGNA = "\u0000";

  function scappa(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function larghezzaRientro(s) {
    return s.replace(/\t/g, "    ").length;
  }

  /* ------------------------------------------------------------- in riga */

  function inRiga(s) {
    var codici = [];
    var t = scappa(s);

    // Il codice esce di scena per primo e rientra per ultimo: dentro
    // `a_*_b` gli asterischi sono codice, non corsivo.
    t = t.replace(/(`+)([\s\S]*?)\1/g, function (_, apici, corpo) {
      codici.push(corpo);
      return SEGNA + (codici.length - 1) + SEGNA;
    });

    // Immagine: didascalia, mai una richiesta di rete.
    t = t.replace(/!\[([^\]]*)\]\(([^)\s]*)[^)]*\)/g, function (_, alt) {
      return '<span class="md-img">' + (alt || "immagine") + "</span>";
    });

    t = t.replace(/\[([^\]]+)\]\(([^)\s]+)(?:[ \t]+&quot;[^)]*&quot;)?\)/g,
      function (intero, testo, url) {
        if (!SCHEMA_AMMESSO.test(url)) return testo;
        return '<a href="' + url + '" rel="noopener noreferrer nofollow">' + testo + "</a>";
      });

    t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    t = t.replace(/(^|[^\w])__([^_]+)__(?=[^\w]|$)/g, "$1<strong>$2</strong>");
    t = t.replace(/(^|[^*\w])\*([^*\n]+)\*(?=[^*\w]|$)/g, "$1<em>$2</em>");
    // Il trattino basso fa corsivo solo fuori da una parola: in un documento
    // convertito `nome_file` e `api_key` sono la norma, non l'eccezione.
    t = t.replace(/(^|[^\w`])_([^_\n]+)_(?=[^\w]|$)/g, "$1<em>$2</em>");
    t = t.replace(/~~([^~]+)~~/g, "<del>$1</del>");

    return t.replace(new RegExp(SEGNA + "(\\d+)" + SEGNA, "g"), function (_, i) {
      return "<code>" + codici[Number(i)] + "</code>";
    });
  }

  /* ------------------------------------------------------------- tabelle */

  function celle(riga) {
    var t = riga.trim().replace(/^\|/, "").replace(/\|$/, "");
    return t.split("|").map(function (c) {
      return c.trim();
    });
  }

  function allineamenti(riga) {
    return celle(riga).map(function (c) {
      var a = c.charAt(0) === ":";
      var b = c.charAt(c.length - 1) === ":";
      if (a && b) return "center";
      if (b) return "right";
      if (a) return "left";
      return "";
    });
  }

  function tabella(righe, i) {
    var intestazione = celle(righe[i]);
    var allinea = allineamenti(righe[i + 1]);
    var corpo = [];
    var j = i + 2;
    while (j < righe.length && righe[j].indexOf("|") !== -1 && righe[j].trim()) {
      corpo.push(celle(righe[j]));
      j++;
    }

    function cella(tag, testo, k) {
      var stile = allinea[k] ? ' style="text-align:' + allinea[k] + '"' : "";
      return "<" + tag + stile + ">" + inRiga(testo) + "</" + tag + ">";
    }

    var html = "<table><thead><tr>";
    intestazione.forEach(function (c, k) {
      html += cella("th", c, k);
    });
    html += "</tr></thead><tbody>";
    corpo.forEach(function (r) {
      html += "<tr>";
      // Una riga piu' corta dell'intestazione non e' un errore da nascondere:
      // si completa con celle vuote, cosi' la tabella resta leggibile e le
      // colonne restano allineate.
      for (var k = 0; k < intestazione.length; k++) {
        html += cella("td", r[k] === undefined ? "" : r[k], k);
      }
      html += "</tr>";
    });
    return [html + "</tbody></table>", j];
  }

  /* --------------------------------------------------------------- liste */

  function sfila(righe) {
    var minimo = Infinity;
    righe.forEach(function (r) {
      if (r.trim()) minimo = Math.min(minimo, larghezzaRientro(r.match(/^[ \t]*/)[0]));
    });
    if (!isFinite(minimo) || minimo === 0) return righe;
    return righe.map(function (r) {
      return r.replace(/^[ \t]*/, function (sp) {
        return " ".repeat(Math.max(0, larghezzaRientro(sp) - minimo));
      });
    });
  }

  function lista(righe, i) {
    var primo = VOCE.exec(righe[i]);
    var base = larghezzaRientro(primo[1]);
    var ordinata = /\d/.test(primo[2]);
    var voci = [];

    while (i < righe.length) {
      var riga = righe[i];
      var m = VOCE.exec(riga);

      if (m && larghezzaRientro(m[1]) <= base + 1) {
        if (larghezzaRientro(m[1]) < base) break;
        // Cambiare marcatore vuol dire cambiare lista: un elenco puntato
        // dentro a uno numerato e' un'altra cosa, non la stessa proseguita.
        if (/\d/.test(m[2]) !== ordinata) break;
        voci.push({ prima: m[3], figli: [] });
        i++;
        continue;
      }

      if (!voci.length) break;

      if (!riga.trim()) {
        // Una riga vuota chiude la lista solo se dopo non c'e' altro della
        // lista: fra due voci distanziate il vuoto e' spaziatura.
        var k = i + 1;
        while (k < righe.length && !righe[k].trim()) k++;
        if (k >= righe.length) break;
        var dopo = VOCE.exec(righe[k]);
        var rientroDopo = larghezzaRientro(righe[k].match(/^[ \t]*/)[0]);
        if (!(rientroDopo > base || (dopo && larghezzaRientro(dopo[1]) >= base))) break;
        voci[voci.length - 1].figli.push("");
        i++;
        continue;
      }

      if (larghezzaRientro(riga.match(/^[ \t]*/)[0]) > base) {
        voci[voci.length - 1].figli.push(riga);
        i++;
        continue;
      }
      break;
    }

    var tag = ordinata ? "ol" : "ul";
    var inizio = "";
    if (ordinata) {
      var n = parseInt(primo[2], 10);
      if (n !== 1) inizio = ' start="' + n + '"';
    }

    var html = "<" + tag + inizio + ">";
    voci.forEach(function (v) {
      var testo = v.prima;
      var classe = "";
      // Casella di spunta: si mostra il segno, non un comando. Un `<input>`
      // qui darebbe l'idea di poter spuntare la voce di un documento.
      var spunta = /^\[([ xX])\][ \t]+(.*)$/.exec(testo);
      if (spunta) {
        classe = ' class="md-spunta"';
        testo = (spunta[1] === " " ? "☐ " : "☑ ") + spunta[2];
      }
      html += "<li" + classe + ">" + inRiga(testo);
      if (v.figli.length) html += blocchi(sfila(v.figli));
      html += "</li>";
    });
    return [html + "</" + tag + ">", i];
  }

  /* -------------------------------------------------------------- blocchi */

  function apreUnBlocco(riga) {
    return (
      !riga.trim() ||
      TITOLO.test(riga) ||
      RIGA_ORIZZONTALE.test(riga) ||
      RECINTO.test(riga) ||
      VOCE.test(riga) ||
      CITAZIONE.test(riga)
    );
  }

  function blocchi(righe) {
    var fuori = "";
    var i = 0;

    while (i < righe.length) {
      var riga = righe[i];

      if (!riga.trim()) {
        i++;
        continue;
      }

      var rec = RECINTO.exec(riga);
      if (rec) {
        var dentro = [];
        var chiuso = false;
        i++;
        while (i < righe.length) {
          var fine = RECINTO.exec(righe[i]);
          if (fine && fine[2] === rec[2]) {
            chiuso = true;
            i++;
            break;
          }
          dentro.push(righe[i]);
          i++;
        }
        // Un recinto mai chiuso — capita con l'OCR — si rende comunque:
        // buttare via il resto del documento sarebbe peggio del difetto.
        var lingua = rec[3] ? ' class="lang-' + scappa(rec[3]) + '"' : "";
        fuori += "<pre><code" + lingua + ">" + scappa(dentro.join("\n")) + "</code></pre>";
        if (!chiuso) break;
        continue;
      }

      if (RIGA_ORIZZONTALE.test(riga)) {
        fuori += "<hr>";
        i++;
        continue;
      }

      var tit = TITOLO.exec(riga);
      if (tit) {
        var liv = tit[1].length;
        fuori += "<h" + liv + ">" + inRiga(tit[2]) + "</h" + liv + ">";
        i++;
        continue;
      }

      if (
        riga.indexOf("|") !== -1 &&
        i + 1 < righe.length &&
        SEPARATORE_TABELLA.test(righe[i + 1]) &&
        righe[i + 1].indexOf("-") !== -1
      ) {
        var esito = tabella(righe, i);
        fuori += esito[0];
        i = esito[1];
        continue;
      }

      if (CITAZIONE.test(riga)) {
        var dentroCit = [];
        while (i < righe.length && righe[i].trim()) {
          var c = CITAZIONE.exec(righe[i]);
          // Una riga senza «>» dentro una citazione ne fa parte comunque:
          // e' la continuazione, ed e' come la scrive quasi tutto il mondo.
          dentroCit.push(c ? c[1] : righe[i]);
          i++;
        }
        fuori += "<blockquote>" + blocchi(dentroCit) + "</blockquote>";
        continue;
      }

      if (VOCE.test(riga)) {
        var el = lista(righe, i);
        fuori += el[0];
        i = el[1];
        continue;
      }

      var paragrafo = [];
      while (i < righe.length && !apreUnBlocco(righe[i])) {
        paragrafo.push(righe[i].trim());
        i++;
      }
      if (paragrafo.length) {
        // Il ritorno a capo singolo e' uno spazio, come vuole Markdown: un
        // PDF va a capo dove finisce la riga sulla pagina, non dove finisce
        // la frase, e rispettarlo spezzerebbe ogni paragrafo.
        fuori += "<p>" + inRiga(paragrafo.join(" ")) + "</p>";
      } else {
        i++;
      }
    }

    return fuori;
  }

  function render(sorgente) {
    if (!sorgente) return "";
    return blocchi(String(sorgente).replace(/\r\n?/g, "\n").split("\n"));
  }

  var API = { render: render, scappa: scappa };

  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else globale.MrRaoMarkdown = API;
})(typeof globalThis !== "undefined" ? globalThis : this);
