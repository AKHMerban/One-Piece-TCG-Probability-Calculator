/* =====================================================================
   BASE DE CARTES — recherche, filtres et fiches

   Les donnees viennent de /data/cards.json, construit par
   tools/scrape-cards.py depuis le site officiel du jeu. Une entree par
   numero de carte : les parallales sont repliees sur leur carte de base,
   puisqu'elles ne different que par l'artwork.

   Le fichier fait environ 1,8 Mo. Il n'est donc PAS charge au demarrage :
   il l'est a la premiere ouverture de l'onglet Cartes, ou au premier
   caractere tape dans une des recherches des autres onglets.
   ===================================================================== */

const CARD_DATA_URL = "/data/cards.json";
const CARD_IMAGE_BASE = "/cards/";
const PAGE_SIZE = 48;

const CardDB = (() => {
  let data = null;
  let error = null;
  let promise = null;

  /* Chaine de recherche precalculee : nom FR, nom EN, numero, types et
     texte d'effet dans les deux langues. Un joueur cherche indifferemment
     « Zoro », « OP01-025 » ou « blocker », et souvent avec le nom anglais
     meme sur une interface francaise. */
  function buildIndex(cards) {
    for (const c of cards) {
      const parts = [c.number];
      for (const loc of ["fr", "en"]) {
        const l = c[loc];
        if (!l) continue;
        if (l.name) parts.push(l.name);
        if (l.types && l.types.length) parts.push(l.types.join(" "));
        if (l.effect) parts.push(l.effect);
        if (l.set) parts.push(l.set);
      }
      c._h = parts.join(" ").toLowerCase();
    }
  }

  function load() {
    if (promise) return promise;
    promise = fetch(CARD_DATA_URL)
      .then(res => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(payload => {
        buildIndex(payload.cards);
        data = payload;
        return payload;
      })
      .catch(err => {
        error = err;
        console.warn("Base de cartes indisponible :", err);
        throw err;
      });
    return promise;
  }

  return {
    load,
    get ready() { return data !== null; },
    get failed() { return error !== null; },
    get all() { return data ? data.cards : []; },
    get generated() { return data ? data.generated : null; },
    get count() { return data ? data.count : 0; },
  };
})();

/* --------------------------------------------------------------------
   Helpers de presentation
   -------------------------------------------------------------------- */

let displayLang = "fr";

function loc(card, lang) {
  const wanted = lang || displayLang;
  return card[wanted] || card.fr || card.en || {};
}

/* Vrai quand la carte n'existe pas dans la langue demandee : l'interface
   le signale plutot que d'afficher silencieusement une autre langue. */
function isFallback(card, lang) {
  const wanted = lang || displayLang;
  return !card[wanted];
}

function cardName(card, lang) {
  return loc(card, lang).name || card.number;
}

const CATEGORY_LABELS = {
  LEADER: "Leader",
  CHARACTER: "Personnage",
  EVENT: "Événement",
  STAGE: "Stage",
};

const COLOR_LABELS = {
  Red: "Rouge", Green: "Vert", Blue: "Bleu",
  Purple: "Violet", Black: "Noir", Yellow: "Jaune",
};

function colorLabel(c) { return COLOR_LABELS[c] || c; }

function fmt(value, suffix) {
  if (value === null || value === undefined) return "—";
  return suffix ? value + suffix : String(value);
}

/* --------------------------------------------------------------------
   Onglet Cartes
   -------------------------------------------------------------------- */

let filtered = [];
let shown = 0;

function cardsEls() {
  return {
    q: document.getElementById("cards-q"),
    color: document.getElementById("cards-color"),
    cat: document.getElementById("cards-cat"),
    cost: document.getElementById("cards-cost"),
    set: document.getElementById("cards-set"),
    attr: document.getElementById("cards-attr"),
    results: document.getElementById("cards-results"),
    status: document.getElementById("cards-status"),
    more: document.getElementById("cards-more"),
  };
}

function fillSelect(select, values, allLabel) {
  select.innerHTML = "";
  const opt = document.createElement("option");
  opt.value = "";
  opt.textContent = allLabel;
  select.appendChild(opt);
  for (const v of values) {
    const o = document.createElement("option");
    o.value = v.value;
    o.textContent = v.label;
    select.appendChild(o);
  }
}

function buildFilters() {
  const els = cardsEls();
  const cards = CardDB.all;

  const colors = [...new Set(cards.flatMap(c => c.colors))].sort();
  fillSelect(els.color, colors.map(c => ({ value: c, label: colorLabel(c) })),
             "Toutes");

  const cats = [...new Set(cards.map(c => c.category).filter(Boolean))].sort();
  fillSelect(els.cat, cats.map(c => ({ value: c, label: CATEGORY_LABELS[c] || c })),
             "Toutes");

  const costs = [...new Set(cards.map(c => c.cost).filter(v => v !== null))]
    .sort((a, b) => a - b);
  fillSelect(els.cost, costs.map(c => ({ value: String(c), label: String(c) })),
             "Tous");

  const attrs = [...new Set(cards.map(c => c.attribute).filter(Boolean))].sort();
  fillSelect(els.attr, attrs.map(a => ({ value: a, label: a })), "Tous");

  /* Les extensions sont regroupees par leur code entre crochets — le nom
     complet change d'une langue a l'autre, pas le code. */
  const sets = new Map();
  for (const c of cards) {
    const label = (c.en && c.en.set) || (c.fr && c.fr.set);
    if (!label) continue;
    const m = label.match(/\[([^\]]+)\]\s*$/);
    const key = m ? m[1] : label;
    if (!sets.has(key)) sets.set(key, label);
  }
  const setOptions = [...sets.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([key, label]) => ({ value: key, label: `${key} — ${label.replace(/\s*\[[^\]]+\]\s*$/, "")}` }));
  fillSelect(els.set, setOptions, "Toutes");
}

