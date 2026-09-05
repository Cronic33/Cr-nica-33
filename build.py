#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador estatico de Cronica 33.
Sin dependencias externas: solo hace falta Python 3.8 o superior.

    python build.py            -> genera la web en dist/
    python build.py --servir   -> genera y abre un servidor local en http://localhost:8000
"""

import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from html import escape
from pathlib import Path

ARREL = Path(os.path.dirname(os.path.abspath(__file__)))
DIR_CONTINGUT = ARREL / "contingut"
DIR_TEMA = ARREL / "tema"
DIR_MEDIA = ARREL / "media"
DIR_SORTIDA = ARREL / "dist"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Barra de ultima hora: se calcula en main() y la usa cada pagina.
BARRA_ULTIMA_HORA = ""


# ---------------------------------------------------------------- utilidades

def llegeix_config():
    dades = json.loads((ARREL / "config.json").read_text(encoding="utf-8"))
    dades.setdefault("nom", "Crónica 33")
    dades.setdefault("nom_principal", dades["nom"])
    dades.setdefault("nom_accent", "")
    dades.setdefault("url", "")
    dades["url"] = dades["url"].rstrip("/")
    dades.setdefault("idioma", "es")
    dades.setdefault("articles_per_pagina", 12)
    dades.setdefault("seccions", [])
    dades.setdefault("xarxes", [])
    dades.setdefault("publicitat", {})
    dades.setdefault("analitica", {})
    dades.setdefault("contacte", {})
    dades.setdefault("logo", "")
    return dades


def camp(dades, *noms):
    """Devuelve el primer campo presente. Acepta nombres en castellano y catalan."""
    for nom in noms:
        if nom in dades and dades[nom] not in ("", None, []):
            return dades[nom]
    return None


def slugifica(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "sin-titulo"


def data_llegible(dt):
    return "%d de %s de %d" % (dt.day, MESES[dt.month - 1], dt.year)


def data_hora_llegible(dt):
    return "%s, %02d:%02d h" % (data_llegible(dt), dt.hour, dt.minute)


def analitza_data(valor):
    if isinstance(valor, datetime):
        return valor
    text = str(valor).strip()
    for patro in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S",
                  "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:len("2026-09-04T12:00:00")], patro)
        except ValueError:
            continue
    return datetime.now()


def valor_yaml(brut):
    brut = brut.strip()
    if not brut:
        return ""
    if brut[0] in "\"'" and brut[-1] == brut[0] and len(brut) > 1:
        return brut[1:-1]
    if brut.startswith("[") and brut.endswith("]"):
        cos = brut[1:-1].strip()
        if not cos:
            return []
        return [valor_yaml(t) for t in cos.split(",")]
    baix = brut.lower()
    if baix in ("true", "si", "sí", "yes"):
        return True
    if baix in ("false", "no"):
        return False
    return brut


def separa_capcalera(text):
    """Separa la cabecera --- ... --- del cuerpo en Markdown."""
    if not text.startswith("---"):
        return {}, text
    tall = text.find("\n---", 3)
    if tall == -1:
        return {}, text
    capcalera = text[3:tall].strip("\n")
    cos = text[tall + 4:].lstrip("\n")
    dades = {}
    clau_llista = None
    for linia in capcalera.split("\n"):
        if not linia.strip() or linia.strip().startswith("#"):
            continue
        if linia.lstrip().startswith("- ") and clau_llista:
            dades[clau_llista].append(valor_yaml(linia.lstrip()[2:]))
            continue
        if ":" not in linia:
            continue
        clau, _, resta = linia.partition(":")
        clau = clau.strip().lower()
        resta = resta.strip()
        if resta == "":
            dades[clau] = []
            clau_llista = clau
        else:
            dades[clau] = valor_yaml(resta)
            clau_llista = None
    return dades, cos


# ------------------------------------------------------------- incrustaciones

RE_YOUTUBE = re.compile(r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{6,})")
RE_VIMEO = re.compile(r"vimeo\.com/(?:video/)?(\d+)")
RE_DAILY = re.compile(r"dailymotion\.com/video/([A-Za-z0-9]+)")
RE_RUMBLE = re.compile(r"rumble\.com/embed/([A-Za-z0-9]+)")


def incrusta(url):
    """Convierte una direccion de red social o video en HTML incrustable."""
    url = str(url).strip()
    if not url:
        return ""
    m = RE_YOUTUBE.search(url)
    if m:
        return ('<div class="incrusta"><iframe src="https://www.youtube-nocookie.com/embed/%s" '
                'title="Vídeo de YouTube" loading="lazy" allowfullscreen '
                'allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                'referrerpolicy="strict-origin-when-cross-origin"></iframe></div>') % m.group(1)
    m = RE_VIMEO.search(url)
    if m:
        return ('<div class="incrusta"><iframe src="https://player.vimeo.com/video/%s" '
                'title="Vídeo de Vimeo" loading="lazy" allowfullscreen></iframe></div>') % m.group(1)
    m = RE_DAILY.search(url)
    if m:
        return ('<div class="incrusta"><iframe src="https://www.dailymotion.com/embed/video/%s" '
                'title="Vídeo de Dailymotion" loading="lazy" allowfullscreen></iframe></div>') % m.group(1)
    m = RE_RUMBLE.search(url)
    if m:
        return ('<div class="incrusta"><iframe src="https://rumble.com/embed/%s/" '
                'title="Vídeo de Rumble" loading="lazy" allowfullscreen></iframe></div>') % m.group(1)
    if "tiktok.com" in url:
        return ('<blockquote class="tiktok-embed" cite="%s"><a href="%s">Ver el vídeo en TikTok</a></blockquote>'
                '<script async src="https://www.tiktok.com/embed.js"></script>') % (escape(url), escape(url))
    if "instagram.com" in url:
        return ('<blockquote class="instagram-media" data-instgrm-permalink="%s" data-instgrm-version="14">'
                '<a href="%s">Ver la publicación en Instagram</a></blockquote>'
                '<script async src="https://www.instagram.com/embed.js"></script>') % (escape(url), escape(url))
    if "twitter.com" in url or "x.com" in url:
        return ('<blockquote class="twitter-tweet"><a href="%s">Ver la publicación</a></blockquote>'
                '<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>') % escape(url)
    if "facebook.com" in url:
        return ('<div class="incrusta"><iframe src="https://www.facebook.com/plugins/post.php?href=%s&show_text=true" '
                'title="Publicación de Facebook" loading="lazy" allowfullscreen></iframe></div>') % escape(url)
    return ('<p class="enllac-extern"><a href="%s" target="_blank" rel="noopener">'
            'Ver la publicación original</a></p>') % escape(url)


def video_propi(fitxer, poster=""):
    atrib_poster = ' poster="%s"' % escape(poster) if poster else ""
    return ('<figure class="video-propi"><video controls preload="metadata" playsinline%s>'
            '<source src="%s"><p>Tu navegador no puede reproducir este vídeo. '
            '<a href="%s">Descárgalo</a>.</p></video></figure>') % (
        atrib_poster, escape(fitxer), escape(fitxer))


# ------------------------------------------------------------------ markdown

RE_CODI = re.compile(r"`([^`]+)`")
RE_IMATGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]*)\")?\)")
RE_ENLLAC = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
RE_NEGRETA = re.compile(r"\*\*([^*]+)\*\*")
RE_CURSIVA = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)")
RE_DRECERA = re.compile(r"^\[\[\s*(video|embed|destacado|destacat|imagen|imatge)\s*:\s*(.+?)\s*\]\]$",
                        re.IGNORECASE)


def inline(text):
    """Formatea negrita, cursiva, enlaces, imagenes y codigo dentro de un parrafo."""
    text = escape(text, quote=False)
    guardats = []

    def guarda(fragment):
        guardats.append(fragment)
        return "\x00%d\x00" % (len(guardats) - 1)

    text = RE_CODI.sub(lambda m: guarda("<code>%s</code>" % m.group(1)), text)
    text = RE_IMATGE.sub(
        lambda m: guarda('<img src="%s" alt="%s" loading="lazy">' % (m.group(2), m.group(1))), text)

    def fes_enllac(m):
        adreca = m.group(2)
        atrib = ' target="_blank" rel="noopener"' if adreca.startswith("http") else ""
        return guarda('<a href="%s"%s>%s</a>' % (adreca, atrib, m.group(1)))

    text = RE_ENLLAC.sub(fes_enllac, text)
    text = RE_NEGRETA.sub(lambda m: "<strong>%s</strong>" % m.group(1), text)
    text = RE_CURSIVA.sub(lambda m: "<em>%s</em>" % m.group(1), text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: guardats[int(m.group(1))], text)
    return text


def drecera_a_html(nom, arguments):
    nom = nom.lower()
    parts = [p.strip() for p in arguments.split("|")]
    if nom == "video":
        return video_propi(parts[0], parts[1] if len(parts) > 1 else "")
    if nom == "embed":
        return incrusta(parts[0])
    if nom in ("destacado", "destacat"):
        return '<blockquote class="destacat">%s</blockquote>' % inline(parts[0])
    if nom in ("imagen", "imatge"):
        peu = ('<figcaption>%s</figcaption>' % inline(parts[1])) if len(parts) > 1 else ""
        return '<figure><img src="%s" alt="%s" loading="lazy">%s</figure>' % (
            escape(parts[0]), escape(parts[1] if len(parts) > 1 else ""), peu)
    return ""


def markdown(text):
    """Convierte un subconjunto de Markdown en HTML."""
    linies = text.replace("\r\n", "\n").split("\n")
    sortida = []
    i = 0
    while i < len(linies):
        net = linies[i].strip()

        if not net:
            i += 1
            continue

        if net.startswith("```"):
            i += 1
            bloc = []
            while i < len(linies) and not linies[i].strip().startswith("```"):
                bloc.append(linies[i])
                i += 1
            i += 1
            sortida.append("<pre><code>%s</code></pre>" % escape("\n".join(bloc)))
            continue

        m = RE_DRECERA.match(net)
        if m:
            sortida.append(drecera_a_html(m.group(1), m.group(2)))
            i += 1
            continue

        if re.match(r"^(-{3,}|\*{3,})$", net):
            sortida.append("<hr>")
            i += 1
            continue

        if net.startswith("#"):
            nivell = len(net) - len(net.lstrip("#"))
            nivell = min(max(nivell, 1), 6)
            contingut = net[nivell:].strip()
            etiqueta = "h%d" % min(nivell + 1, 6)
            sortida.append('<%s id="%s">%s</%s>' % (
                etiqueta, slugifica(contingut), inline(contingut), etiqueta))
            i += 1
            continue

        if net.startswith(">"):
            bloc = []
            while i < len(linies) and linies[i].strip().startswith(">"):
                bloc.append(linies[i].strip().lstrip(">").strip())
                i += 1
            sortida.append("<blockquote><p>%s</p></blockquote>" % inline(" ".join(bloc)))
            continue

        if re.match(r"^[-*]\s+", net):
            elements = []
            while i < len(linies) and re.match(r"^[-*]\s+", linies[i].strip()):
                elements.append(inline(re.sub(r"^[-*]\s+", "", linies[i].strip())))
                i += 1
            sortida.append("<ul>%s</ul>" % "".join("<li>%s</li>" % e for e in elements))
            continue

        if re.match(r"^\d+[.)]\s+", net):
            elements = []
            while i < len(linies) and re.match(r"^\d+[.)]\s+", linies[i].strip()):
                elements.append(inline(re.sub(r"^\d+[.)]\s+", "", linies[i].strip())))
                i += 1
            sortida.append("<ol>%s</ol>" % "".join("<li>%s</li>" % e for e in elements))
            continue

        paragraf = []
        while i < len(linies) and linies[i].strip() and not RE_DRECERA.match(linies[i].strip()) \
                and not linies[i].strip().startswith(("#", ">", "```")) \
                and not re.match(r"^([-*]\s+|\d+[.)]\s+|-{3,}$)", linies[i].strip()):
            paragraf.append(linies[i].strip())
            i += 1
        text_paragraf = inline(" ".join(paragraf))
        if text_paragraf.startswith("<figure") or text_paragraf.startswith("<img"):
            sortida.append(text_paragraf)
        else:
            sortida.append("<p>%s</p>" % text_paragraf)
    return "\n".join(sortida)


def resum_de(text, longitud=180):
    net = re.sub(r"\[\[.*?\]\]", " ", text)
    net = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", net)
    net = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", net)
    net = re.sub(r"(?m)^\s*[-*]\s+", "", net)
    net = re.sub(r"[#>*`_]", " ", net)
    net = re.sub(r"\s+", " ", net).strip()
    if len(net) <= longitud:
        return net
    return net[:longitud].rsplit(" ", 1)[0] + "…"


# ------------------------------------------------------------------ contenido

def carrega_articles(config):
    articles = []
    carpeta = DIR_CONTINGUT / "articles"
    noms_seccio = {s["slug"]: s["nom"] for s in config["seccions"]}
    per_defecte = config["seccions"][0]["slug"] if config["seccions"] else "sucesos"

    for fitxer in sorted(carpeta.glob("*.md")):
        dades, cos = separa_capcalera(fitxer.read_text(encoding="utf-8"))
        if camp(dades, "borrador", "esborrany") is True:
            continue

        titol = str(camp(dades, "titulo", "titol") or fitxer.stem.replace("-", " ").capitalize())
        slug = str(camp(dades, "slug") or slugifica(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", fitxer.stem)))
        seccio = slugifica(camp(dades, "seccion", "seccio") or per_defecte)
        data = analitza_data(camp(dades, "fecha", "data")
                             or datetime.fromtimestamp(fitxer.stat().st_mtime))
        etiquetes = camp(dades, "etiquetas", "etiquetes") or []
        if isinstance(etiquetes, str):
            etiquetes = [t.strip() for t in etiquetes.split(",") if t.strip()]

        cos_html = markdown(cos)
        paraules = len(re.sub(r"<[^>]+>", " ", cos_html).split())
        video = str(camp(dades, "video") or "")
        embed = str(camp(dades, "embed") or "")

        articles.append({
            "titol": titol,
            "subtitol": str(camp(dades, "subtitulo", "subtitol") or ""),
            "slug": slug,
            "url": "/noticia/%s/" % slug,
            "seccio": seccio,
            "seccio_nom": noms_seccio.get(seccio, seccio.replace("-", " ").capitalize()),
            "autor": str(camp(dades, "autor") or config.get("autor_per_defecte") or config["nom"]),
            "data": data,
            "imatge": str(camp(dades, "imagen", "imatge") or ""),
            "peu_imatge": str(camp(dades, "pie_imagen", "peu_imatge") or ""),
            "video": video,
            "video_poster": str(camp(dades, "video_poster") or ""),
            "embed": embed,
            "etiquetes": [str(t) for t in etiquetes if str(t).strip()],
            "destacat": camp(dades, "destacado", "destacat") is True,
            "ultima_hora": camp(dades, "ultima_hora") is True,
            "resum": str(camp(dades, "resumen", "resum") or resum_de(cos)),
            "cos": cos_html,
            "minuts": max(1, round(paraules / 200)),
            "te_video": bool(video or embed),
        })

    articles.sort(key=lambda a: a["data"], reverse=True)
    return articles


def carrega_pagines():
    pagines = []
    carpeta = DIR_CONTINGUT / "pagines"
    for fitxer in sorted(carpeta.glob("*.md")):
        dades, cos = separa_capcalera(fitxer.read_text(encoding="utf-8"))
        slug = str(camp(dades, "slug") or slugifica(fitxer.stem))
        pagines.append({
            "titol": str(camp(dades, "titulo", "titol") or fitxer.stem.replace("-", " ").capitalize()),
            "slug": slug,
            "url": "/%s/" % slug,
            "menu_peu": camp(dades, "menu_pie", "menu_peu") is not False,
            "cos": markdown(cos),
            "resum": str(camp(dades, "resumen", "resum") or resum_de(cos)),
        })
    return pagines


# --------------------------------------------------------------------- bloques

def anunci(config, posicio):
    pub = config.get("publicitat", {})
    client = str(pub.get("adsense_client") or "").strip()
    slot = str(pub.get("slot_%s" % posicio) or "").strip()
    if client and slot:
        return ('<div class="anunci" data-posicio="%s"><span class="anunci-etiqueta">Publicidad</span>'
                '<ins class="adsbygoogle" style="display:block" data-ad-client="%s" data-ad-slot="%s" '
                'data-ad-format="auto" data-full-width-responsive="true"></ins></div>') % (
            posicio, client, slot)
    propis = [b for b in pub.get("banners_propis", [])
              if str(b.get("imatge") or "").strip() and b.get("posicio", "article") == posicio]
    if propis:
        b = propis[0]
        img = '<img src="%s" alt="%s" loading="lazy">' % (
            escape(b["imatge"]), escape(str(b.get("alt") or "")))
        if str(b.get("enllac") or "").strip():
            img = '<a href="%s" target="_blank" rel="noopener sponsored">%s</a>' % (
                escape(b["enllac"]), img)
        return ('<div class="anunci anunci-propi" data-posicio="%s">'
                '<span class="anunci-etiqueta">Publicidad</span>%s</div>') % (posicio, img)
    return ""


def targeta(art, mida="normal"):
    if art["imatge"]:
        visual = '<img src="%s" alt="%s" loading="lazy">' % (escape(art["imatge"]), escape(art["titol"]))
    elif art["video_poster"]:
        visual = '<img src="%s" alt="%s" loading="lazy">' % (
            escape(art["video_poster"]), escape(art["titol"]))
    else:
        visual = '<span class="sense-imatge" aria-hidden="true">33</span>'
    marca_video = '<span class="marca-video" aria-hidden="true">▶</span>' if art["te_video"] else ""
    urgent = '<span class="marca-urgent">Última hora</span>' if art["ultima_hora"] else ""
    subtitol = ('<p class="targeta-entradeta">%s</p>' % escape(art["subtitol"])) \
        if art["subtitol"] and mida != "petita" else ""
    return ('<article class="targeta targeta-%s">'
            '<a class="targeta-imatge" href="%s">%s%s%s</a>'
            '<div class="targeta-cos">'
            '<a class="etiqueta-seccio" href="/seccion/%s/">%s</a>'
            '<h3><a href="%s">%s</a></h3>%s'
            '<p class="meta"><time datetime="%s">%s</time> · %s min</p>'
            '</div></article>') % (
        mida, escape(art["url"]), visual, marca_video, urgent,
        escape(art["seccio"]), escape(art["seccio_nom"]),
        escape(art["url"]), escape(art["titol"]), subtitol,
        art["data"].strftime("%Y-%m-%d"), data_llegible(art["data"]), art["minuts"])


def graella(articles, mida="normal"):
    if not articles:
        return '<p class="buit">Todavía no hay publicaciones en esta sección.</p>'
    return '<div class="graella">%s</div>' % "".join(targeta(a, mida) for a in articles)


def navegacio(config):
    enllacos = ['<a href="/">Portada</a>']
    for s in config["seccions"]:
        enllacos.append('<a href="/seccion/%s/">%s</a>' % (escape(s["slug"]), escape(s["nom"])))
    return "".join(enllacos)


def favicon(config):
    """Icona de pestanya: la imatge de la marca si n'hi ha, si no una de generada."""
    propia = str(config.get("favicon") or "").strip()
    if propia:
        return propia
    color = str(config.get("color_principal") or "#c3132b")
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
           "<rect width='100' height='100' fill='#0b0b0d'/>"
           "<text x='50' y='74' text-anchor='middle' font-family='Georgia,serif' "
           "font-style='italic' font-weight='bold' font-size='64' fill='%s'>33</text></svg>") % color
    return "data:image/svg+xml," + svg.replace("#", "%23")


