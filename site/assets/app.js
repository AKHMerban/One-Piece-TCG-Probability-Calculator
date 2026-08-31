/* =====================================================================
   MOTEUR DE CALCUL — loi hypergeometrique (calcul en espace log pour
   eviter les overflows sur les grands deck).
   ===================================================================== */
const LN_FACT_MAX = 1000;
const LN_FACT = (() => {
  const arr = [0];
  let sum = 0;
  for (let i = 1; i <= LN_FACT_MAX; i++) { sum += Math.log(i); arr.push(sum); }
  return arr;
})();
function lnComb(n, k) {
  if (k < 0 || k > n || n < 0) return -Infinity;
  return LN_FACT[n] - LN_FACT[k] - LN_FACT[n - k];
}
function probaAuMoinsUne(N, K, n) {
  if (n > N || K > N || n < 0 || K < 0) throw new Error("Parametres invalides");
  if (n === 0 || K === 0) return 0;
  let probaAucune = 1;
  for (let i = 0; i < n; i++) probaAucune *= (N - K - i) / (N - i);
  return (1 - probaAucune) * 100;
}
function probaCombo(N, cartes, n) {
  const totalK = cartes.reduce((s, c) => s + c[0], 0);
  if (totalK > N || n > N || n < 0) throw new Error("Parametres invalides");
  const autres = N - totalK;
  const lnDenom = lnComb(N, n);
  let total = 0;
  (function recurse(idx, sumA, lnWaysSoFar) {
    if (idx === cartes.length) {
      const reste = n - sumA;
      if (reste < 0 || reste > autres) return;
      total += Math.exp(lnWaysSoFar + lnComb(autres, reste) - lnDenom);
      return;
    }
    const k = cartes[idx][0], r = cartes[idx][1];
    for (let a = r; a <= k; a++) recurse(idx + 1, sumA + a, lnWaysSoFar + lnComb(k, a));
  })(0, 0, 0);
  return total * 100;
}
function cartesVuesParTour(hand, position, maxTurn = 10) {
  const turns = [], vues = [];
  for (let t = 1; t <= maxTurn; t++) {
    turns.push(t);
    vues.push(hand + (position === "p1" ? Math.max(0, t - 1) : t));
  }
  return { turns, vues };
}
function donDisponibleParTour(position, maxTurn = 10) {
  const dons = [];
  for (let t = 1; t <= maxTurn; t++) {
    dons.push(position === "p1" ? Math.min(1 + 2 * (t - 1), 10) : Math.min(2 * t, 10));
  }
  return dons;
}
function parsePoints(text) {
  return text.split(",").map(s => s.trim()).filter(Boolean).map(Number).filter(n => !isNaN(n));
}

/* =====================================================================
   MINI-MOTEUR DE GRAPHIQUE (canvas natif, sans dependance externe)
   ===================================================================== */
const CHART_COLORS = ["#D9A93B", "#5B9BD5", "#C1453A", "#4A9B6E", "#A47FDB"];

