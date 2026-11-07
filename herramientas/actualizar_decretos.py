#!/usr/bin/env python3
"""Digesto de Decretos del Ejecutivo — actualización automática desde el SIBOM.

Lee los boletines nuevos (los que todavía no están en decretos.html), extrae cada decreto
(número, fecha, visto, artículo 1º), lo clasifica por tema y subtema con un modelo entrenado
sobre el registro existente (acierto medido: 89 % por subtema, 92 % por tema), detecta los de
alcance general y vuelve a calcular el análisis. Escribe el resultado dentro de decretos.html.

    python herramientas/actualizar_decretos.py              # consulta el SIBOM
    python herramientas/actualizar_decretos.py --verificar  # recalcula sin red y compara
"""
import collections, datetime as dt, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import actualizar_novedades as AN
from clasificador_decretos import entrenar

RAIZ = AN.RAIZ
F = os.path.join(RAIZ, 'decretos.html')
RX_DATA = re.compile(r'(<script id="data" type="application/json">)(.*?)(</script>)', re.S)
MESES = 'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split()
AUT = [('2023-12-10', 3), ('2021-12-06', 2), ('0000', 0)]  # índice en D['auts']


def leer():
    s = open(F, encoding='utf-8').read()
    return s, json.loads(RX_DATA.search(s).group(2))


