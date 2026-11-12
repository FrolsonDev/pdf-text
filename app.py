"""
pdf-texte : service HTTP minimal autour de PyMuPDF et pymupdf4llm.

Chaque route execute une operation PyMuPDF elementaire et renvoie le resultat
brut. Le service ne prend aucune decision : quelles pages lire, a quel zoom,
quoi caviarder, tout est fourni par l'appelant.

Le document se designe de deux facons :
  - JSON  {"chemin": "/data/doc.pdf", ...}         (fichier visible du service)
  - multipart : champ fichier "pdf" + champ texte "params" (JSON)

Copyright (C) 2026 FrolsonDev

Licence : GNU AGPL v3 (voir LICENSE). PyMuPDF, pymupdf4llm et pymupdf-layout
sont distribues par Artifex sous AGPL v3.
"""
import json
import os
import re

import pymupdf as fitz
import pymupdf4llm
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

DOSSIERS_AUTORISES = [d for d in os.getenv("PDF_TEXTE_DOSSIERS", "/data").split(":") if d]


class ErreurRequete(Exception):
    pass


@app.errorhandler(ErreurRequete)
def _erreur_requete(e):
    return jsonify({"erreur": str(e)}), 400


def _params():
    if request.files:
        return json.loads(request.form.get("params") or "{}")
    return request.get_json(force=True, silent=True) or {}


def _chemin(params):
    """Chemin valide du document, ou None s'il est envoye en multipart."""
    if request.files.get("pdf") is not None:
        return None
    chemin = params.get("chemin")
    if not chemin:
        raise ErreurRequete("ni 'chemin' ni fichier 'pdf'")
    reel = os.path.realpath(chemin)
    if not any(reel == d or reel.startswith(d.rstrip("/") + "/") for d in DOSSIERS_AUTORISES):
        raise ErreurRequete(f"chemin hors des dossiers autorises : {chemin}")
    if not os.path.exists(reel):
        raise ErreurRequete(f"fichier introuvable : {chemin}")
    return reel


def _ouvrir(params):
    """Ouvre le document designe par la requete (chemin ou octets envoyes)."""
    chemin = _chemin(params)
    if chemin is None:
        return fitz.open(stream=request.files["pdf"].read(), filetype=params.get("type") or "pdf")
    return fitz.open(chemin)


def _pages(params, doc):
    if "pages" in params and params["pages"] is not None:
        return [int(p) for p in params["pages"]]
    return [int(params.get("page", 0))]


def _json_propre(objet):
    """Retire les octets (images) d'une structure get_text('dict')."""
    if isinstance(objet, dict):
        return {k: _json_propre(v) for k, v in objet.items() if not isinstance(v, (bytes, bytearray))}
    if isinstance(objet, (list, tuple)):
        return [_json_propre(v) for v in objet]
    return objet


def _binaire(donnees, type_mime):
    return Response(bytes(donnees), mimetype=type_mime)


@app.get("/sante")
def sante():
    return jsonify({"ok": True, "pymupdf": fitz.VersionBind,
                    "pymupdf4llm": getattr(pymupdf4llm, "__version__", "?")})


@app.post("/info")
def info():
    """Nombre de pages et rectangle de chaque page."""
    with _ouvrir(_params()) as doc:
        return jsonify({"pages": doc.page_count,
                        "rects": [list(p.rect) for p in doc]})


@app.post("/texte")
def texte():
    """page.get_text(mode, sort=...) pour une ou plusieurs pages."""
    params = _params()
    mode = params.get("mode", "text")
    if mode not in ("text", "blocks", "dict", "words"):
        raise ErreurRequete(f"mode non gere : {mode}")
    options = {"sort": True} if params.get("sort") else {}
    with _ouvrir(params) as doc:
        res = [_json_propre(doc[p].get_text(mode, **options)) for p in _pages(params, doc)]
    return jsonify({"textes": res})


@app.post("/rendu")
def rendu():
    """Image d'une page : get_pixmap(matrix=Matrix(zoom, zoom)) puis tobytes()."""
    params = _params()
    options = {}
    if params.get("zoom") is not None:
        z = float(params["zoom"])
        options["matrix"] = fitz.Matrix(z, z)
    if params.get("colorspace") == "rgb":
        options["colorspace"] = fitz.csRGB
    fmt = params.get("format", "png")
    sortie = {}
    if params.get("jpg_quality") is not None:
        sortie["jpg_quality"] = int(params["jpg_quality"])
    with _ouvrir(params) as doc:
        pix = doc[int(params.get("page", 0))].get_pixmap(**options)
        donnees = pix.tobytes(fmt, **sortie)
    return _binaire(donnees, "image/jpeg" if fmt in ("jpg", "jpeg") else "image/" + fmt)


@app.post("/extraire")
def extraire():
    """Nouveau PDF fait des pages demandees, dans l'ordre donne."""
    params = _params()
    with _ouvrir(params) as src:
        sous = fitz.open()
        for p in _pages(params, src):
            sous.insert_pdf(src, from_page=p, to_page=p)
        donnees = sous.tobytes()
        sous.close()
    return _binaire(donnees, "application/pdf")