function drawLineChart(canvas, series, xLabels, opts = {}) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 900, cssH = parseInt(canvas.getAttribute("height")) || 220;
  canvas.width = cssW * dpr; canvas.height = cssH * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const W = cssW, H = cssH;
  ctx.clearRect(0, 0, W, H);

  const yMax = opts.yMax || 100;
  const padL = 42, padR = 16, padT = 26, padB = 30;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const n = xLabels.length;
  const stepX = n > 1 ? plotW / (n - 1) : 0;

  ctx.strokeStyle = "#2C5580"; ctx.lineWidth = 1;
  ctx.font = "11px Inter, sans-serif";
  for (let i = 0; i <= 4; i++) {
    const val = yMax * i / 4;
    const y = padT + plotH - (val / yMax) * plotH;
    ctx.strokeStyle = "rgba(159,182,204,0.15)";
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + plotW, y); ctx.stroke();
    ctx.fillStyle = "#9FB6CC"; ctx.textAlign = "right"; ctx.textBaseline = "middle";
    ctx.fillText((opts.yFormat ? opts.yFormat(val) : Math.round(val)), padL - 8, y);
  }
  ctx.strokeStyle = "#2C5580";
  ctx.beginPath(); ctx.moveTo(padL, padT); ctx.lineTo(padL, padT + plotH); ctx.lineTo(padL + plotW, padT + plotH); ctx.stroke();

  ctx.fillStyle = "#9FB6CC"; ctx.textAlign = "center"; ctx.textBaseline = "top";
  const labelEvery = Math.max(1, Math.ceil(n / 12));
  xLabels.forEach((lab, i) => {
    if (i % labelEvery === 0 || n <= 12) {
      const x = padL + (n > 1 ? i * stepX : plotW / 2);
      ctx.fillText(String(lab), x, padT + plotH + 6);
    }
  });

  series.forEach((s, si) => {
    const color = s.color || CHART_COLORS[si % CHART_COLORS.length];
    ctx.strokeStyle = color; ctx.lineWidth = 2;
    ctx.beginPath();
    s.data.forEach((v, i) => {
      const x = padL + (n > 1 ? i * stepX : plotW / 2);
      const y = padT + plotH - (Math.min(v, yMax) / yMax) * plotH;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.fillStyle = color;
    s.data.forEach((v, i) => {
      const x = padL + (n > 1 ? i * stepX : plotW / 2);
      const y = padT + plotH - (Math.min(v, yMax) / yMax) * plotH;
      ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
    });
  });

  if (series.length > 1 || (series[0] && series[0].label)) {
    ctx.textAlign = "left"; ctx.textBaseline = "middle"; ctx.font = "11px Inter, sans-serif";
    let lx = padL, ly = 12;
    series.forEach((s, si) => {
      const color = s.color || CHART_COLORS[si % CHART_COLORS.length];
      ctx.fillStyle = color; ctx.fillRect(lx, ly - 5, 10, 10);
      ctx.fillStyle = "#EAF1F8"; ctx.fillText(s.label, lx + 14, ly);
      lx += ctx.measureText(s.label).width + 34;
    });
  }
}

/* =====================================================================
   HELPERS UI PARTAGES : position + cartes vues, tableau HTML
   ===================================================================== */
function wirePositionBlock(prefix, handInputId) {
  const radios = document.querySelectorAll(`input[name="${prefix}-position"]`);
  const pointsInput = document.getElementById(`${prefix}-points`);
  const pointsLabel = document.getElementById(`${prefix}-points-label`);
  radios.forEach(r => r.addEventListener("change", () => {
    const pos = document.querySelector(`input[name="${prefix}-position"]:checked`).value;
    if (pos === "manuel") {
      pointsInput.disabled = false;
      pointsLabel.textContent = "Cartes vues (séparées par des virgules)";
    } else {
      const hand = parseInt(document.getElementById(handInputId).value) || 5;
      const { vues } = cartesVuesParTour(hand, pos);
      pointsInput.value = vues.join(",");
      pointsInput.disabled = true;
      pointsLabel.textContent = "Cartes vues par tour (1 à 10, calculé auto)";
    }
  }));
}

function renderTable(container, columns, rows) {
  let html = "<table><thead><tr>";
  columns.forEach(c => html += `<th>${c}</th>`);
  html += "</tr></thead><tbody>";
  rows.forEach(r => {
    html += "<tr>" + r.map(v => `<td>${v}</td>`).join("") + "</tr>";
  });
  html += "</tbody></table>";
  container.innerHTML = html;
}

function getCheckedValues(containerId) {
  return Array.from(document.querySelectorAll(`#${containerId} input:checked`)).map(el => parseInt(el.value));
}

/* =====================================================================
   TAB 1 : STANDARD
   ===================================================================== */
function calcStandard() {
  const N = parseInt(document.getElementById("std-deck").value);
  const points = parsePoints(document.getElementById("std-points").value);
  const copies = getCheckedValues("std-copies");
  if (!copies.length || !points.length) return;
  if (Math.max(...points) > N) { alert("Le nombre de cartes vues ne peut pas dépasser la taille du deck."); return; }

  const results = {};
  copies.forEach(K => { results[K] = points.map(n => probaAuMoinsUne(N, K, n)); });

  const cols = ["Cartes vues", ...copies.map(k => `${k}x dans le deck`)];
  const rows = points.map((n, i) => [n, ...copies.map(k => results[k][i].toFixed(1) + "%")]);
  renderTable(document.getElementById("std-table"), cols, rows);

  const series = copies.map(k => ({ label: `${k} copies dans le deck`, data: results[k] }));
  drawLineChart(document.getElementById("std-chart"), series, points, { yMax: 100 });
}

/* =====================================================================
   TAB 2 : VIE DU LEADER
   ===================================================================== */
function calcVie() {
  const Ndeck = parseInt(document.getElementById("vie-deck").value);
  const life = parseInt(document.querySelector('input[name="vie-life"]:checked').value);
  const N = Ndeck - life;
  const effEl = document.getElementById("vie-effectif");
  if (N <= 0) { effEl.textContent = "Erreur : la vie du leader dépasse la taille du deck."; return; }
  effEl.textContent = `→ Deck effectif (piochable) : ${Ndeck} - ${life} (cartes de vie) = ${N} cartes`;

  const position = document.querySelector('input[name="vie-position"]:checked').value;
  const points = parsePoints(document.getElementById("vie-points").value);
  const copies = getCheckedValues("vie-copies");
  if (!copies.length || !points.length) return;
  if (Math.max(...points) > N) { alert("Le nombre de cartes vues dépasse le deck effectif."); return; }

  const turns = (position === "p1" || position === "p2") ? points.map((_, i) => i + 1) : null;
  const results = {};
  copies.forEach(K => { results[K] = points.map(n => probaAuMoinsUne(N, K, n)); });

  const showTurn = !!turns;
  const cols = [...(showTurn ? ["Tour"] : []), "Cartes vues", ...copies.map(k => `${k}x dans le deck`)];
  const rows = points.map((n, i) => [
    ...(showTurn ? [turns[i]] : []), n, ...copies.map(k => results[k][i].toFixed(1) + "%")
  ]);
  renderTable(document.getElementById("vie-table"), cols, rows);

  const xaxis = document.querySelector('input[name="vie-xaxis"]:checked').value;
  const useTurnAxis = xaxis === "tour" && showTurn;
  const xLabels = useTurnAxis ? turns : points;
  const series = copies.map(k => ({ label: `${k} copies dans le deck`, data: results[k] }));
  drawLineChart(document.getElementById("vie-chart"), series, xLabels, { yMax: 100 });
}

/* =====================================================================
   TAB 3 : DON!!
   ===================================================================== */
function calcDon() {
  const Ndeck = parseInt(document.getElementById("don-deck").value);
  const life = parseInt(document.querySelector('input[name="don-life"]:checked').value);
  const N = Ndeck - life;
  if (N <= 0) { alert("La vie du leader dépasse la taille du deck."); return; }

  const K = parseInt(document.querySelector('input[name="don-copies"]:checked').value);
  const cost = parseInt(document.getElementById("don-cost").value);
  const reserveOn = document.getElementById("don-reserve-check").checked;
  const reserve = reserveOn ? parseInt(document.getElementById("don-reserve").value) : 0;
  const position = document.querySelector('input[name="don-position"]:checked').value;
  const hand = 5;

  const turns = Array.from({length:10}, (_,i)=>i+1);
  const donDispo = donDisponibleParTour(position);
  const cartesVues = turns.map(t => Math.min(hand + (position === "p1" ? Math.max(0, t-1) : t), N));
  const probas = cartesVues.map(n => probaAuMoinsUne(N, K, n));
  const seuil = cost + reserve;
  const jouable = donDispo.map(d => d >= seuil);
  const tourIdeal = turns.find((t, i) => jouable[i]) || null;

  const cols = ["Tour", "DON!! dispo", "Cartes vues", "Proba d'avoir la carte en main", "Jouable ce tour ?"];
  const rows = turns.map((t, i) => [t, donDispo[i], cartesVues[i], probas[i].toFixed(1) + "%", jouable[i] ? "Oui" : "Non"]);
  renderTable(document.getElementById("don-table"), cols, rows);

  const resultEl = document.getElementById("don-result");
  if (tourIdeal) {
    const p = probas[tourIdeal - 1];
    const extra = reserve ? ` (en gardant ${reserve} DON!! de réserve)` : "";
    resultEl.textContent = `→ Tour idéal pour jouer cette carte à ${cost} DON!!${extra} : Tour ${tourIdeal} (${donDispo[tourIdeal-1]} DON!! disponibles). Probabilité de l'avoir déjà piochée à ce tour : ${p.toFixed(1)}%.`;
  } else {
    resultEl.textContent = `→ Avec un coût de ${cost} + ${reserve} de réserve = ${seuil} DON!!, ce n'est jouable à aucun tour dans les 10 premiers tours.`;
  }

  drawLineChart(document.getElementById("don-chart-1"), [{ label: "DON!! disponible", data: donDispo, color: "#C1453A" }], turns, { yMax: 10 });
  drawLineChart(document.getElementById("don-chart-2"), [{ label: "Proba carte en main (%)", data: probas, color: "#5B9BD5" }], turns, { yMax: 100 });
}

/* =====================================================================
   TAB 4 : EFFETS SUPPLEMENTAIRES
   ===================================================================== */
let effEffects = [];
/* Cellule « supprimer la ligne », partagee par les tableaux des onglets
   Effets et Combinaisons. La classe porte le style : aucun attribut style
   dans le balisage, ce qui permet une CSP sans 'unsafe-inline'. */
function makeRemoveCell(idx) {
  const td = document.createElement("td");
  const btn = document.createElement("button");
  btn.className = "btn secondary btn-xs";
  btn.dataset.idx = idx;
  btn.textContent = "✕";
  btn.setAttribute("aria-label", "Supprimer cette ligne");
  td.appendChild(btn);
  return td;
}

function refreshEffectsTable() {
  const tbody = document.querySelector("#eff-list-table tbody");
  tbody.innerHTML = "";
  effEffects.forEach((e, i) => {
    const cartes = e.valeur * e.uses;
    const tr = document.createElement("tr");
    // textContent, jamais innerHTML : les libelles passent par le DOM sans
    // etre reinterpretes comme du HTML.
    [e.typeLabel, e.valeur, e.uses, cartes].forEach(v => {
      const td = document.createElement("td");
      td.textContent = v;
      tr.appendChild(td);
    });
    tr.appendChild(makeRemoveCell(i));
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    effEffects.splice(parseInt(b.dataset.idx), 1);
    refreshEffectsTable();
    calcEffets();
  }));
  const total = effEffects.reduce((s, e) => s + e.valeur * e.uses, 0);
  document.getElementById("eff-total").textContent = `Total cartes ajoutées par les effets : ${total}`;
}
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("eff-add").addEventListener("click", () => {
    const typeSel = document.getElementById("eff-type");
    effEffects.push({
      typeLabel: typeSel.options[typeSel.selectedIndex].text,
      valeur: parseInt(document.getElementById("eff-valeur").value),
      uses: parseInt(document.getElementById("eff-uses").value),
    });
    refreshEffectsTable();
    calcEffets();
  });
});