def marca_html(config):
    """Cabecera de marca: el logo si lo hay, y si no el logotipo compuesto."""
    if str(config.get("logo") or "").strip():
        return '<img class="marca-logo" src="%s" alt="%s">' % (
            escape(config["logo"]), escape(config["nom"]))
    return ('<span class="marca-nom"><span class="marca-nom-principal">%s</span>'
            '<span class="marca-nom-accent">%s</span></span>') % (
        escape(str(config.get("nom_principal") or config["nom"])),
        escape(str(config.get("nom_accent") or "")))


def barra_ultima_hora(articles):
    urgents = [a for a in articles if a["ultima_hora"]][:3]
    if not urgents:
        return ""
    enllacos = "".join(
        '<a href="%s"><time datetime="%s">%02d:%02d</time> %s</a>' % (
            escape(a["url"]), a["data"].strftime("%Y-%m-%d"),
            a["data"].hour, a["data"].minute, escape(a["titol"]))
        for a in urgents)
    return ('<div class="ultima-hora"><div class="contenidor ultima-hora-cos">'
            '<span class="ultima-hora-marca">Última hora</span>'
            '<div class="ultima-hora-llista">%s</div></div></div>') % enllacos


def peu_de_pagina(config, pagines):
    xarxes = "".join(
        '<a href="%s" target="_blank" rel="noopener">%s</a>' % (escape(x["url"]), escape(x["nom"]))
        for x in config.get("xarxes", []) if str(x.get("url") or "").strip())
    enllacos = "".join('<a href="%s">%s</a>' % (escape(p["url"]), escape(p["titol"]))
                       for p in pagines if p["menu_peu"])
    correu = str(config.get("contacte", {}).get("email") or "").strip()
    contacte = '<a href="mailto:%s">%s</a>' % (escape(correu), escape(correu)) if correu else ""
    return ('<div class="peu-columnes">'
            '<div><span class="peu-marca">%s</span>%s</div>'
            '<div><h4>Secciones</h4><nav>%s</nav></div>'
            '<div><h4>El medio</h4><nav>%s</nav>%s</div>'
            '</div>') % (
        marca_html(config),
        ('<div class="peu-xarxes">%s</div>' % xarxes) if xarxes else "",
        "".join('<a href="/seccion/%s/">%s</a>' % (escape(s["slug"]), escape(s["nom"]))
                for s in config["seccions"]),
        enllacos, contacte)


