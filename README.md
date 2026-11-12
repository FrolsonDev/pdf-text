# pdf-texte

Petit service HTTP autour de [PyMuPDF](https://github.com/pymupdf/PyMuPDF) et
[pymupdf4llm](https://github.com/pymupdf/pymupdf4llm) : chaque route exécute une
opération élémentaire sur un PDF et renvoie le résultat brut (texte, JSON, image
ou PDF). Le service ne prend aucune décision métier : les pages, le zoom ou les
zones à caviarder sont fournis par l'appelant.

## Lancer

```bash
docker build -t pdf-texte .
docker run -p 8000:8000 -v /chemin/vers/pdfs:/data:ro pdf-texte
```

Les documents se désignent soit par un chemin sous un dossier autorisé
(`PDF_TEXTE_DOSSIERS`, par défaut `/data`), soit en envoyant le fichier.

- JSON : `{"chemin": "/data/doc.pdf", ...}`
- multipart : champ fichier `pdf` + champ texte `params` (JSON)

## Routes

| Route | Paramètres | Réponse |
|---|---|---|
| `GET /sante` | — | versions de PyMuPDF / pymupdf4llm |
| `POST /info` | — | nombre de pages et rectangle de chaque page |
| `POST /texte` | `page` ou `pages`, `mode` (`text`, `blocks`, `dict`, `words`), `sort` | texte de chaque page |
| `POST /rendu` | `page`, `zoom`, `format` (`png`, `jpeg`), `jpg_quality`, `colorspace` | image de la page |
| `POST /extraire` | `pages` | PDF composé des pages demandées |
| `POST /dessins` | `page` ou `pages` | nombre de dessins vectoriels |
| `POST /texte-lecture` | `page` ou `pages` | texte dans l'ordre de lecture, tableaux en Markdown |
| `POST /markdown` | `pages` (facultatif), `use_ocr` | `pymupdf4llm.to_markdown(page_chunks=True)` : texte et métadonnées par page |
| `POST /aplatir-premiere-page` | — | PDF dont la page 1 est remplacée par son image |
| `POST /caviarder` | `regles` : `[{texte, ignorer_casse, pleine_largeur, marge, remplacement}]` | PDF caviardé (en-tête `X-Caviardages`) |

## Ghostscript (`ghostscript/`)

Second service, construit séparément : exécute Ghostscript (`pdfwrite`) sur un ou
plusieurs PDF et renvoie le PDF produit. Image Ubuntu 22.04 (Ghostscript 9.55).

```bash
docker build -t pdf-gs ghostscript
docker run -p 8001:8000 -v /chemin/vers/pdfs:/data:ro pdf-gs
```

`POST /gs` : `{"entrees": ["/data/a.pdf"], "args": ["-sDEVICE=pdfwrite",
"-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dQUIET", "-dBATCH", "-sOutputFile=@SORTIE",
"@ENTREE"], "delai": 600}` — ou multipart (fichiers `entree` + champ `params`).
La ligne de commande est exécutée dans l'ordre donné (Ghostscript la recopie dans
le PDF). Sorties, autres périphériques et options désactivant le mode sûr sont
refusés. Réponse : le PDF (200), `{returncode, stdout, stderr}` (422) ou 504.

## Versions

Les versions sont épinglées dans `requirements.txt` (PyMuPDF, pymupdf4llm et
pymupdf-layout 1.28.2) pour obtenir des sorties identiques d'un déploiement à
l'autre.

## Licence

Copyright (C) 2026 FrolsonDev

Ce programme est un logiciel libre : vous pouvez le redistribuer et/ou le
modifier selon les termes de la GNU Affero General Public License publiée par
la Free Software Foundation, version 3 de la licence ou (à votre choix) toute
version ultérieure. Il est distribué SANS AUCUNE GARANTIE. Voir le fichier
[LICENSE](LICENSE).

PyMuPDF, pymupdf4llm, pymupdf-layout et Ghostscript sont distribués par Artifex
Software sous GNU AGPL v3 ; ils sont utilisés ici sans modification.