function calcEffets() {
  const Ndeck = parseInt(document.getElementById("eff-deck").value);
  const life = parseInt(document.querySelector('input[name="eff-life"]:checked').value);
  const N = Ndeck - life;
  const effEl = document.getElementById("eff-effectif");
  if (N <= 0) { effEl.textContent = "Erreur : la vie du leader dépasse la taille du deck."; return; }
  effEl.textContent = `→ Deck effectif (piochable) : ${Ndeck} - ${life} (cartes de vie) = ${N} cartes`;

  const basePoints = parsePoints(document.getElementById("eff-points").value);
  const copies = getCheckedValues("eff-copies");
  if (!copies.length || !basePoints.length) return;

  const extra = effEffects.reduce((s, e) => s + e.valeur * e.uses, 0);
  const position = document.querySelector('input[name="eff-position"]:checked').value;
  const turns = (position === "p1" || position === "p2") ? basePoints.map((_, i) => i + 1) : null;
  const totalPoints = basePoints.map(n => Math.min(n + extra, N));

  const results = {};
  copies.forEach(K => { results[K] = totalPoints.map(n => probaAuMoinsUne(N, K, n)); });

  const showTurn = !!turns;
  const cols = [...(showTurn ? ["Tour"] : []), "Cartes vues (base)", "+ Effets", "Total vues", ...copies.map(k => `${k}x dans le deck`)];
  const rows = basePoints.map((n, i) => [
    ...(showTurn ? [turns[i]] : []), n, extra, totalPoints[i], ...copies.map(k => results[k][i].toFixed(1) + "%")
  ]);
  renderTable(document.getElementById("eff-table"), cols, rows);

  const xaxis = document.querySelector('input[name="eff-xaxis"]:checked').value;
  const useTurnAxis = xaxis === "tour" && showTurn;
  const xLabels = useTurnAxis ? turns : totalPoints;
  const series = copies.map(k => ({ label: `${k} copies dans le deck`, data: results[k] }));
  drawLineChart(document.getElementById("eff-chart"), series, xLabels, { yMax: 100 });
}