# ----------------------------------------------------------------- plantilla

def metadades(config, titol, descripcio, ruta, imatge="", tipus="website", extra=""):
    base = config["url"]
    canonica = base + ruta if base else ruta
    img = imatge if imatge.startswith("http") else (base + imatge if (base and imatge) else imatge)
    etiquetes = [
        '<meta name="description" content="%s">' % escape(descripcio),
        '<link rel="canonical" href="%s">' % escape(canonica),
        '<meta property="og:type" content="%s">' % tipus,
        '<meta property="og:site_name" content="%s">' % escape(config["nom"]),
        '<meta property="og:title" content="%s">' % escape(titol),
        '<meta property="og:description" content="%s">' % escape(descripcio),
        '<meta property="og:url" content="%s">' % escape(canonica),
        '<meta property="og:locale" content="es_ES">',
        '<meta name="twitter:card" content="%s">' % ("summary_large_image" if img else "summary"),
        '<meta name="twitter:title" content="%s">' % escape(titol),
        '<meta name="twitter:description" content="%s">' % escape(descripcio),
    ]
    if img:
        etiquetes.append('<meta property="og:image" content="%s">' % escape(img))
        etiquetes.append('<meta name="twitter:image" content="%s">' % escape(img))
    if extra:
        etiquetes.append(extra)
    return "\n  ".join(etiquetes)


