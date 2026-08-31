#!/usr/bin/env python3
"""
Construit la base de cartes du One Piece Card Game a partir du site officiel.

Source : https://en.onepiece-cardgame.com/cardlist/  (catalogue complet)
         https://fr.onepiece-cardgame.com/cardlist/  (traduction, catalogue partiel)

L'anglais sert de base parce qu'il est complet ; le francais est superpose
carte par carte quand il existe. Une carte recente sortira donc en anglais,
une carte plus ancienne en francais.

Le site est rendu cote serveur et ne declare aucun robots.txt. Une requete
par extension suffit (~60 en anglais, ~37 en francais), espacees d'une
seconde : le scraping complet represente une centaine de requetes.

Sortie :
  site/data/cards.json      metadonnees fusionnees, consommees par le site
  site/data/images.txt      manifeste des visuels a telecharger (url -> fichier)

Usage :
  python3 tools/scrape-cards.py --out site/data
  python3 tools/scrape-cards.py --out site/data --limit 2   # essai rapide

Ce script tourne sur le serveur de build, jamais sur le poste de travail.
"""

import argparse
import gzip
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import OrderedDict

LOCALES = {
    "en": "https://en.onepiece-cardgame.com",
    "fr": "https://fr.onepiece-cardgame.com",
}

# Un agent identifiable : si notre trafic derange, ils savent qui contacter.
USER_AGENT = (
    "OPTCG-Odds/1.0 (calculateur de probabilites communautaire; "
    "+https://opdeck.hokhori.be)"
)

DELAY_SECONDS = 1.0

# Le libelle du <h3> distingue un cout d'une valeur de vie : les Leaders
# reutilisent la meme div que les Personnages.
LIFE_LABELS = {"life", "vie"}

CATEGORY_CANON = {
    "LEADER": "LEADER",
    "CHARACTER": "CHARACTER",
    "PERSONNAGE": "CHARACTER",
    "EVENT": "EVENT",
    "EVENEMENT": "EVENT",
    "STAGE": "STAGE",
    "SCENE": "STAGE",
    "DON!!": "DON",
    "DON!! CARD": "DON",
}


def canon_category(raw):
    """Categorie canonique, quelle que soit la langue du libelle.

    Le site francais ecrit « EVENEMENTS » au pluriel et accentue ; l'anglais
    « EVENT » au singulier. On retire accents et pluriel avant de comparer,
    faute de quoi une categorie francaise ressort telle quelle et casse les
    filtres de l'interface.
    """
    if not raw:
        return None
    flat = unicodedata.normalize("NFKD", raw.strip().upper())
    flat = "".join(ch for ch in flat if not unicodedata.combining(ch))
    if flat in CATEGORY_CANON:
        return CATEGORY_CANON[flat]
    if flat.endswith("S") and flat[:-1] in CATEGORY_CANON:
        return CATEGORY_CANON[flat[:-1]]
    return flat


# --------------------------------------------------------------------------
# Reseau
# --------------------------------------------------------------------------

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "fr,en;q=0.8",
        "Accept-Encoding": "gzip",
    })
    with urllib.request.urlopen(req, timeout=45) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="replace")


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def strip_tags(fragment, keep_breaks=False):
    """Texte brut d'un fragment HTML. keep_breaks conserve les <br> en sauts."""
    if keep_breaks:
        fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = html.unescape(text)
    if keep_breaks:
        lines = [" ".join(l.split()) for l in text.split("\n")]
        return "\n".join(l for l in lines if l)
    return " ".join(text.split())


def field(block, css_class, keep_breaks=False):
    """Contenu d'une div de la fiche, <h3> de libelle retire."""
    m = re.search(r'<div class="%s">(.*?)</div>\s*(?=<div|<a|</div>)'
                  % re.escape(css_class), block, re.S)
    if not m:
        m = re.search(r'<div class="%s">(.*?)</div>' % re.escape(css_class), block, re.S)
        if not m:
            return None, None
    inner = m.group(1)
    label_m = re.search(r"<h3>(.*?)</h3>", inner, re.S)
    label = strip_tags(label_m.group(1)).lower() if label_m else None
    body = re.sub(r"<h3>.*?</h3>", "", inner, flags=re.S)
    return label, strip_tags(body, keep_breaks=keep_breaks)


def to_int(value):
    if value is None:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def split_multi(value):
    if not value or value == "-":
        return []
    return [p.strip() for p in value.split("/") if p.strip()]


def parse_series_options(page):
    """Identifiants d'extension du selecteur, dans l'ordre de la page."""
    ids = re.findall(r'<option value="(\d+)"', page)
    seen = OrderedDict((i, None) for i in ids)
    return list(seen.keys())


