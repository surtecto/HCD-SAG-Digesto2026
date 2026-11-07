#!/usr/bin/env python3
"""Digesto Gilense — actualizador de novedades.

1. Lee las ordenanzas nuevas que el H.C.D. entrega en Word (novedades/ordenanzas/*.docx).
2. Consulta el SIBOM (Boletín Oficial Municipal, municipio 111) y busca, en los boletines
   todavía no revisados, decretos del Departamento Ejecutivo que promulguen o veten ordenanzas.
3. Calcula el estado de cada ordenanza nueva (promulgada, vetada, en plazo, promulgación
   tácita presunta por art. 108 inc. 2 de la Ley Orgánica de las Municipalidades).
4. Escribe digesto-novedades.js, que index.html lee al abrir.

Sólo usa la biblioteca estándar de Python. Uso:
    python herramientas/actualizar_novedades.py            # todo
    python herramientas/actualizar_novedades.py --sin-sibom
"""
import datetime as dt
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
import zipfile
from xml.etree import ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_ORD = os.path.join(RAIZ, 'novedades', 'ordenanzas')
F_REL = os.path.join(RAIZ, 'novedades', 'relaciones.json')
F_EST = os.path.join(RAIZ, 'novedades', 'estado-sibom.json')
F_OUT = os.path.join(RAIZ, 'digesto-novedades.js')
F_IDX = os.path.join(RAIZ, 'index.html')
SIBOM = 'https://sibom.slyt.gba.gob.ar'
MUNI = 111
HOY = dt.date.today()