@app.post("/dessins")
def dessins():
    """Nombre de dessins vectoriels de chaque page demandee."""
    params = _params()
    with _ouvrir(params) as doc:
        return jsonify({"nombres": [len(doc[p].get_drawings()) for p in _pages(params, doc)]})


@app.post("/lignes-pivotees")
def lignes_pivotees():
    """Texte des lignes non horizontales de chaque page demandee (texte vertical
    ou incline), dans l'ordre du document. `seuil` : une ligne est retenue quand
    la composante horizontale de sa direction est inferieure a ce seuil (0.9)."""
    params = _params()
    seuil = float(params.get("seuil", 0.9))
    with _ouvrir(params) as doc:
        res = []
        for p in _pages(params, doc):
            res.append(["".join(s["text"] for s in l["spans"])
                        for b in doc[p].get_text("dict")["blocks"]
                        for l in b.get("lines", []) if abs(l["dir"][0]) < seuil])
        return jsonify({"lignes": res})


@app.post("/texte-lecture")
def texte_lecture():
    """Texte d'une page dans l'ordre de lecture, tableaux en markdown."""
    params = _params()
    with _ouvrir(params) as doc:
        return jsonify({"textes": [_texte_lecture(doc[p]) for p in _pages(params, doc)]})


def _texte_lecture(page):
    items, rects = [], []
    try:
        for tb in page.find_tables().tables:
            try:
                md = tb.to_markdown().strip()
            except Exception:
                md = ""
            if md:
                rects.append(fitz.Rect(tb.bbox))
                items.append((tb.bbox[1], md))
    except Exception:
        rects, items = [], []
    for b in page.get_text("blocks", sort=True):
        if len(b) > 6 and b[6] != 0:
            continue
        txt = (b[4] or "").strip()
        if not txt:
            continue
        r = fitz.Rect(b[:4])
        aire = max(r.get_area(), 1e-6)
        if any((r & t).get_area() / aire > 0.5 for t in rects):
            continue
        items.append((b[1], txt))
    items.sort(key=lambda x: x[0])
    return "\n".join(t for _, t in items)


@app.post("/markdown")
def markdown():
    """pymupdf4llm.to_markdown(page_chunks=True) : texte et metadonnees par page."""
    params = _params()
    options = {"page_chunks": True, "use_ocr": bool(params.get("use_ocr", False))}
    if params.get("pages"):
        options["pages"] = [int(p) for p in params["pages"]]
    # Sur un chemin, to_markdown ouvre le fichier lui-meme, comme un appel direct.
    chemin = _chemin(params)
    if chemin is not None:
        chunks = pymupdf4llm.to_markdown(chemin, **options)
    else:
        with _ouvrir(params) as doc:
            chunks = pymupdf4llm.to_markdown(doc, **options)
    return jsonify({"chunks": [{"text": c.get("text", ""),
                                "metadata": _json_propre(c.get("metadata", {}))}
                               for c in chunks]})


@app.post("/aplatir-premiere-page")
def aplatir_premiere_page():
    """Remplace la page 1 par son image (pages suivantes inchangees)."""
    with _ouvrir(_params()) as src:
        nouveau = fitz.open()
        premiere = src.load_page(0)
        pix = premiere.get_pixmap()
        rect = premiere.rect
        page = nouveau.new_page(width=rect.width, height=rect.height)
        page.insert_image(fitz.Rect(0, 0, rect.width, rect.height), stream=pix.tobytes(output="png"))
        for n in range(1, src.page_count):
            nouveau.insert_pdf(src, from_page=n, to_page=n)
        donnees = nouveau.tobytes()
        nouveau.close()
    return _binaire(donnees, "application/pdf")


@app.post("/caviarder")
def caviarder():
    """
    Applique des regles de caviardage, dans l'ordre, sur chaque page.
    Regle : {"texte": str, "ignorer_casse": bool, "pleine_largeur": bool,
             "marge": float, "remplacement": str (optionnel)}
    """
    params = _params()
    regles = params.get("regles") or []
    total = 0
    with _ouvrir(params) as doc:
        for page in doc:
            texte_page = page.get_text()
            rect_page = page.rect
            for r in regles:
                cible = r["texte"]
                if r.get("ignorer_casse"):
                    occurrences = [m.group() for m in re.finditer(re.escape(cible), texte_page, re.IGNORECASE)]
                else:
                    occurrences = [cible]
                for occ in occurrences:
                    for zone in page.search_for(occ):
                        if r.get("pleine_largeur"):
                            m = float(r.get("marge", 0))
                            zone = fitz.Rect(rect_page.x0, zone.y0 - m, rect_page.x1, zone.y1 + m)
                        if "remplacement" in r:
                            page.add_redact_annot(zone, text=r["remplacement"])
                        else:
                            page.add_redact_annot(zone)
                        total += 1
            page.apply_redactions()
        donnees = doc.tobytes()
        pages = doc.page_count
    rep = _binaire(donnees, "application/pdf")
    rep.headers["X-Caviardages"] = str(total)
    rep.headers["X-Pages"] = str(pages)
    return rep
