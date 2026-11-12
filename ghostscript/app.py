"""
pdf-gs : service HTTP qui execute Ghostscript (pdfwrite) sur un ou plusieurs PDF.

POST /gs
  - JSON  {"entrees": ["/data/a.pdf", ...], "delai": 600,
           "args": ["-sDEVICE=pdfwrite", "-dPDFSETTINGS=/ebook", "-sOutputFile=@SORTIE", "@ENTREE", ...]}
  - ou multipart : fichiers "entree" (dans l'ordre) + champ texte "params" (JSON, sans "entrees")
Renvoie le PDF produit (200), ou {"returncode", "stdout", "stderr"} (422) si gs echoue,
ou 504 si le delai est depasse.

Le service n'ajoute aucune logique : l'appelant fournit les options de gs ;
seules les options dangereuses (sortie, mode non sur, autre peripherique) sont refusees.

Copyright (C) 2026 FrolsonDev
Licence : GNU AGPL v3 (voir ../LICENSE). Ghostscript est distribue par Artifex
sous AGPL v3 ; il est utilise ici sans modification.
"""
import json
import os
import subprocess
import tempfile

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
DOSSIERS_AUTORISES = [d for d in os.getenv("PDF_GS_DOSSIERS", "/data").split(":") if d]
# Options refusees : sortie (fixee par le service), sorties de securite,
# autre peripherique que pdfwrite, fichiers d'arguments.
PREFIXES_INTERDITS = ("-sOutputFile", "-o", "-dNOSAFER", "-dDELAYSAFER", "-dNOSAFETY",
                      "-sDEVICE", "-q@", "-@")


def _option_valide(opt):
    return (isinstance(opt, str) and opt.startswith("-") and "%" not in opt
            and not opt.startswith(PREFIXES_INTERDITS))


def _chemin(c):
    reel = os.path.realpath(c)
    if not any(reel == d or reel.startswith(d.rstrip("/") + "/") for d in DOSSIERS_AUTORISES):
        raise ValueError(f"chemin hors des dossiers autorises : {c}")
    if not os.path.isfile(reel):
        raise ValueError(f"fichier introuvable : {c}")
    return reel


@app.get("/sante")
def sante():
    v = subprocess.run(["gs", "--version"], capture_output=True, text=True).stdout.strip()
    return jsonify({"ok": True, "ghostscript": v})


@app.post("/gs")
def gs():
    if request.files:
        params = json.loads(request.form.get("params") or "{}")
    else:
        params = request.get_json(force=True, silent=True) or {}
    # "args" : la ligne de commande dans son ordre exact (gs la recopie dans le
    # PDF), avec "-sOutputFile=@SORTIE" et "@ENTREE" a la place des fichiers.
    args = params.get("args") or []
    autorises = ("-sDEVICE=pdfwrite", "-sOutputFile=@SORTIE", "@ENTREE")
    mauvaises = [o for o in args if o not in autorises and not _option_valide(o)]
    if mauvaises:
        return jsonify({"erreur": f"options refusees : {mauvaises}"}), 400
    delai = min(float(params.get("delai", 600)), 3600)

    with tempfile.TemporaryDirectory() as tmp:
        try:
            if request.files:
                entrees = []
                for i, f in enumerate(request.files.getlist("entree")):
                    p = os.path.join(tmp, f"entree_{i:03d}.pdf")
                    f.save(p)
                    entrees.append(p)
            else:
                entrees = [_chemin(c) for c in params.get("entrees") or []]
        except ValueError as e:
            return jsonify({"erreur": str(e)}), 400
        if not entrees:
            return jsonify({"erreur": "aucune entree"}), 400
        sortie = os.path.join(tmp, "sortie.pdf")
        if args.count("-sDEVICE=pdfwrite") != 1 or args.count("-sOutputFile=@SORTIE") != 1 \
                or args.count("@ENTREE") != len(entrees):
            return jsonify({"erreur": "args : il faut -sDEVICE=pdfwrite, -sOutputFile=@SORTIE "
                                      "et un @ENTREE par fichier"}), 400
        # Pas de -dSAFER explicite : c'est le defaut depuis gs 9.50, et gs recopie
        # sa ligne de commande dans le PDF (%%Invocation) -> octets differents.
        reste = iter(entrees)
        cmd = ["gs"] + [f"-sOutputFile={sortie}" if a == "-sOutputFile=@SORTIE"
                        else next(reste) if a == "@ENTREE" else a for a in args]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=delai)
        except subprocess.TimeoutExpired:
            return jsonify({"erreur": "delai depasse", "delai": delai}), 504
        if r.returncode != 0 or not os.path.exists(sortie):
            return jsonify({"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}), 422
        with open(sortie, "rb") as fh:
            donnees = fh.read()
    rep = Response(donnees, mimetype="application/pdf")
    rep.headers["X-Gs-Returncode"] = str(r.returncode)
    return rep