def escriu(ruta, contingut):
    desti = DIR_SORTIDA / ruta.lstrip("/")
    desti.parent.mkdir(parents=True, exist_ok=True)
    desti.write_text(contingut, encoding="utf-8")


def pagina(config, plantilla, pagines, titol, contingut, descripcio, ruta,
           imatge="", tipus="website", classe="", extra_head="", extra_body=""):
    titol_complet = titol if titol == config["nom"] else "%s | %s" % (titol, config["nom"])
    pub = config.get("publicitat", {})
    scripts = extra_body
    client = str(pub.get("adsense_client") or "").strip()
    if client:
        scripts += '\n<script>window.CLIENTE_ADSENSE="%s";</script>' % escape(client)
    analitica = config.get("analitica", {})
    if str(analitica.get("plausible_domini") or "").strip():
        scripts += ('\n<script defer data-domain="%s" src="https://plausible.io/js/script.js"></script>'
                    % escape(analitica["plausible_domini"]))

    reemplacos = {
        "IDIOMA": config.get("idioma", "es"),
        "TITOL": escape(titol_complet),
        "META": metadades(config, titol, descripcio, ruta, imatge, tipus, extra_head),
        "NOM": escape(config["nom"]),
        "MARCA": marca_html(config),
        "FAVICON": favicon(config),
        "LEMA": escape(str(config.get("lema") or "")),
        "COLOR": escape(str(config.get("color_principal") or "#c8102e")),
        "NAV": navegacio(config),
        "ULTIMA_HORA": BARRA_ULTIMA_HORA,
        "CONTINGUT": contingut,
        "PEU": peu_de_pagina(config, pagines),
        "ANY": str(datetime.now().year),
        "LEGAL": escape(str(config.get("peu_legal") or "")),
        "CLASSE": classe,
        "SCRIPTS": scripts,
    }
    sortida = plantilla
    for clau, valor in reemplacos.items():
        sortida = sortida.replace("{{%s}}" % clau, valor)
    escriu(ruta + "index.html" if ruta.endswith("/") else ruta, sortida)