def parse_cards(page, locale):
    """Toutes les fiches d'une page d'extension."""
    out = []
    for block in re.findall(r'<dl class="modalCol".*?</dl>', page, re.S):
        id_m = re.search(r'<dl class="modalCol" id="([^"]+)"', block)
        if not id_m:
            continue
        card_id = id_m.group(1).strip()

        info_m = re.search(r'<div class="infoCol">(.*?)</div>', block, re.S)
        spans = re.findall(r"<span>(.*?)</span>", info_m.group(1), re.S) if info_m else []
        spans = [strip_tags(s) for s in spans]
        number = spans[0] if len(spans) > 0 else card_id.split("_")[0]
        rarity = spans[1] if len(spans) > 1 else None
        category_raw = spans[2] if len(spans) > 2 else None

        name_m = re.search(r'<div class="cardName">(.*?)</div>', block, re.S)
        name = strip_tags(name_m.group(1)) if name_m else None

        img_m = re.search(r'data-src="([^"]+)"', block)
        image = None
        if img_m:
            image = re.sub(r"^\.\./", "/", img_m.group(1)).split("?")[0]

        cost_label, cost_value = field(block, "cost")
        is_life = cost_label in LIFE_LABELS if cost_label else False

        _, power = field(block, "power")
        _, counter = field(block, "counter")
        _, color = field(block, "color")
        _, block_icon = field(block, "block")
        _, types = field(block, "feature")
        _, effect = field(block, "text", keep_breaks=True)
        _, card_set = field(block, "getInfo")

        attr_m = re.search(r'<div class="attribute">(.*?)</div>', block, re.S)
        attribute = None
        if attr_m:
            i_m = re.search(r"<i>(.*?)</i>", attr_m.group(1), re.S)
            if i_m:
                attribute = strip_tags(i_m.group(1))
            else:
                alt_m = re.search(r'alt="([^"]*)"', attr_m.group(1))
                attribute = alt_m.group(1) if alt_m else None
            # Les Evenements et Scenes n'ont pas d'attribut : la div existe
            # mais son contenu est vide. Une chaine vide n'est pas une valeur.
            if attribute is not None and not attribute.strip():
                attribute = None

        category = canon_category(category_raw)

        out.append({
            "id": card_id,
            "number": number,
            "rarity": rarity,
            "category": category,
            "name": name,
            "cost": None if is_life else to_int(cost_value),
            "life": to_int(cost_value) if is_life else None,
            "power": to_int(power),
            "counter": to_int(counter),
            "colors": split_multi(color),
            "attribute": attribute,
            "block": block_icon if block_icon and block_icon != "-" else None,
            "types": split_multi(types),
            "effect": effect if effect and effect != "-" else None,
            "set": card_set,
            "image": image,
            "locale": locale,
        })
    return out


# --------------------------------------------------------------------------
# Collecte
# --------------------------------------------------------------------------

def harvest(locale, limit=None, verbose=True):
    base = LOCALES[locale]
    index = fetch(base + "/cardlist/")
    series = parse_series_options(index)
    if limit:
        series = series[:limit]
    if verbose:
        print(f"[{locale}] {len(series)} extensions a parcourir", file=sys.stderr)

    cards = {}
    for n, sid in enumerate(series, 1):
        url = f"{base}/cardlist/?series={sid}"
        try:
            page = fetch(url)
        except urllib.error.HTTPError as exc:
            print(f"[{locale}] extension {sid} : HTTP {exc.code}, ignoree", file=sys.stderr)
            continue
        except urllib.error.URLError as exc:
            print(f"[{locale}] extension {sid} : {exc.reason}, ignoree", file=sys.stderr)
            continue

        found = parse_cards(page, locale)
        for card in found:
            cards.setdefault(card["id"], card)
        if verbose:
            print(f"[{locale}] {n}/{len(series)} extension {sid} : "
                  f"{len(found)} fiches ({len(cards)} cartes uniques)", file=sys.stderr)
        time.sleep(DELAY_SECONDS)

    return cards