MESES = {m: i + 1 for i, m in enumerate(
    'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split())}
MESES['setiembre'] = 9

# Feriados nacionales (para estimar los 10 días hábiles del art. 108 inc. 2 LOM).
FERIADOS = {
    '2026-01-01', '2026-02-16', '2026-02-17', '2026-03-23', '2026-03-24', '2026-04-02', '2026-04-03',
    '2026-05-01', '2026-05-25', '2026-06-15', '2026-06-20', '2026-07-09', '2026-07-10', '2026-08-17',
    '2026-10-12', '2026-11-23', '2026-12-07', '2026-12-08', '2026-12-25',
    '2027-01-01', '2027-02-08', '2027-02-09', '2027-03-24', '2027-03-25', '2027-03-26', '2027-04-02',
    '2027-05-01', '2027-05-25', '2027-06-17', '2027-06-20', '2027-07-09', '2027-08-17', '2027-10-11',
    '2027-11-22', '2027-12-08', '2027-12-25',
}
DIAS_NOTIF = 5      # margen supuesto entre la sesión y la notificación al D.E.
DIAS_VETO = 10      # art. 108 inc. 2 LOM

INTENDENTES = [  # desde, texto de autoridades
    ('2021-12-06', 'Int. Sr. Miguel Ángel Gesualdi'),
    ('2015-12-10', 'Int. Cr. Carlos Javier Puglelli'),
]

# Clasificación automática para ordenanzas sin corrección manual: (patrón, materia, categoría)
REGLAS = [
    (r'presupuesto|c[aá]lculo de recursos', 'II', 'Presupuesto y cálculo de recursos'),
    (r'fiscal|impositiva|tasa', 'II', 'Ordenanza fiscal e impositiva — tasas y derechos'),
    (r'exim|condon|exenci', 'II', 'Eximiciones, exenciones y condonaciones'),
    (r'salari|personal municipal|escalaf', 'I', 'Personal municipal y del Cuerpo'),
    (r'consejo|comisi[oó]n asesora', 'I', 'Consejos, comisiones y organismos asesores'),
    (r'nombre.*(calle|barrio|camino)|(calle|barrio).*nombre|denominaci[oó]n.*calle', 'XI', 'Imposición de nombres a calles y caminos'),
    (r'nombre.*(plaza|espacio|edificio)|(plaza|espacio).*nombre', 'XI', 'Denominación de plazas, edificios y espacios'),
    (r'mensura|subdivisi|loteo|fracciona|visado de plano', 'III', 'Fraccionamientos, subdivisiones y apertura de calles'),
    (r'cesi[oó]n|donaci[oó]n|escritur|dominio', 'III', 'Dominio municipal, catastro y transferencias'),
    (r'convenio urban|zonific|uso conforme|c[oó]digo de ordenamiento', 'III', 'Planeamiento urbano y zonificación'),
    (r'arbol|arbolado|espacio verde', 'V', 'Arbolado público, espacios verdes y biodiversidad'),
    (r'agroqu|fitosanit', 'V', 'Agroquímicos, producción sustentable y periurbano'),
    (r'residuo', 'V', 'Residuos sólidos urbanos y saneamiento'),
    (r'tr[aá]nsito|estacionamiento|vehículo|monopat|motos', 'VIII', 'Tránsito, seguridad vial y estacionamiento'),
    (r'ganader|agropecuar|rural|chacinad', 'VI', 'Producción agropecuaria y ruralidad'),
    (r'hospital|salud|anestes|m[eé]dic', 'VII', 'Salud pública y hospital municipal'),
    (r'escuela|educaci', 'VII', 'Educación y formación'),
    (r'cultura|patrimonio|museo', 'VII', 'Cultura, patrimonio e identidad local'),
    (r'adhesi[oó]n|adhi[eé]r', 'X', 'Adhesiones a leyes nacionales y provinciales'),
    (r'convenio', 'X', 'Convenios con Nación, Provincia y entes'),
    (r'inter[eé]s municipal|declara', 'X', 'Declaraciones de interés y reconocimientos'),
]

REGLAS_HCD = [
    (r'reconoc|homenaje|distinci|destacad', 'X', 'Declaraciones de interés y reconocimientos'),
    (r'inter[eé]s (legislativo|municipal|cultural)', 'X', 'Declaraciones de interés y reconocimientos'),
    (r'repudi|rechazo|preocupaci|benepl[aá]cito|adhesi[oó]n a la jornada|solidaridad', 'X', 'Beneplácitos, repudios y pronunciamientos'),
    (r'solicit|requer|inform|pedido', 'X', 'Pedidos de informes y requerimientos al D.E.'),
    (r'rendici[oó]n de cuentas', 'II', 'Rendición de cuentas y control'),
    (r'reglamento interno|licencia|incorpora.*concejal', 'I', 'Reglamento y funcionamiento del H.C.D.'),
]

UA = 'DigestoGilense/1.0 (actualizador del Digesto de San Andres de Giles)'


def nrm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


def dia_habil(d):
    return d.weekday() < 5 and d.isoformat() not in FERIADOS


def suma_habiles(d, n):
    while n > 0:
        d += dt.timedelta(days=1)
        if dia_habil(d):
            n -= 1
    return d


# ---------------------------------------------------------------- Word
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def leer_docx(ruta):
    with zipfile.ZipFile(ruta) as z:
        raiz = ET.fromstring(z.read('word/document.xml'))
    pars = []
    for p in raiz.iter(W + 'p'):
        partes = []
        for el in p.iter():
            if el.tag == W + 't':
                partes.append(el.text or '')
            elif el.tag in (W + 'tab',):
                partes.append(' ')
            elif el.tag in (W + 'br', W + 'cr'):
                partes.append('\n')
        t = re.sub(r'[ \t ]+', ' ', ''.join(partes)).strip()
        if t:
            pars.append(t)
    return pars


def fecha_txt(s):
    m = re.search(r'(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:del?\s+)?(?:a[ñn]o\s+)?(\d{4})', s, re.I)
    if not m or nrm(m.group(2)) not in MESES:
        return None
    try:
        return dt.date(int(m.group(3)), MESES[nrm(m.group(2))], int(m.group(1)))
    except ValueError:
        return None


def autoridad(d):
    if not d:
        return ''
    for desde, au in INTENDENTES:
        if d.isoformat() >= desde:
            return au
    return ''


TIPO_NOM = {'ord': 'Ordenanza', 'res': 'Resolución', 'com': 'Comunicación'}


def ficha(pars, t, n, y_titulo, a, archivo, rel):
    """Arma los datos de un instrumento a partir de sus párrafos de texto."""
    texto = '\n'.join(pars)
    ms = re.search(r'Dada en (Sesi[oó]n\s+\w+)[^\n]*?el d[ií]a\s+([^\n]+)', texto, re.I) \
        or re.search(r'(Sesi[oó]n\s+(?:Ordinaria|Extraordinaria|Especial|Preparatoria))[^\n]{0,120}?(\d{1,2}\s+de\s+[a-záéíóú]+\s+(?:de|del)\s+\d{4})', texto, re.I)
    fe = fecha_txt(ms.group(2)) if ms else None
    se = re.sub(r'^Sesi[oó]n', 'Sesión', ms.group(1).strip().title()) if ms else ''
    y = y_titulo or (fe.year if fe else None)
    vi = ''
    iv = next((i for i, p in enumerate(pars) if re.match(r'^\s*VISTO\b', p, re.I)), None)
    if iv is not None:
        bloque = []
        primero = re.sub(r'^\s*VISTO\s*:?\s*', '', pars[iv], flags=re.I)
        if primero:
            bloque.append(primero)
        for p in pars[iv + 1:]:
            if re.match(r'^\s*CONSIDERANDO', p, re.I):
                break
            bloque.append(p)
        vi = ' '.join(bloque)[:600]
    if not a:
        art = re.search(r'Art[ií]culo\s*1[°º]?\s*[:.\-–]\s*([^\n]+)', texto, re.I)
        a = art.group(1)[:240] if art else f'{TIPO_NOM[t]} {n}'
    rz, c = (rel.get('clasificacion', {}).get(str(n), (None, None)) if t == 'ord' else (None, None))
    if not rz:
        base = nrm(a + ' ' + vi)
        rz, c = '0', 'Requiere lectura del documento'
        reglas = REGLAS if t == 'ord' else REGLAS_HCD + REGLAS
        for pat, r1, c1 in reglas:
            if re.search(pat, base):
                rz, c = r1, c1
                break
    return {
        't': t, 'n': n, 'y': y, 'a': a, 'fe_iso': fe.isoformat() if fe else None,
        'fe': fe and f'{fe.day} de {list(MESES)[fe.month - 1]} de {fe.year}',
        'se': se or 'Sesión', 'vi': vi, 'texto': texto, 'archivo': archivo,
        'rz': rz, 'c': c, 'au': autoridad(fe),
    }


def leer_ordenanza(ruta, rel):
    nombre = os.path.basename(ruta)
    pars = leer_docx(ruta)
    texto = '\n'.join(pars)
    m = re.search(r'ORDENANZA\s*N[°º.o]*\s*([\d.]+)', texto, re.I)
    mf = re.search(r'Ord0*(\d+)', nombre)
    n = int((m.group(1) if m else mf.group(1)).replace('.', ''))
    my = re.match(r'(\d{4})-', nombre)
    msum = re.search(r'\((.+)\)\s*\.docx$', nombre, re.I)
    o = ficha(pars, 'ord', n, None, msum.group(1).strip() if msum else '', nombre, rel)
    if not o['y']:
        o['y'] = int(my.group(1)) if my else HOY.year
    o['fuente'] = 'Texto entregado por la Secretaría del H.C.D.'
    return o


def efectos_auto(texto):
    """Detecta derogaciones y modificaciones expresas en la parte dispositiva."""
    i = re.search(r'\n\s*O\s*R\s*D\s*E\s*N\s*A\s*N\s*Z\s*A\s*:?\s*\n', texto)
    disp = texto[i.end():] if i else texto
    out = []
    for m in re.finditer(r'(abr[oó]g|derog|modif[ií]c|sustit[uú]y|incorp[oó]r)\w*[^.\n]{0,80}?Ordenanzas?\s*(?:Municipal(?:es)?\s*)?N[°º.o]*\s*([\d.]+)\s*/\s*(\d{2,4})', disp, re.I):
        verbo = nrm(m.group(1))
        acc = 'Deroga' if verbo.startswith(('abro', 'dero')) else 'Modifica'
        n = int(m.group(2).replace('.', ''))
        y = int(m.group(3))
        y = y if y > 999 else (2000 + y if y < 50 else 1900 + y)
        out.append(['ord', n, y, acc])
    return out


# ---------------------------------------------------------------- SIBOM
def traer(url, intentos=3):
    for k in range(intentos):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'es-AR'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:  # noqa: BLE001
            if k == intentos - 1:
                raise
            time.sleep(3 + 4 * k)


def texto_html(h):
    h = re.sub(r'(?is)<(script|style).*?</\1>', ' ', h)
    h = re.sub(r'(?i)<br\s*/?>|</p>|</div>', '\n', h)
    return html.unescape(re.sub(r'<[^>]+>', ' ', h))


RX_DEC = re.compile(r'Decreto\s*N[°º]?\s*(\d+)\s*/\s*(\d{2,4})\s*San Andr[ée]s de Giles,\s*(\d{2}/\d{2}/\d{4})', re.I)
NUM = r'(?:Ordenanza\s*N[°º.o]*|registro\s+llevar[aá]\s+el\s+n[°º.o]*|registrada\s+(?:bajo|con)\s+el\s+n[°º.o]*|bajo\s+el\s+n[°º.o]*)\s*([\d.]{3,6})(?:\s*/\s*(\d{2,4}))?'
RX_PROM = re.compile(r'(Prom[uú]lg[a-z]*|T[eé]ngase\s+por\s+promulgada)\b[^;]{0,700}?' + NUM, re.I)
RX_VETO = re.compile(r'(V[eé]t[a-z]*|Observ[a-z]*)\s*(total|parcial)?[a-z]*\b[^;]{0,700}?' + NUM, re.I)


def anio4(s, ref):
    if not s:
        return ref
    v = int(s)
    return v if v > 999 else 2000 + v


def revisar_sibom(estado):
    vistos = set(estado.get('boletines_revisados', []))
    halla = estado.setdefault('decretos', {})
    pag = traer(f'{SIBOM}/cities/{MUNI}')
    boletines = re.findall(r'bulletin-title">\s*([^<]+?)\s*</p>\s*<p class="bulletin-date">\s*Publicado el\s*([\d/]+)\s*</p>.*?action="/bulletins/(\d+)"', pag, re.S)
    if not boletines:
        raise RuntimeError('no se reconoció la lista de boletines del SIBOM')
    nuevos = [b for b in boletines if b[2] not in vistos]
    for titulo, publ, bid in reversed(nuevos):
        bh = traer(f'{SIBOM}/bulletins/{bid}')
        enl = list(dict.fromkeys(re.findall(rf'/bulletins/{bid}/contents/(\d+)', bh)))
        n_hall = 0
        for cid in enl:
            try:
                t = texto_html(traer(f'{SIBOM}/bulletins/{bid}/contents/{cid}'))
            except Exception:  # noqa: BLE001
                continue
            t = re.sub(r'\s+', ' ', t)
            md = RX_DEC.search(t)
            if not md:
                continue
            dnum, dy, dfe = int(md.group(1)), anio4(md.group(2), 0), md.group(3)
            cuerpo = t[md.end():]
            art = re.search(r'Art[ií]culo\s*1[°º]?\s*[:.\-–]?(.{0,900})', cuerpo, re.I)
            zona = art.group(1) if art else cuerpo[:1500]
            for rx, tipo in ((RX_PROM, 'prom'), (RX_VETO, 'veto')):
                for m in rx.finditer(zona):
                    gn = 2 if tipo == 'prom' else 3
                    on, oy = int(m.group(gn).replace('.', '')), anio4(m.group(gn + 1), dy)
                    if tipo == 'prom':
                        est = 'tacita_decreto' if re.match(r't[eé]ngase', m.group(1), re.I) else 'promulgada'
                    else:
                        est = 'vetada_parcial' if (m.group(2) or '').lower().startswith('parc') or re.search(r'parcial', m.group(0), re.I) else 'vetada_total'
                    if on < 100:
                        continue
                    d1, m1, y1 = dfe.split('/')
                    halla[f'{on}-{oy}'] = {
                        'estado': est, 'decreto': f'{dnum}/{str(dy)[-2:]}', 'fecha': f'{y1}-{m1}-{d1}',
                        'boletin': titulo, 'publicado': '-'.join(reversed(publ.split('/'))),
                        'url': f'{SIBOM}/bulletins/{bid}/contents/{cid}',
                    }
                    n_hall += 1
            time.sleep(0.4)
        vistos.add(bid)
        print(f'  SIBOM {titulo} ({publ}): {len(enl)} piezas, {n_hall} promulgaciones o vetos')
    estado['boletines_revisados'] = sorted(vistos, key=int)
    estado['ultimo_boletin'] = boletines[0][0] + ' · ' + boletines[0][1]
    return estado


# ---------------------------------------------------------------- corpus existente
def corpus_existente():
    try:
        with open(F_IDX, encoding='utf-8') as f:
            s = f.read()
        m = re.search(r'<script[^>]*id="payload"[^>]*>(.*?)</script>', s, re.S)
        D = json.loads(m.group(1))['d']
        return {(r['t'], r['n'], r['y']): r for r in D if r.get('n')}
    except Exception as e:  # noqa: BLE001
        print('  aviso: no se pudo leer el corpus de index.html:', e)
        return {}


# ---------------------------------------------------------------- sitio del H.C.D.
HCD = 'https://hcdsanandresdegiles.com.ar'
F_HCD = os.path.join(RAIZ, 'novedades', 'hcd-cache.json')
CAT_HCD = {37: 'ord', 28: 'res', 23: 'com'}   # categorías de WordPress del sitio del Concejo
RX_TIT = re.compile(r'^\s*(?:(\d{4})\s*[-–]?\s*)?(Ord|Resol|Res|Com)[a-z]*\.?\s*[-–.]?\s*0*(\d{1,4})(?:\s*[-–/]\s*(\d{2,4}))?\s*(?:[-–]\s*)?(?:\((.*?)\)?\s*)?', re.I)


def leer_pdf(datos):
    try:
        import io
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        r = PdfReader(io.BytesIO(datos))
        t = '\n'.join((pg.extract_text() or '') for pg in r.pages)
    except Exception:  # noqa: BLE001
        return None
    lineas = [re.sub(r'[ \t\u00a0]+', ' ', x).strip() for x in t.splitlines()]
    # une renglones cortados dentro de un mismo párrafo
    pars, cur = [], ''
    for x in lineas:
        if not x:
            if cur:
                pars.append(cur); cur = ''
            continue
        nuevo = re.match(r'^(Art[ií]culo|ART[IÍ]CULO|VISTO|Visto|CONSIDERANDO|Considerando|Que\b|Por ello|ORDENANZA|RESOLUCI|COMUNICACI|Dada en|[A-Z]\)|\d+\))', x)
        if cur and (nuevo or cur.endswith(('.', ':', ';'))):
            pars.append(cur); cur = x
        else:
            cur = (cur + ' ' + x).strip()
    if cur:
        pars.append(cur)
    return pars


def revisar_hcd(corpus, ya, rel, cache):
    """Busca en el sitio del Concejo ordenanzas, resoluciones y comunicaciones que no estén en el Digesto."""
    posts = cache.setdefault('posts', {})
    desde = cache.get('ultima_revision')
    nuevos = 0
    for cat, t in CAT_HCD.items():
        for pag in range(1, 80):
            url = f'{HCD}/wp-json/wp/v2/posts?categories={cat}&per_page=100&page={pag}&_fields=id,date,modified,title,link'
            if desde:
                url += '&modified_after=' + desde
            try:
                lote = json.loads(traer(url))
            except Exception as e:  # noqa: BLE001
                if pag > 1 and '400' in str(e):
                    break
                raise
            if not lote:
                break
            for p in lote:
                pid = str(p['id'])
                if pid in posts and posts[pid].get('mod') == p['modified']:
                    continue
                tit = html.unescape(p['title']['rendered'])
                m = RX_TIT.match(tit)
                reg = {'mod': p['modified'], 'fecha_post': p['date'][:10], 'titulo': tit, 'link': p['link'], 't': t}
                if not m:
                    reg['omitido'] = 'título sin número'
                    posts[pid] = reg
                    continue
                y = m.group(1) or m.group(4)
                reg.update(n=int(m.group(3)), y=anio4(y, 0) if y else None, a=(m.group(5) or '').strip(' )'))
                posts[pid] = reg
                nuevos += 1
            if len(lote) < 100:
                break
    print(f'  sitio del H.C.D.: {nuevos} publicaciones nuevas o modificadas')
    # completar con PDF sólo lo que falta en el Digesto
    falta = lambda r: hcd_falta(r, corpus, ya)
    for pid, r in posts.items():
        if not falta(r) or r.get('texto_ok') == r['mod']:
            continue
        try:
            cont = json.loads(traer(f"{HCD}/wp-json/wp/v2/posts/{pid}?_fields=content"))['content']['rendered']
        except Exception:  # noqa: BLE001
            continue
        txt = re.sub(r'\s+', ' ', texto_html(cont))
        me = re.search(r'ESTADO:?\s*([A-Za-zÁÉÍÓÚáéíóúñ ]+?)\s*(?:DESCARGAR|$)', txt)
        mi = re.search(r'INGRESADO EL:?\s*(\d{1,2}/\d{1,2}/\d{4})', txt)
        ma = re.search(r'AUTOR:?\s*(.*?)\s*ESTADO', txt)
        r['estado_hcd'] = (me.group(1).strip() if me else '')
        r['ingresado'] = mi.group(1) if mi else ''
        r['autor'] = (ma.group(1).strip() if ma else '')
        pdfs = [u for u in re.findall(r'href="([^"]+\.pdf)"', cont, re.I)]
        r['pdf'] = pdfs[0] if pdfs else ''
        r['texto_ok'] = r['mod']
        if r['pdf']:
            try:
                req = urllib.request.Request(r['pdf'], headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    pars = leer_pdf(resp.read())
                if pars:
                    r['pars'] = pars
            except Exception as e:  # noqa: BLE001
                r['pdf_error'] = str(e)[:120]
        time.sleep(0.3)
    cache['ultima_revision'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    return revisar_hcd_armar(corpus, ya, rel, cache)


def hcd_falta(r, corpus, ya):
    t, n, y = r['t'], r.get('n'), r.get('y')
    if not n or r.get('omitido'):
        return False
    if t == 'ord' and n >= 100 and (any(k[0] == 'ord' and k[1] == n and (k[2] or 0) >= 1993 for k in corpus) or ('ord', n) in ya):
        return False   # serie continua de ordenanzas: el número no se repite
    if y and ((t, n, y) in corpus or (t, n, y) in ya):
        return False
    return True


def revisar_hcd_armar(corpus, ya, rel, cache):
    posts = cache.get('posts', {})
    falta = lambda r: hcd_falta(r, corpus, ya)
    # armar fichas (el sitio repite algunas publicaciones: queda la que tiene texto)
    salida, vistos = [], {}
    for pid, r in posts.items():
        if not falta(r) or 'aprob' not in nrm(r.get('estado_hcd', 'aprobado')):
            continue
        pars = r.get('pars') or []
        texto = '\n'.join(pars)
        y = r.get('y')
        if pars:
            # el número del texto debe coincidir con el del título (el sitio a veces adjunta otro archivo)
            mt = re.search(r'(ORDENANZA|RESOLUCI[OÓ]N|COMUNICACI[OÓ]N)\s*N[°º.o]*\s*:?\s*([\d.]+)', texto, re.I)
            if mt and int(mt.group(2).replace('.', '') or 0) != r['n']:
                pars = []
        o = ficha(pars, r['t'], r['n'], y, r.get('a', ''), (r.get('pdf') or '').rsplit('/', 1)[-1], rel)
        if not o['y']:
            o['y'] = int(r['fecha_post'][:4]) if r['t'] != 'ord' else None
        if not o['y'] or (r['t'], r['n'], o['y']) in corpus:
            continue
        o['texto'] = '\n'.join(pars)
        o['fuente'] = 'Sitio del H.C.D. (' + r['link'] + ')'
        o['autor'] = r.get('autor', '')
        o['ingresado'] = r.get('ingresado', '')
        o['publicado_hcd'] = r['fecha_post']
        k = (o['t'], o['n'], o['y'])
        if k in vistos and (vistos[k]['texto'] or not o['texto']):
            continue
        vistos[k] = o
    salida = list(vistos.values())
    return salida


def revisar_hcd_cache(corpus, ya, rel, cache):
    """Rearma las fichas del sitio del H.C.D. con lo ya guardado, sin conectarse."""
    return revisar_hcd_armar(corpus, ya, rel, cache) if cache.get('posts') else []


# ---------------------------------------------------------------- estado de cada ordenanza
def estado_de(o, prom):
    p = prom.get(f"{o['n']}-{o['y']}")
    if p:
        etq = {'promulgada': 'Promulgada', 'vetada_total': 'Vetada', 'vetada_parcial': 'Vetada parcialmente',
               'tacita_decreto': 'Promulgada de hecho'}[p['estado']]
        return dict(p, etiqueta=etq + (f" · Dec. {p['decreto']}" if p.get('decreto') else ''))
    if not o['fe_iso']:
        return {'estado': 'sin_dato', 'etiqueta': 'Sancionada'}
    ses = dt.date.fromisoformat(o['fe_iso'])
    limite = suma_habiles(ses, DIAS_NOTIF + DIAS_VETO)
    if HOY > limite:
        return {'estado': 'tacita_presunta', 'limite': limite.isoformat(),
                'etiqueta': 'Promulgada de hecho (presunta)'}
    return {'estado': 'en_plazo', 'limite': limite.isoformat(), 'etiqueta': 'En plazo de promulgación'}


VIG = {
    'promulgada': 'Vigente (sujeta a verificación)', 'tacita_presunta': 'Vigente (sujeta a verificación)',
    'tacita_decreto': 'Vigente (sujeta a verificación)', 'sin_dato': 'Vigente (sujeta a verificación)',
    'en_plazo': 'Sancionada (en plazo de promulgación)', 'vetada_total': 'Vetada',
    'vetada_parcial': 'Vigente con modificaciones',
}
T3 = {'ord': 'Ord', 'dec': 'Dec', 'res': 'Res', 'com': 'Com'}


def nota(pr):
    e = pr['estado']
    if e in ('promulgada', 'vetada_total', 'vetada_parcial', 'tacita_decreto'):
        return (f"{pr['etiqueta']} ({pr['fecha'][8:]}/{pr['fecha'][5:7]}/{pr['fecha'][:4]})"
                + (f", publicado en el Boletín Oficial Municipal {pr['boletin']}." if pr.get('boletin') else '.'))
    if e == 'tacita_presunta':
        return ('No se publicó en el Boletín Oficial Municipal un decreto de promulgación ni de veto. '
                'Vencido el plazo de diez días hábiles del art. 108 inc. 2 de la Ley Orgánica de las Municipalidades '
                f"(estimado al {pr['limite'][8:]}/{pr['limite'][5:7]}/{pr['limite'][:4]}), la ordenanza se presume promulgada de hecho. Sujeto a verificación.")
    if e == 'en_plazo':
        return ('Sancionada por el H.C.D. El Departamento Ejecutivo tiene diez días hábiles desde la notificación para '
                f"promulgarla o vetarla (art. 108 inc. 2 LOM); plazo estimado hasta el {pr['limite'][8:]}/{pr['limite'][5:7]}/{pr['limite'][:4]}.")
    return ''


def main():
    sin_sibom = '--sin-sibom' in sys.argv
    sin_hcd = '--sin-hcd' in sys.argv
    with open(F_REL, encoding='utf-8') as f:
        rel = json.load(f)
    estado = {}
    if os.path.exists(F_EST):
        with open(F_EST, encoding='utf-8') as f:
            estado = json.load(f)
    consulta = {'fecha': dt.datetime.now().isoformat(timespec='minutes'), 'ok': None}
    if not sin_sibom:
        try:
            estado = revisar_sibom(estado)
            consulta['ok'] = True
        except Exception as e:  # noqa: BLE001
            consulta['ok'] = False
            consulta['error'] = str(e)[:200]
            print('  aviso: no se pudo consultar el SIBOM:', e)
    estado['ultima_consulta'] = consulta if consulta['ok'] is not None else estado.get('ultima_consulta')
    prom = dict(estado.get('decretos', {}))
    for k, v in (rel.get('promulgaciones') or {}).items():
        prom[k] = v

    corpus = corpus_existente()
    instr = []
    archivos = sorted(f for f in os.listdir(DIR_ORD) if f.lower().endswith('.docx') and not f.startswith('~$'))
    for fn in archivos:
        instr.append(leer_ordenanza(os.path.join(DIR_ORD, fn), rel))
    ya = {(o['t'], o['n'], o['y']) for o in instr} | {(o['t'], o['n']) for o in instr}
    cache = {}
    if os.path.exists(F_HCD):
        with open(F_HCD, encoding='utf-8') as f:
            cache = json.load(f)
    if not sin_hcd:
        try:
            instr += revisar_hcd(corpus, ya, rel, cache)
            cache['ultima_consulta'] = {'fecha': dt.datetime.now().isoformat(timespec='minutes'), 'ok': True}
        except Exception as e:  # noqa: BLE001
            cache['ultima_consulta'] = {'fecha': dt.datetime.now().isoformat(timespec='minutes'), 'ok': False, 'error': str(e)[:200]}
            print('  aviso: no se pudo consultar el sitio del H.C.D.:', e)
            instr += [o for o in revisar_hcd_cache(corpus, ya, rel, cache)]
    else:
        instr += revisar_hcd_cache(corpus, ya, rel, cache)

    nuevas, efectos = [], {}
    for o in instr:
        t = o['t']
        if t == 'ord':
            pr = estado_de(o, prom)
            efs = rel.get('efectos', {}).get(str(o['n'])) or efectos_auto(o['texto'])
            v = VIG[pr['estado']]
        else:
            pr = {'estado': 'hcd', 'etiqueta': 'Aprobada por el H.C.D.'}
            efs = []
            v = 'Cumplida / declarativa' if t == 'com' else 'Vigente (sujeta a verificación)'
        rf = [[T3[tt], n, acc, 1 if (tt, n, y) in corpus else 0] for tt, n, y, acc in efs]
        nt = nota(pr)
        extra = ' '.join(x for x in (
            f"Autor: {o['autor']}." if o.get('autor') else '',
            f"Ingresado el {o['ingresado']}." if o.get('ingresado') else '',
            f"Fuente: {o['fuente']}." if o.get('fuente') else '') if x)
        if t != 'ord' or o.get('autor'):
            nt = (nt + ' ' + extra).strip()
        if not o['texto']:
            nt += ' El texto completo no pudo leerse del archivo publicado.'
        e = {
            'id': f"{t}-{o['n']}-{o['y']}", 't': t, 'n': o['n'], 'y': o['y'], 'a': o['a'],
            'texto': o['texto'], 'archivo': o['archivo'], 'rz': o['rz'], 'c': o['c'],
            'v': v, 'fe': o['fe'] or '', 'se': o['se'], 'vi': o['vi'], 'au': o['au'],
            'nt': nt, 'rf': rf, 'pr': pr, 'fs': o['fe_iso'] or o.get('publicado_hcd'), 'ts': 1,
            'src': 'hcd' if o.get('publicado_hcd') else 'docx',
        }
        if not o['fe_iso'] and o.get('publicado_hcd'):
            e['fs_aprox'] = True
        nuevas.append(e)
        if pr['estado'] == 'vetada_total':
            continue  # una ordenanza vetada no produce efectos sobre otras
        for tt, n, y, acc in efs:
            r = corpus.get((tt, n, y))
            if not r:
                continue
            k = f'{tt}-{n}-{y}'
            x = efectos.setdefault(k, {'id': k, 't': tt, 'n': n, 'y': y, 'ts': 1, 'ri': [], 'efecto': True})
            x['ri'].append([T3[t], o['n'], acc])
            if acc == 'Deroga':
                x['v'] = 'Derogada'
            elif acc in ('Modifica', 'Deroga parcialmente') and x.get('v') != 'Derogada' and not r['v'].startswith('Derog'):
                x['v'] = 'Vigente con modificaciones'

    nuevas.sort(key=lambda e: (e['fs'] or '', {'ord': 3, 'res': 2, 'com': 1}[e['t']], e['n']), reverse=True)
    salida = {
        'v': 1, 'generado': dt.datetime.now().isoformat(timespec='minutes'),
        'sibom': {'ultimo_boletin': estado.get('ultimo_boletin'), 'consulta': estado.get('ultima_consulta')},
        'hcd': {'consulta': cache.get('ultima_consulta')},
        'list': nuevas, 'efectos': list(efectos.values()),
    }
    js = ('/* Digesto Gilense — ordenanzas nuevas y su estado de promulgación.\n'
          '   Lo genera herramientas/actualizar_novedades.py (GitHub Actions). No editar a mano. */\n'
          'window.__DIGESTO_NOVEDADES=' + json.dumps(salida, ensure_ascii=False).replace(' ', ' ').replace(' ', ' ') + ';\n')
    previo = None
    if os.path.exists(F_OUT):
        try:
            t = open(F_OUT, encoding='utf-8').read()
            previo = json.loads(t[t.index('{'):t.rindex('}') + 1])
        except Exception:  # noqa: BLE001
            previo = None
    clave = lambda j: json.dumps({k: j.get(k) for k in ('list', 'efectos')} | {'b': (j.get('sibom') or {}).get('ultimo_boletin')}, ensure_ascii=False, sort_keys=True)
    if previo and clave(previo) == clave(salida):
        print('  sin cambios en las ordenanzas ni en sus estados: digesto-novedades.js queda como estaba')
    else:
        with open(F_OUT, 'w', encoding='utf-8') as f:
            f.write(js)
    with open(F_EST, 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)
    if cache:
        with open(F_HCD, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=0)
    from collections import Counter
    c = Counter(e['t'] for e in nuevas)
    print(f"{c['ord']} ordenanzas, {c['res']} resoluciones y {c['com']} comunicaciones nuevas; "
          f'{len(efectos)} normas anteriores afectadas → {os.path.basename(F_OUT)}')
    for e in nuevas[:40]:
        print(f"  {T3[e['t']]}. {e['n']}/{e['y']} · {e['fe'] or e['fs']} · {e['pr']['etiqueta']} · {e['c']}")


if __name__ == '__main__':
    main()