def paginador(ruta_base, actual, total):
    if total <= 1:
        return ""

    def adreca(n):
        return ruta_base if n == 1 else "%s%d/" % (ruta_base, n)

    parts = []
    if actual > 1:
        parts.append('<a class="pag-prev" href="%s">← Anteriores</a>' % adreca(actual - 1))
    parts.append('<span class="pag-estat">Página %d de %d</span>' % (actual, total))
    if actual < total:
        parts.append('<a class="pag-seg" href="%s">Siguientes →</a>' % adreca(actual + 1))
    return '<nav class="paginacio">%s</nav>' % "".join(parts)


def comparteix(config, art):
    base = config["url"] + art["url"]
    text = art["titol"]
    return ('<div class="compartir"><span>Comparte:</span>'
            '<a href="https://wa.me/?text=%s" target="_blank" rel="noopener">WhatsApp</a>'
            '<a href="https://t.me/share/url?url=%s&text=%s" target="_blank" rel="noopener">Telegram</a>'
            '<a href="https://twitter.com/intent/tweet?url=%s&text=%s" target="_blank" rel="noopener">X</a>'
            '<a href="https://www.facebook.com/sharer/sharer.php?u=%s" target="_blank" rel="noopener">Facebook</a>'
            '<button type="button" class="copia-enllac" data-url="%s">Copiar enlace</button>'
            '</div>') % (escape(base + " " + text), escape(base), escape(text),
                         escape(base), escape(text), escape(base), escape(base))