function applyFilters() {
  const els = cardsEls();
  const q = els.q.value.trim().toLowerCase();
  const color = els.color.value;
  const cat = els.cat.value;
  const cost = els.cost.value;
  const set = els.set.value;
  const attr = els.attr.value;

  filtered = CardDB.all.filter(c => {
    if (q && !c._h.includes(q)) return false;
    if (color && !c.colors.includes(color)) return false;
    if (cat && c.category !== cat) return false;
    if (cost !== "" && String(c.cost) !== cost) return false;
    if (attr && c.attribute !== attr) return false;
    if (set) {
      const label = (c.en && c.en.set) || (c.fr && c.fr.set) || "";
      const m = label.match(/\[([^\]]+)\]\s*$/);
      if ((m ? m[1] : label) !== set) return false;
    }
    return true;
  });

  shown = 0;
  els.results.innerHTML = "";
  renderMore();

  const total = CardDB.count;
  els.status.textContent = filtered.length === total
    ? `${total} cartes dans la base — mise à jour du ${CardDB.generated}.`
    : `${filtered.length} carte${filtered.length > 1 ? "s" : ""} sur ${total}.`;
}

function renderMore() {
  const els = cardsEls();
  const slice = filtered.slice(shown, shown + PAGE_SIZE);
  const frag = document.createDocumentFragment();
  for (const card of slice) frag.appendChild(renderCard(card));
  els.results.appendChild(frag);
  shown += slice.length;
  els.more.classList.toggle("is-hidden", shown >= filtered.length);
  els.more.textContent = `Voir ${Math.min(PAGE_SIZE, filtered.length - shown)} cartes de plus`;
}

function renderCard(card) {
  const l = loc(card);
  const art = document.createElement("article");
  art.className = "card-tile";

  const img = document.createElement("img");
  img.className = "card-art";
  img.loading = "lazy";
  img.decoding = "async";
  img.width = 600;
  img.height = 838;
  img.src = CARD_IMAGE_BASE + card.id + ".webp";
  img.alt = cardName(card);
  art.appendChild(img);

  const body = document.createElement("div");
  body.className = "card-tile-body";

  const h = document.createElement("h3");
  h.className = "card-tile-name";
  h.textContent = l.name || card.number;
  body.appendChild(h);

  const meta = document.createElement("p");
  meta.className = "card-tile-meta";
  meta.textContent = [
    card.number,
    card.rarity,
    CATEGORY_LABELS[card.category] || card.category,
  ].filter(Boolean).join(" · ");
  body.appendChild(meta);

  const stats = document.createElement("dl");
  stats.className = "card-stats";
  const rows = [];
  if (card.life !== null && card.life !== undefined) rows.push(["Vie", fmt(card.life)]);
  if (card.cost !== null && card.cost !== undefined) rows.push(["Coût", fmt(card.cost)]);
  if (card.power !== null) rows.push(["Puissance", fmt(card.power)]);
  if (card.counter !== null) rows.push(["Contre", fmt(card.counter)]);
  if (card.colors.length) rows.push(["Couleur", card.colors.map(colorLabel).join(" / ")]);
  if (card.attribute) rows.push(["Attribut", card.attribute]);
  for (const [k, v] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = k;
    const dd = document.createElement("dd");
    dd.textContent = v;
    stats.appendChild(dt);
    stats.appendChild(dd);
  }
  body.appendChild(stats);

  if (l.types && l.types.length) {
    const types = document.createElement("p");
    types.className = "card-tile-types";
    types.textContent = l.types.join(" / ");
    body.appendChild(types);
  }

  if (l.effect) {
    const eff = document.createElement("p");
    eff.className = "card-tile-effect";
    eff.textContent = l.effect;
    body.appendChild(eff);
  }

  const foot = document.createElement("p");
  foot.className = "card-tile-set";
  foot.textContent = l.set || "";
  if (isFallback(card)) {
    const warn = document.createElement("span");
    warn.className = "card-tile-lang";
    warn.textContent = displayLang === "fr" ? "en anglais" : "en français";
    warn.title = "Cette carte n'est pas encore parue dans cette langue.";
    foot.appendChild(document.createTextNode(" "));
    foot.appendChild(warn);
  }
  body.appendChild(foot);

  art.appendChild(body);
  return art;
}

