# Conformité des licences

Ce dépôt contient le code source complet des deux services qui exécutent les
composants AGPL d'Artifex pour le site yachtsecure.com : `pdf-texte` (racine) et
`pdf-gs` (`ghostscript/`). Les versions taguées sont celles qui ont été déployées
en production.

## Composants Artifex (GNU AGPL v3)

Ces composants sont utilisés **sans modification**. Ils sont installés depuis
leurs paquets officiels, et leurs versions sont figées.

| Composant | Version | Service | Installé depuis | Licence déclarée par le paquet | Source |
|---|---|---|---|---|---|
| PyMuPDF | 1.28.2 | pdf-texte | PyPI (`requirements.txt`) | Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License | https://github.com/pymupdf/PyMuPDF |
| pymupdf4llm | 1.28.2 | pdf-texte | PyPI (`requirements.txt`) | Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License | https://github.com/pymupdf/pymupdf4llm |
| pymupdf-layout | 1.28.2 | pdf-texte | PyPI (`requirements.txt`) | Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License ¹ | https://pypi.org/project/pymupdf-layout/ |
| Ghostscript | 9.55.0~dfsg1-0ubuntu5.15 | pdf-gs | paquet Ubuntu 22.04 (`apt`) | GNU AGPL v3 | https://ghostscript.com/releases/ — https://launchpad.net/ubuntu/+source/ghostscript |

¹ Les métadonnées de pymupdf-layout 1.28.2 portent aussi le classificateur
`License :: Other/Proprietary License`. Ce classificateur désigne l'option de
licence commerciale. Le champ `License` du même paquet indique la double
licence AGPL v3 / licence commerciale Artifex.

## Autres composants inclus dans les images

Tous sous licence permissive. Aucune obligation de publication.

| Composant | Version | Licence |
|---|---|---|
| Flask / Werkzeug | 3.1.3 / 3.1.9 | BSD-3-Clause |
| gunicorn | 26.2.0 | MIT |
| onnxruntime | 1.31.1 | MIT |
| numpy | 2.3.2 | BSD |
| networkx | 3.5 | BSD |
| tabulate | 0.10.0 | MIT |
| PyYAML | 6.0.2 | MIT |
| psutil | 7.0.0 | BSD-3-Clause |
| Images de base | `python:3.11-slim`, `ubuntu:22.04` | licences de leurs distributions respectives |

## Code propre à ce dépôt

`app.py`, `ghostscript/app.py` et les Dockerfile sont publiés sous GNU AGPL v3
ou ultérieure (fichier `LICENSE`).

Les services exposent des opérations élémentaires sur un PDF par HTTP (voir le
`README.md`). Ils ne contiennent aucune logique métier. L'application qui les
appelle est un programme séparé : elle échange uniquement des requêtes HTTP et
reçoit du texte, du JSON, des images ou des PDF.

## Reconstruire les services

```bash
git clone https://github.com/FrolsonDev/pdf-text.git && cd pdf-text
git checkout <tag>                     # la version voulue, voir l'historique ci-dessous
docker build -t pdf-texte .
docker build -t pdf-gs ghostscript
docker run -p 8000:8000 -v /chemin/vers/pdfs:/data:ro pdf-texte
docker run -p 8001:8000 -v /chemin/vers/pdfs:/data:ro pdf-gs
```

## Historique des déploiements en production

| Tag | Date de mise en production | Contenu |
|---|---|---|
| `v1.0.0` | 12/11/2026 | Premier déploiement : `pdf-texte`, puis `pdf-gs` le même jour |
| `v1.1.0` | 12/11/2026 | Route `/lignes-pivotees` ; ajout de ce fichier |

Toute nouvelle version déployée reçoit un tag et une ligne dans ce tableau.

## Où le lien vers ce dépôt est affiché

- Sur yachtsecure.com, en bas de chaque page de l'analyseur de polices, dans les 6 langues.
- Dans les mentions légales de yachtsecure.com, dans les 6 langues.