def merge(en_cards, fr_cards):
    """Anglais en base, francais superpose quand la carte y existe."""
    merged = []
    for card_id, en in sorted(en_cards.items()):
        fr = fr_cards.get(card_id)
        entry = {
            "id": card_id,
            "number": en["number"],
            "rarity": en["rarity"],
            "category": en["category"],
            "cost": en["cost"],
            "life": en["life"],
            "power": en["power"],
            "counter": en["counter"],
            "colors": en["colors"],
            "attribute": en["attribute"],
            "block": en["block"],
            "image": en["image"],
            "en": {
                "name": en["name"],
                "types": en["types"],
                "effect": en["effect"],
                "set": en["set"],
            },
        }
        if fr:
            entry["fr"] = {
                "name": fr["name"],
                "types": fr["types"],
                "effect": fr["effect"],
                "set": fr["set"],
            }
        merged.append(entry)

    # Cartes presentes en francais mais absentes du catalogue anglais :
    # improbable, mais on ne les perd pas en silence.
    orphans = 0
    for card_id, fr in sorted(fr_cards.items()):
        if card_id in en_cards:
            continue
        orphans += 1
        merged.append({
            "id": card_id,
            "number": fr["number"],
            "rarity": fr["rarity"],
            "category": fr["category"],
            "cost": fr["cost"],
            "life": fr["life"],
            "power": fr["power"],
            "counter": fr["counter"],
            "colors": fr["colors"],
            "attribute": fr["attribute"],
            "block": fr["block"],
            "image": fr["image"],
            "fr": {
                "name": fr["name"],
                "types": fr["types"],
                "effect": fr["effect"],
                "set": fr["set"],
            },
        })
    if orphans:
        print(f"[merge] {orphans} cartes absentes du catalogue anglais", file=sys.stderr)
    return merged


def collapse_variants(cards):
    """Une entree par numero de carte, les parallales repliees dessus.

    Une parallale (`OP01-001_p1`) et sa carte de base partagent toutes les
    donnees de jeu : seul l'artwork change. Les garder separees afficherait
    six fois le meme personnage dans la recherche et multiplierait par deux
    le nombre de visuels a stocker, sans rien apporter a un calculateur de
    probabilites. On conserve la liste de leurs identifiants pour ne rien
    perdre.
    """
    by_number = OrderedDict()
    for card in cards:
        by_number.setdefault(card["number"], []).append(card)

    out = []
    for number, group in by_number.items():
        base = next((c for c in group if c["id"] == number), group[0])
        entry = dict(base)
        variants = sorted(c["id"] for c in group if c["id"] != base["id"])
        if variants:
            entry["variants"] = variants
        out.append(entry)
    return out


def finalize(cards, outdir):
    """Repli, ecriture du JSON et du manifeste des visuels."""
    cards = collapse_variants(cards)
    os.makedirs(outdir, exist_ok=True)

    payload = {
        "generated": time.strftime("%Y-%m-%d"),
        "source": "https://en.onepiece-cardgame.com/cardlist/ + fr.onepiece-cardgame.com",
        "count": len(cards),
        "count_fr": sum(1 for c in cards if "fr" in c),
        "cards": cards,
    }
    cards_path = os.path.join(outdir, "cards.json")
    with open(cards_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

    version_path = os.path.join(outdir, "version.json")
    with open(version_path, "w", encoding="utf-8") as fh:
        json.dump({"generated": payload["generated"], "count": payload["count"]}, fh)

    # Manifeste : uniquement les cartes de base, une ligne « url<TAB>fichier ».
    manifest_path = os.path.join(outdir, "images.txt")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        for card in cards:
            if not card.get("image"):
                continue
            fh.write("%s%s\t%s.png\n" % (LOCALES["en"], card["image"], card["id"]))

    size = os.path.getsize(cards_path)
    print(f"\n{len(cards)} cartes ecrites dans {cards_path} ({size/1024:.0f} Ko)",
          file=sys.stderr)
    print(f"{payload['count_fr']} disposent d'une traduction francaise", file=sys.stderr)
    print(f"manifeste des visuels : {manifest_path} "
          f"({sum(1 for c in cards if c.get('image'))} visuels)", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="site/data", help="dossier de sortie")
    ap.add_argument("--limit", type=int, default=None,
                    help="ne parcourir que les N premieres extensions (essai)")
    ap.add_argument("--locales", default="en,fr", help="langues a collecter")
    ap.add_argument("--collapse-only", metavar="FICHIER", default=None,
                    help="ne rien telecharger : replier un cards-raw.json existant")
    args = ap.parse_args()

    if args.collapse_only:
        with open(args.collapse_only, encoding="utf-8") as fh:
            raw = json.load(fh)
        finalize(raw["cards"], args.out)
        return

    wanted = [l.strip() for l in args.locales.split(",") if l.strip()]
    harvested = {l: harvest(l, args.limit) for l in wanted}
    en_cards = harvested.get("en", {})
    fr_cards = harvested.get("fr", {})
    cards = merge(en_cards, fr_cards) if en_cards else list(fr_cards.values())

    os.makedirs(args.out, exist_ok=True)
    # Le brut conserve les parallales : il permet de rejouer le repli sans
    # relancer une centaine de requetes sur le site officiel.
    with open(os.path.join(args.out, "cards-raw.json"), "w", encoding="utf-8") as fh:
        json.dump({"generated": time.strftime("%Y-%m-%d"), "cards": cards},
                  fh, ensure_ascii=False, separators=(",", ":"))

    finalize(cards, args.out)


if __name__ == "__main__":
    main()