/* =====================================================================
   TAB 5 : COMBINAISONS
   ===================================================================== */
let comboCards = [];
function refreshComboTable() {
  const tbody = document.querySelector("#combo-list-table tbody");
  tbody.innerHTML = "";
  comboCards.forEach((c, i) => {
    const tr = document.createElement("tr");
    // c.nom est saisi par l'utilisateur ou vient de l'API optcgapi.com :
    // ces deux sources sont hors de notre controle, donc jamais d'innerHTML.
    [c.nom, c.copies, c.minimum].forEach(v => {
      const td = document.createElement("td");
      td.textContent = v;
      tr.appendChild(td);
    });
    tr.appendChild(makeRemoveCell(i));
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    comboCards.splice(parseInt(b.dataset.idx), 1);
    refreshComboTable();
    calcCombo();
  }));
}
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("combo-add").addEventListener("click", () => {
    if (comboCards.length >= 5) { alert("Maximum 5 cartes dans une combinaison."); return; }
    const copies = parseInt(document.getElementById("combo-copies").value);
    const minimum = parseInt(document.getElementById("combo-min").value);
    if (minimum > copies) { alert("Le minimum requis ne peut pas dépasser le nombre de copies dans le deck."); return; }
    const nom = document.getElementById("combo-name").value.trim() || `Carte ${comboCards.length + 1}`;
    comboCards.push({ nom, copies, minimum });
    refreshComboTable();
    document.getElementById("combo-name").value = "";
    calcCombo();
  });
});