def escribir(s, D):
    j = json.dumps(D, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    s = RX_DATA.sub(lambda m: m.group(1) + j + m.group(3), s, count=1)
    open(F, 'w', encoding='utf-8').write(s)


def autoridad(f):
    if not f:
        return 4
    for desde, i in AUT:
        if f >= desde:
            return i


# ---------------------------------------------------------------- análisis
def analizar(D):
    S, T, subOf = D['subs'], D['temas'], D['subOf']
    R = [r for r in D['R'] if r[2] and r[2] >= '2017-01']   # el SIBOM de Giles arranca en 2017
    A = D['an']; top = A['top']
    tix = {t: i for i, t in enumerate(T)}
    grupo = lambda ti: top.index(T[ti]) if T[ti] in top else len(top) - 1
    por_mes = collections.defaultdict(list)
    for r in R:
        if r[2]:
            por_mes[r[2][:7]].append(r)
    meses = sorted(por_mes)
    def todos_los_meses(a, b):
        y, m = int(a[:4]), int(a[5:]); out = []
        while (y, m) <= (int(b[:4]), int(b[5:])):
            out.append(f'{y}-{m:02d}'); m += 1
            if m > 12: y, m = y + 1, 1
        return out
    rango = todos_los_meses(meses[0], meses[-1])
    publ = lambda ym: len(por_mes.get(ym, [])) >= 10
    isub = S.index('Subsidios y ayudas'); itemp = S.index('Personal temporario')
    A['meses'] = []
    for ym in rango:
        v = [0] * len(top)
        for r in por_mes.get(ym, []):
            v[grupo(r[3])] += 1
        A['meses'].append([ym, v])
    A['series'] = [[ym, sum(1 for r in por_mes.get(ym, []) if r[4] == isub),
                    sum(1 for r in por_mes.get(ym, []) if r[4] == itemp), publ(ym)] for ym in rango]
    años = sorted({int(ym[:4]) for ym in meses}); A['years'] = años
    comp = {y: [0] * len(top) for y in años}
    for r in R:
        if r[2]:
            comp[int(r[2][:4])][grupo(r[3])] += 1
    A['comp'] = [[y, comp[y]] for y in años]
    est = []
    for m in range(1, 13):
        vals = [len(por_mes[ym]) for ym in rango if int(ym[5:]) == m and publ(ym)]
        est.append(sum(vals) / len(vals) if vals else 0)
    A['est'] = est
    heat = []
    for lab, lvl, _ in A['heat']:
        if lvl == 0:
            ti = tix[lab]; v = [sum(1 for r in R if r[3] == ti and r[2] and int(r[2][:4]) == y) for y in años]
        else:
            si = S.index(lab); v = [sum(1 for r in R if r[4] == si and r[2] and int(r[2][:4]) == y) for y in años]
        heat.append([lab, lvl, v])
    A['heat'] = heat
    ipers = tix['Personal']; aut = []
    for i, lab in enumerate(D['auts'][:4]):
        rs = [r for r in R if r[9] == i and r[2]]
        if not rs:
            continue
        ms = sorted({r[2][:7] for r in rs}); n = sum(1 for ym in ms if publ(ym)) or len(ms)
        aut.append([f'{lab} · {ms[0]} a {ms[-1]}', n, len(rs), len(rs) / n,
                    sum(1 for r in rs if r[4] == isub) / n, sum(1 for r in rs if r[3] == ipers) / n])
    A['aut'] = aut
    tot = len(D['R']); npub = sum(1 for ym in rango if publ(ym))
    nprom = sum(1 for x in D['N'] if 'Promulgación' in x['cls'])
    A['kpis'] = [[f'{tot:,}'.replace(',', '.'), 'decretos del D.E. registrados'],
                 [f'{round(tot / npub)}', 'decretos por mes publicado, en promedio'],
                 [f'{round(100 * sum(1 for r in D['R'] if T[r[3]] == "Acción social") / tot)} %', 'son ayudas sociales y subsidios'],
                 [f'{round(100 * sum(1 for r in D['R'] if r[3] == ipers) / tot)} %', 'se refieren al personal municipal'],
                 [f'{len(D["N"])}', f'decretos de alcance general ({nprom} promulgaciones)']]
    D['rango'] = f'{rango[0][:4]}/{rango[0][5:]} – {rango[-1][:4]}/{rango[-1][5:]}'
    # cobertura por numeración
    cov = []
    for y in años:
        ns = {r[0] for r in D['R'] if r[1] == y and r[0]}
        if not ns:
            continue
        faltan = [MESES[int(ym[5:]) - 1][:3] for ym in rango if ym[:4] == str(y) and not publ(ym)]
        cov.append([y, len(ns), max(ns), round(100 * len(ns) / max(ns)), 'faltan: ' + ', '.join(faltan) if faltan else 'todos'])
    D['cov'] = cov
    return D


# ---------------------------------------------------------------- normativo
CLASES = [('Promulgación', r'prom[uú]lg|t[eé]ngase por promulgada'), ('Veto', r'\bv[eé]t[ao]'),
          ('Reglamentario', r'reglam[eé]nt'), ('Emergencia', r'emergencia'),
          ('Régimen fiscal', r'ordenanza (fiscal|impositiva)|\btasas?\b|al[ií]cuota|plan de (pagos|facilidades)'),
          ('Estructura orgánica', r'estructura org[aá]nica|organigrama')]


def normativo(art1):
    t = AN.nrm(art1)
    return [c for c, rx in CLASES if re.search(rx, t)]


def sumillas_digesto():
    try:
        s = open(os.path.join(RAIZ, 'index.html'), encoding='utf-8').read()
        P = json.loads(re.search(r'<script[^>]*id="payload"[^>]*>(.*?)</script>', s, re.S).group(1))
        return {(r['n'], r['y']): r['a'] for r in P['d'] if r['t'] == 'ord'}
    except Exception:
        return {}


# ---------------------------------------------------------------- SIBOM
def boletines_nuevos(D):
    vistos = {str(b[2]) for b in D['bul']}
    pag = AN.traer(f'{AN.SIBOM}/cities/{AN.MUNI}')
    bs = re.findall(r'bulletin-title">\s*(\d+)º[^<]*</p>\s*<p class="bulletin-date">\s*Publicado el\s*([\d/]+)\s*</p>.*?action="/bulletins/(\d+)"', pag, re.S)
    return [(int(n), f, bid) for n, f, bid in reversed(bs) if bid not in vistos]


def leer_boletin(bid):
    bh = AN.traer(f'{AN.SIBOM}/bulletins/{bid}')
    out = []
    cids = list(dict.fromkeys(re.findall(rf'/bulletins/{bid}/contents/(\d+)', bh)))
    leer_boletin.piezas = len(cids)
    for cid in cids:
        try:
            t = re.sub(r'\s+', ' ', AN.texto_html(AN.traer(f'{AN.SIBOM}/bulletins/{bid}/contents/{cid}')))
        except Exception:
            continue
        m = AN.RX_DEC.search(t)
        if not m:
            continue
        cuerpo = t[m.end():]
        vm = re.search(r'Visto\s*(.*?)\s*(?:Considerando|Por ello)', cuerpo, re.I)
        am = re.search(r'Art[ií]culo\s*1[°º]?\s*[:.\-–]?\s*(.{0,600}?)(?:Art[ií]culo\s*2|$)', cuerpo, re.I)
        d1, m1, y1 = m.group(3).split('/')
        out.append({'n': int(m.group(1)), 'y': AN.anio4(m.group(2), int(y1)), 'f': f'{y1}-{m1}-{d1}',
                    'v': (vm.group(1) if vm else cuerpo[:300]).strip(), 'a1': (am.group(1) if am else '').strip(), 'c': int(cid)})
        time.sleep(0.3)
    return out


def main():
    s, D = leer()
    if '--probar' in sys.argv:
        bid = sys.argv[sys.argv.index('--probar') + 1]; modelo = entrenar(D['R'])
        xs = leer_boletin(bid); print(f'boletín {bid}: {leer_boletin.piezas} piezas, {len(xs)} decretos reconocidos')
        idx = {(r[0], r[1]): r for r in D['R']}; ok = n = 0
        for x in xs:
            sub = modelo.predecir(x['v'] + ' ' + x['a1']); r = idx.get((x['n'], x['y']))
            if r: n += 1; ok += (D['subOf'][sub] == r[3])
        print(f'  tema coincide con el relevamiento en {ok} de {n}; alcance general: {sum(1 for x in xs if normativo(x["a1"]))}')
        for x in xs[:3]: print('  ', x['n'], x['y'], x['f'], '|', x['v'][:70], '|', D['subs'][modelo.predecir(x['v'] + ' ' + x['a1'])])
        return
    if '--verificar' in sys.argv:
        import copy
        antes = copy.deepcopy(D['an']); analizar(D)
        for k in ('meses', 'series', 'comp', 'heat', 'kpis'):
            print(k, 'igual' if D['an'][k] == antes[k] else 'DISTINTO')
        print('est', [round(a - b, 2) for a, b in zip(D['an']['est'], antes['est'])])
        print('aut', [(round(a[3] - b[3], 2), round(a[4] - b[4], 2), round(a[5] - b[5], 2)) for a, b in zip(D['an']['aut'], antes['aut'])])
        return
    estado = {'fecha': dt.datetime.now().isoformat(timespec='minutes'), 'ok': True, 'nuevos': 0}
    try:
        nuevos = boletines_nuevos(D)
    except Exception as e:  # noqa: BLE001
        print('  aviso: no se pudo consultar el SIBOM:', e)
        nuevos = None; estado.update(ok=False, error=str(e)[:200])
    if nuevos:
        modelo = entrenar(D['R']); sumas = sumillas_digesto()
        conocidos = {(r[0], r[1]) for r in D['R']}
        for num, fecha, bid in nuevos:
            todos = leer_boletin(bid)
            if leer_boletin.piezas and not todos:
                print(f'  aviso: el boletín {num}º tiene {leer_boletin.piezas} piezas pero no se reconoció ningún decreto; se reintenta mañana')
                continue
            decs = [x for x in todos if (x['n'], x['y']) not in conocidos]
            for x in decs:
                sub = modelo.predecir(x['v'] + ' ' + x['a1']); tema = D['subOf'][sub]
                au = autoridad(x['f'])
                D['R'].append([x['n'], x['y'], x['f'], tema, sub, 0, x['v'][:220] + ('…' if len(x['v']) > 220 else ''), num, x['c'], au])
                conocidos.add((x['n'], x['y']))
                cls = normativo(x['a1'])
                if cls:
                    ords = []
                    for mo in re.finditer(r'n[°º.o]*\s*([\d.]{3,6})\s*/\s*(\d{2,4})', x['a1'], re.I):
                        on, oy = int(mo.group(1).replace('.', '')), AN.anio4(mo.group(2), x['y'])
                        ords.append({'n': on, 'y': oy, 'a': sumas.get((on, oy), '')})
                    D['N'].insert(0, {'n': x['n'], 'y': x['y'], 'f': x['f'], 'cls': cls,
                                      'vig': 'Agotado (acto cumplido)' if cls == ['Promulgación'] else 'Vigente (sujeto a verificación)',
                                      'res': x['a1'], 'v': x['v'][:220], 'g': '', 't': tema, 'au': D['auts'][au], 'b': num, 'c': x['c'],
                                      'ords': ords, 'decs': [], 'dp': [], 'mp': [], 'auto': 1})
            ms = sorted(x['f'][:7] for x in decs)
            D['bul'].append([num, fecha, bid])
            D['bulinfo'].append([num, fecha, len(decs), (ms[0] if ms[0] == ms[-1] else f'{ms[0]} a {ms[-1]}') if ms else '—', bid])
            estado['nuevos'] += len(decs)
            print(f'  boletín {num}º ({fecha}): {len(decs)} decretos nuevos')
        D['R'].sort(key=lambda r: (r[2] or '', r[0]), reverse=True)
        D['N'].sort(key=lambda x: (x['f'] or '', x['n']), reverse=True)
        analizar(D)
    ult = max((r[2] for r in D['R'] if r[2]), default='')
    act = D.get('act') or {}
    act.update({'consulta': estado, 'ultimo_boletin': f"{D['bul'][-1][0]}º · {D['bul'][-1][1]}", 'firmados_hasta': ult})
    if nuevos:
        act['actualizado'] = dt.date.today().isoformat()
    act.setdefault('actualizado', '2026-10-29')
    D['act'] = act
    escribir(s, D)
    print(f"decretos.html: {len(D['R'])} decretos, último firmado {ult}, boletín {act['ultimo_boletin']}")


if __name__ == '__main__':
    main()
