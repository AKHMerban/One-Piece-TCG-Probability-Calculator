#!/usr/bin/env python3
"""
Telecharge les visuels des cartes et les convertit en WebP.

Lit le manifeste produit par scrape-cards.py (une ligne « url<TAB>fichier ») et
depose un .webp par carte dans le dossier de sortie.

Pourquoi WebP : les PNG officiels font ~200 Ko chacun ; a qualite 78 le meme
visuel tombe autour de 52 Ko, soit 26 %. Sur 2785 cartes de base, c'est 145 Mo
au lieu de 640 Mo. Les originaux font deja 600 px de large, donc aucun
redimensionnement n'est applique : on ne perd pas de definition.

Le script est reprenable : un fichier deja converti est saute. On peut donc
l'interrompre et le relancer sans tout refaire.

Usage :
  python3 tools/fetch-card-images.py --manifest out/images.txt --out out/cards

Ce script tourne sur le serveur de build, jamais sur le poste de travail.
"""

import argparse
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

USER_AGENT = (
    "OPTCG-Odds/1.0 (calculateur de probabilites communautaire; "
    "+https://opdeck.hokhori.be)"
)

# Six fils, chacun marquant une courte pause entre deux requetes : environ
# trois requetes par seconde au total, mesurees. C'est peu pour des images
# statiques, et cela ramene les 2785 visuels sous le quart d'heure.
WORKERS = 6
PER_WORKER_DELAY = 0.1

_lock = threading.Lock()
_stats = {"ok": 0, "skip": 0, "fail": 0}


def report(kind):
    with _lock:
        _stats[kind] += 1
        done = _stats["ok"] + _stats["skip"] + _stats["fail"]
        if done % 100 == 0:
            print(f"  {done} traites — {_stats['ok']} convertis, "
                  f"{_stats['skip']} deja presents, {_stats['fail']} en echec",
                  file=sys.stderr, flush=True)


def convert(png_bytes, dest, quality):
    """PNG en memoire -> WebP sur disque, via cwebp qui lit sur stdin."""
    proc = subprocess.run(
        ["cwebp", "-quiet", "-q", str(quality), "-o", dest, "--", "-"],
        input=png_bytes, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace").strip() or "cwebp a echoue")


def handle(entry, outdir, quality, retries):
    url, filename = entry
    stem = os.path.splitext(filename)[0]
    dest = os.path.join(outdir, stem + ".webp")

    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        report("skip")
        return

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = resp.read()
            convert(data, dest, quality)
            report("ok")
            time.sleep(PER_WORKER_DELAY)
            return
        except (urllib.error.URLError, RuntimeError, OSError) as exc:
            if attempt == retries:
                print(f"  ECHEC {stem} : {exc}", file=sys.stderr, flush=True)
                # Ne pas laisser un fichier tronque derriere soi.
                if os.path.exists(dest) and os.path.getsize(dest) == 0:
                    os.remove(dest)
                report("fail")
                return
            time.sleep(2 * attempt)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, help="fichier images.txt")
    ap.add_argument("--out", required=True, help="dossier de sortie des .webp")
    ap.add_argument("--quality", type=int, default=78, help="qualite WebP (defaut 78)")
    ap.add_argument("--retries", type=int, default=3)
    args = ap.parse_args()

    if subprocess.run(["which", "cwebp"], stdout=subprocess.DEVNULL).returncode != 0:
        sys.exit("cwebp introuvable — installer le paquet « webp »")

    entries = []
    with open(args.manifest, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or "\t" not in line:
                continue
            url, filename = line.split("\t", 1)
            entries.append((url, filename))

    os.makedirs(args.out, exist_ok=True)
    print(f"{len(entries)} visuels a traiter, {WORKERS} fils, qualite {args.quality}",
          file=sys.stderr, flush=True)
    started = time.time()

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for entry in entries:
            pool.submit(handle, entry, args.out, args.quality, args.retries)

    total = sum(os.path.getsize(os.path.join(args.out, f))
                for f in os.listdir(args.out) if f.endswith(".webp"))
    count = sum(1 for f in os.listdir(args.out) if f.endswith(".webp"))
    minutes = (time.time() - started) / 60
    print(f"\n{count} visuels sur disque, {total/1024/1024:.0f} Mo "
          f"({total/count/1024:.0f} Ko en moyenne) en {minutes:.1f} min",
          file=sys.stderr)
    print(f"convertis {_stats['ok']} · deja presents {_stats['skip']} · "
          f"echecs {_stats['fail']}", file=sys.stderr)
    if _stats["fail"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