function calcCombo() {
  const Ndeck = parseInt(document.getElementById("combo-deck").value);
  const life = parseInt(document.querySelector('input[name="combo-life"]:checked').value);
  const N = Ndeck - life;
  const effEl = document.getElementById("combo-effectif");
  if (N <= 0) { effEl.textContent = "Erreur : la vie du leader dépasse la taille du deck."; return; }
  effEl.textContent = `→ Deck effectif (piochable) : ${Ndeck} - ${life} (cartes de vie) = ${N} cartes`;

  const summaryEl = document.getElementById("combo-summary");
  if (comboCards.length < 1) {
    summaryEl.textContent = "Ajoute au moins une carte pour lancer le calcul (2+ pour une vraie combinaison).";
    document.getElementById("combo-table").innerHTML = "";
    const c = document.getElementById("combo-chart");
    c.getContext("2d").clearRect(0, 0, c.width, c.height);
    return;
  }
  const totalK = comboCards.reduce((s, c) => s + c.copies, 0);
  if (totalK > N) { alert("Le total de copies des cartes sélectionnées dépasse le deck effectif."); return; }
  summaryEl.textContent = `${comboCards.length} carte(s) — ${totalK} copies au total utilisées sur ${N} cartes du deck effectif.`;

  let points = parsePoints(document.getElementById("combo-points").value).filter(n => n <= N);
  if (!points.length) { alert("Aucun point de pioche valide."); return; }

  const position = document.querySelector('input[name="combo-position"]:checked').value;
  const turns = (position === "p1" || position === "p2") ? points.map((_, i) => i + 1) : null;

  const cartesCombo = comboCards.map(c => [c.copies, c.minimum]);
  const probas = points.map(n => probaCombo(N, cartesCombo, n));

  const showTurn = !!turns;
  const cols = ["Tour", "Cartes vues", "Probabilité de la combinaison"];
  const rows = points.map((n, i) => [showTurn ? turns[i] : "-", n, probas[i].toFixed(1) + "%"]);
  renderTable(document.getElementById("combo-table"), cols, rows);

  const xaxis = document.querySelector('input[name="combo-xaxis"]:checked').value;
  const useTurnAxis = xaxis === "tour" && showTurn;
  const xLabels = useTurnAxis ? turns : points;
  const label = comboCards.map(c => `${c.minimum}x ${c.nom}`).join(" + ");
  drawLineChart(document.getElementById("combo-chart"), [{ label, data: probas, color: "#A47FDB" }], xLabels, { yMax: 100 });
}

/* =====================================================================
   RECHERCHE DE CARTE (API optcgapi.com, avec repli gracieux)
   ===================================================================== */