# --------------------------------------------------------------- construccion

def construeix_portada(config, plantilla, pagines, articles):
    per_pagina = int(config["articles_per_pagina"])
    # L'obertura: la peça marcada com a destacada; si no n'hi ha, l'última hora
    # més recent; si tampoc, simplement la més recent.
    destacats = ([a for a in articles if a["destacat"]]
                 or [a for a in articles if a["ultima_hora"]]
                 or articles[:1])
    principal = destacats[0] if destacats else None
    # La resta: primer l'última hora, després per data.
    resta = sorted((a for a in articles if a is not principal),
                   key=lambda a: (not a["ultima_hora"], -a["data"].timestamp()))
    total = max(1, -(-len(resta) // per_pagina)) if resta else 1

    for num in range(1, total + 1):
        tros = resta[(num - 1) * per_pagina: num * per_pagina]
        blocs = []
        if num == 1 and principal:
            visual = ""
            if principal["imatge"]:
                visual = '<a href="%s" class="obertura-imatge"><img src="%s" alt="%s"></a>' % (
                    escape(principal["url"]), escape(principal["imatge"]), escape(principal["titol"]))
            elif principal["video"]:
                visual = video_propi(principal["video"], principal["video_poster"])
            elif principal["embed"]:
                visual = incrusta(principal["embed"])
            blocs.append(
                '<section class="obertura">%s<div class="obertura-text">'
                '<a class="etiqueta-seccio" href="/seccion/%s/">%s</a>'
                '<h2><a href="%s">%s</a></h2><p class="entradeta">%s</p>'
                '<p class="meta">%s &middot; <time datetime="%s">%s</time></p></div></section>' % (
                    visual, escape(principal["seccio"]), escape(principal["seccio_nom"]),
                    escape(principal["url"]), escape(principal["titol"]),
                    escape(principal["subtitol"] or principal["resum"]),
                    escape(principal["autor"]), principal["data"].strftime("%Y-%m-%d"),
                    data_hora_llegible(principal["data"])))
            blocs.append(anunci(config, "capcalera"))
        if tros:
            blocs.append('<h2 class="titol-seccio">%s</h2>' % (
                "Últimas publicaciones" if num == 1 else "Más publicaciones"))
            blocs.append(graella(tros))
            blocs.append(paginador("/", num, total))
        ruta = "/" if num == 1 else "/%d/" % num
        pagina(config, plantilla, pagines,
               config["nom"] if num == 1 else "Portada, página %d" % num,
               "\n".join(b for b in blocs if b),
               str(config.get("descripcio") or config.get("lema") or ""),
               ruta, principal["imatge"] if principal else "", classe="portada")


def construeix_seccions(config, plantilla, pagines, articles):
    per_pagina = int(config["articles_per_pagina"])
    for s in config["seccions"]:
        propies = [a for a in articles if a["seccio"] == s["slug"]]
        total = max(1, -(-len(propies) // per_pagina))
        for num in range(1, total + 1):
            tros = propies[(num - 1) * per_pagina: num * per_pagina]
            ruta_base = "/seccion/%s/" % s["slug"]
            cos = ('<header class="capcalera-seccio"><h1>%s</h1><p>%d publicaciones</p></header>%s%s%s' % (
                escape(s["nom"]), len(propies), anunci(config, "capcalera"),
                graella(tros), paginador(ruta_base, num, total)))
            pagina(config, plantilla, pagines, s["nom"], cos,
                   "Todas las noticias, artículos y reportajes de %s en %s." % (s["nom"], config["nom"]),
                   ruta_base if num == 1 else "%s%d/" % (ruta_base, num), classe="llistat")


def construeix_etiquetes(config, plantilla, pagines, articles):
    mapa = {}
    for a in articles:
        for t in a["etiquetes"]:
            mapa.setdefault(slugifica(t), {"nom": t, "articles": []})["articles"].append(a)
    for slug, dades in mapa.items():
        cos = ('<header class="capcalera-seccio"><h1>#%s</h1><p>%d publicaciones</p></header>%s' % (
            escape(dades["nom"]), len(dades["articles"]), graella(dades["articles"])))
        pagina(config, plantilla, pagines, "#" + dades["nom"], cos,
               "Publicaciones etiquetadas como %s." % dades["nom"],
               "/etiqueta/%s/" % slug, classe="llistat")
    return mapa


def construeix_articles(config, plantilla, pagines, articles):
    for art in articles:
        capcalera_visual = ""
        if art["imatge"]:
            peu = ('<figcaption>%s</figcaption>' % escape(art["peu_imatge"])) if art["peu_imatge"] else ""
            capcalera_visual = '<figure class="portada-article"><img src="%s" alt="%s">%s</figure>' % (
                escape(art["imatge"]), escape(art["titol"]), peu)
        reproductor = ""
        if art["video"]:
            reproductor += video_propi(art["video"], art["video_poster"])
        if art["embed"]:
            reproductor += incrusta(art["embed"])
        etiquetes = "".join('<a href="/etiqueta/%s/">#%s</a>' % (slugifica(t), escape(t))
                            for t in art["etiquetes"])
        relacionats = [a for a in articles if a["seccio"] == art["seccio"] and a is not art][:3]
        if len(relacionats) < 3:
            for a in articles:
                if len(relacionats) >= 3:
                    break
                if a is not art and a not in relacionats:
                    relacionats.append(a)

        json_ld = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": art["titol"],
            "description": art["resum"],
            "datePublished": art["data"].isoformat(),
            "dateModified": art["data"].isoformat(),
            "inLanguage": "es",
            "author": {"@type": "Person", "name": art["autor"]},
            "publisher": {"@type": "Organization", "name": config["nom"]},
            "mainEntityOfPage": config["url"] + art["url"],
        }
        if art["imatge"]:
            json_ld["image"] = [art["imatge"] if art["imatge"].startswith("http")
                                else config["url"] + art["imatge"]]

        distintiu = '<span class="distintiu-urgent">Última hora</span>' if art["ultima_hora"] else ""
        cos = (
            '<article class="article">'
            '<header class="capcalera-article">'
            '%s<a class="etiqueta-seccio" href="/seccion/%s/">%s</a>'
            '<h1>%s</h1>%s'
            '<p class="meta">Por %s &middot; <time datetime="%s">%s</time> &middot; %s min de lectura</p>'
            '%s</header>'
            '%s%s'
            '<div class="cos-article">%s</div>'
            '%s'
            '<footer class="peu-article">%s%s</footer>'
            '</article>'
            '<section class="relacionats"><h2 class="titol-seccio">Sigue leyendo</h2>%s</section>'
        ) % (
            distintiu, escape(art["seccio"]), escape(art["seccio_nom"]), escape(art["titol"]),
            ('<p class="entradeta">%s</p>' % escape(art["subtitol"])) if art["subtitol"] else "",
            escape(art["autor"]), art["data"].strftime("%Y-%m-%d"),
            data_hora_llegible(art["data"]), art["minuts"],
            comparteix(config, art),
            capcalera_visual, reproductor,
            art["cos"],
            anunci(config, "article"),
            ('<div class="etiquetes">%s</div>' % etiquetes) if etiquetes else "",
            comparteix(config, art),
            graella(relacionats, "petita"))

        pagina(config, plantilla, pagines, art["titol"], cos, art["resum"], art["url"],
               art["imatge"] or art["video_poster"], tipus="article", classe="detall",
               extra_head='<script type="application/ld+json">%s</script>'
                          % json.dumps(json_ld, ensure_ascii=False))


def construeix_pagines(config, plantilla, pagines):
    for p in pagines:
        cos = '<article class="pagina"><h1>%s</h1><div class="cos-article">%s</div></article>' % (
            escape(p["titol"]), p["cos"])
        pagina(config, plantilla, pagines, p["titol"], cos, p["resum"], p["url"], classe="detall")


def construeix_cerca(config, plantilla, pagines, articles):
    index = [{"t": a["titol"], "s": a["subtitol"], "r": a["resum"], "u": a["url"],
              "sec": a["seccio_nom"], "d": data_llegible(a["data"]),
              "img": a["imatge"] or a["video_poster"],
              "tags": " ".join(a["etiquetes"])} for a in articles]
    escriu("/buscar.json", json.dumps(index, ensure_ascii=False))
    cos = ('<header class="capcalera-seccio"><h1>Buscar</h1></header>'
           '<form class="form-cerca" onsubmit="return false"><input type="search" id="camp-cerca" '
           'placeholder="Busca noticias, sucesos, nombres&hellip;" autocomplete="off" autofocus></form>'
           '<div id="resultats-cerca"></div>')
    pagina(config, plantilla, pagines, "Buscar", cos, "Busca dentro de %s." % config["nom"],
           "/buscar/", classe="llistat")


def construeix_feeds(config, articles, pagines):
    base = config["url"]
    items = []
    for a in articles[:30]:
        items.append(
            '<item><title>%s</title><link>%s</link><guid isPermaLink="true">%s</guid>'
            '<pubDate>%s</pubDate><category>%s</category><description>%s</description></item>' % (
                escape(a["titol"]), escape(base + a["url"]), escape(base + a["url"]),
                a["data"].strftime("%a, %d %b %Y %H:%M:%S +0000"),
                escape(a["seccio_nom"]), escape(a["resum"])))
    escriu("/rss.xml",
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0"><channel><title>%s</title><link>%s</link>'
           '<description>%s</description><language>%s</language>%s</channel></rss>' % (
               escape(config["nom"]), escape(base), escape(str(config.get("descripcio") or "")),
               config.get("idioma", "es"), "".join(items)))

    urls = ["/", "/buscar/"]
    urls += ["/seccion/%s/" % s["slug"] for s in config["seccions"]]
    urls += [p["url"] for p in pagines]
    urls += [a["url"] for a in articles]
    entrades = "".join(
        "<url><loc>%s</loc><changefreq>daily</changefreq></url>" % escape(base + u) for u in urls)
    escriu("/sitemap.xml",
           '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>' % entrades)
    escriu("/robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % base)


def copia_estatics():
    for nom in ("estil.css", "app.js"):
        origen = DIR_TEMA / nom
        if origen.exists():
            shutil.copy2(origen, DIR_SORTIDA / nom)
    if DIR_MEDIA.exists():
        shutil.copytree(DIR_MEDIA, DIR_SORTIDA / "media", dirs_exist_ok=True)
    for extra in ("_headers", "_redirects"):
        if (ARREL / extra).exists():
            shutil.copy2(ARREL / extra, DIR_SORTIDA / extra)


def main():
    global BARRA_ULTIMA_HORA

    config = llegeix_config()
    plantilla = (DIR_TEMA / "base.html").read_text(encoding="utf-8")
    articles = carrega_articles(config)
    pagines = carrega_pagines()
    BARRA_ULTIMA_HORA = barra_ultima_hora(articles)

    if DIR_SORTIDA.exists():
        for element in DIR_SORTIDA.iterdir():
            if element.is_dir():
                shutil.rmtree(element, ignore_errors=True)
            else:
                try:
                    element.unlink()
                except OSError:
                    pass
    DIR_SORTIDA.mkdir(parents=True, exist_ok=True)

    copia_estatics()
    construeix_portada(config, plantilla, pagines, articles)
    construeix_seccions(config, plantilla, pagines, articles)
    etiquetes = construeix_etiquetes(config, plantilla, pagines, articles)
    construeix_articles(config, plantilla, pagines, articles)
    construeix_pagines(config, plantilla, pagines)
    construeix_cerca(config, plantilla, pagines, articles)
    construeix_feeds(config, articles, pagines)
    pagina(config, plantilla, pagines, "Página no encontrada",
           '<section class="capcalera-seccio"><h1>404</h1>'
           '<p>Esta página no existe o se ha movido.</p>'
           '<p><a class="boto" href="/">Volver a la portada</a></p></section>',
           "Página no encontrada", "/404.html", classe="llistat")

    print("Generado en %s" % DIR_SORTIDA)
    print("  %d publicaciones | %d secciones | %d etiquetas | %d paginas fijas" % (
        len(articles), len(config["seccions"]), len(etiquetes), len(pagines)))
    if not config["url"]:
        print("  AVISO: 'url' vacia en config.json (hace falta para el SEO y para compartir).")


if __name__ == "__main__":
    main()
    if "--servir" in sys.argv:
        from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

        class Gestor(SimpleHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(DIR_SORTIDA), **kwargs)

            def end_headers(self):
                self.send_header("Cache-Control", "no-store")
                super().end_headers()

            def log_message(self, format, *args):
                pass

        servidor = ThreadingHTTPServer(("127.0.0.1", 8000), Gestor)
        print("Sirviendo en http://localhost:8000  (Ctrl+C para parar)")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            servidor.server_close()