/* --------------------------------------------------------------------
   Recherche compacte, reutilisee par les onglets Coût DON!! et Combinaisons
   -------------------------------------------------------------------- */

function wireCardPicker(inputId, resultsId, statusId, onPick) {
  const input = document.getElementById(inputId);
  const resultsEl = document.getElementById(resultsId);
  const statusEl = document.getElementById(statusId);
  if (!input || !resultsEl || !statusEl) return;

  let timer = null;

  function close() {
    resultsEl.innerHTML = "";
    resultsEl.classList.add("is-hidden");
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim().toLowerCase();
    if (q.length < 2) { close(); statusEl.textContent = ""; return; }

    timer = setTimeout(() => {
      statusEl.textContent = CardDB.ready ? "" : "Chargement de la base de cartes…";
      CardDB.load().then(() => {
        statusEl.textContent = "";
        const matches = CardDB.all
          .filter(c => c.category !== "LEADER" && c._h.includes(q))
          .slice(0, 15);
        if (!matches.length) { close(); return; }

        resultsEl.innerHTML = "";
        for (const c of matches) {
          const div = document.createElement("div");
          const cost = c.cost !== null && c.cost !== undefined ? ` — Coût ${c.cost}` : "";
          div.textContent = `${cardName(c)} (${c.number})${cost}`;
          div.addEventListener("click", () => {
            onPick(c);
            input.value = cardName(c);
            close();
          });
          resultsEl.appendChild(div);
        }
        resultsEl.classList.remove("is-hidden");
      }).catch(() => {
        statusEl.textContent =
          "Recherche indisponible (base de cartes injoignable) — utilise la saisie manuelle.";
        close();
      });
    }, 200);
  });

  document.addEventListener("click", (e) => {
    if (!resultsEl.contains(e.target) && e.target !== input) close();
  });
}

/* --------------------------------------------------------------------
   Initialisation
   -------------------------------------------------------------------- */

let cardsTabReady = false;

function initCardsTab() {
  if (cardsTabReady) return;
  cardsTabReady = true;

  const els = cardsEls();
  els.status.textContent = "Chargement de la base de cartes…";

  CardDB.load().then(() => {
    buildFilters();
    applyFilters();
  }).catch(() => {
    els.status.textContent =
      "La base de cartes n'a pas pu être chargée. Recharge la page pour réessayer.";
  });

  let timer = null;
  els.q.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => { if (CardDB.ready) applyFilters(); }, 180);
  });
  for (const sel of [els.color, els.cat, els.cost, els.set, els.attr]) {
    sel.addEventListener("change", () => { if (CardDB.ready) applyFilters(); });
  }
  els.more.addEventListener("click", renderMore);

  document.querySelectorAll('input[name="cards-lang"]').forEach(radio => {
    radio.addEventListener("change", () => {
      displayLang = radio.value;
      if (CardDB.ready) applyFilters();
    });
  });

  document.getElementById("cards-reset").addEventListener("click", () => {
    els.q.value = "";
    for (const sel of [els.color, els.cat, els.cost, els.set, els.attr]) sel.value = "";
    if (CardDB.ready) applyFilters();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const tabBtn = document.querySelector('nav.tabs button[data-tab="cartes"]');
  if (tabBtn) tabBtn.addEventListener("click", initCardsTab);
});