let cardDatabase = null;
let cardDatabaseError = null;
async function loadCardDatabase() {
  if (cardDatabase || cardDatabaseError) return;
  try {
    const res = await fetch("https://optcgapi.com/api/allSetCards/");
    if (!res.ok) throw new Error("HTTP " + res.status);
    cardDatabase = await res.json();
  } catch (err) {
    cardDatabaseError = err;
    console.warn("Recherche de carte indisponible :", err);
  }
}
function wireCardSearch(inputId, resultsId, statusId, onPick) {
  const input = document.getElementById(inputId);
  const resultsEl = document.getElementById(resultsId);
  const statusEl = document.getElementById(statusId);
  let debounceTimer = null;

  input.addEventListener("focus", () => loadCardDatabase());
  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      const q = input.value.trim().toLowerCase();
      if (q.length < 2) { resultsEl.style.display = "none"; return; }
      if (!cardDatabase && !cardDatabaseError) {
        statusEl.textContent = "Chargement de la base de cartes...";
        await loadCardDatabase();
      }
      if (cardDatabaseError) {
        statusEl.textContent = "Recherche indisponible (pas de connexion ou API hors-service) — utilise la saisie manuelle.";
        resultsEl.style.display = "none";
        return;
      }
      statusEl.textContent = "";
      const matches = cardDatabase
        .filter(c => c.card_name && c.card_name.toLowerCase().includes(q) && c.card_type !== "Leader")
        .slice(0, 15);
      if (!matches.length) { resultsEl.style.display = "none"; return; }
      resultsEl.innerHTML = "";
      matches.forEach(c => {
        const div = document.createElement("div");
        const costTxt = c.card_cost !== null && c.card_cost !== undefined ? ` — Coût ${c.card_cost}` : "";
        div.textContent = `${c.card_name} (${c.card_set_id})${costTxt}`;
        div.addEventListener("click", () => {
          onPick(c);
          resultsEl.style.display = "none";
          input.value = c.card_name;
        });
        resultsEl.appendChild(div);
      });
      resultsEl.style.display = "block";
    }, 250);
  });
  document.addEventListener("click", (e) => {
    if (!resultsEl.contains(e.target) && e.target !== input) resultsEl.style.display = "none";
  });
}

/* =====================================================================
   INITIALISATION
   ===================================================================== */
document.addEventListener("DOMContentLoaded", () => {
  // Navigation par onglets
  document.querySelectorAll("nav.tabs button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("nav.tabs button").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
  });

  // Blocs position/cartes-vues partages
  wirePositionBlock("vie", "vie-hand");
  wirePositionBlock("eff", "eff-hand");
  wirePositionBlock("combo", "combo-hand");

  // Boutons Calculer
  document.getElementById("std-calc").addEventListener("click", calcStandard);
  document.getElementById("vie-calc").addEventListener("click", calcVie);
  document.getElementById("don-calc").addEventListener("click", calcDon);
  document.getElementById("eff-calc").addEventListener("click", calcEffets);
  document.getElementById("combo-calc").addEventListener("click", calcCombo);

  // Recalcul auto sur changement de radio/checkbox simples
  ["vie-life","vie-xaxis","vie-copies","don-life","don-position","don-copies",
   "eff-life","eff-xaxis","eff-copies","combo-life","combo-xaxis"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", () => {});
  });
  document.querySelectorAll('#vie-life input, #vie-xaxis input, #vie-copies input').forEach(el => el.addEventListener("change", calcVie));
  document.querySelectorAll('#don-life input, #don-position input, #don-copies input, #don-reserve-check').forEach(el => el.addEventListener("change", calcDon));
  document.getElementById("don-reserve").addEventListener("change", calcDon);
  document.querySelectorAll('#eff-life input, #eff-xaxis input, #eff-copies input').forEach(el => el.addEventListener("change", calcEffets));
  document.querySelectorAll('#combo-life input, #combo-xaxis input').forEach(el => el.addEventListener("change", calcCombo));

  // Recherche de carte
  wireCardSearch("don-search", "don-search-results", "don-search-status", (card) => {
    if (card.card_cost !== null && card.card_cost !== undefined) {
      document.getElementById("don-cost").value = card.card_cost;
    }
  });
  wireCardSearch("combo-name", "combo-search-results", "combo-search-status", (card) => {
    // nom deja rempli par le clic ; rien d'autre a prerempler (copies/minimum restent au choix du joueur)
  });

  // Calcul initial de tous les onglets
  calcStandard();
  calcVie();
  calcDon();
  refreshEffectsTable();
  calcEffets();
  refreshComboTable();
  calcCombo();
});
