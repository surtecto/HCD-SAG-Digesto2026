#!/usr/bin/env python3
"""Aplica a index.html la capa visual 2026-11 (gráficos, íconos, botones, movimiento, ilustración).
Reemplaza la versión anterior de la capa si ya estaba."""
import os, re
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(R, 'herramientas', 'visual')
F = os.path.join(R, 'index.html')
s = open(F, encoding='utf-8').read()
rd = lambda n: open(os.path.join(V, n), encoding='utf-8').read()
# 1. primitivas de gráficos de Estadística
a = s.index('/* ---- helpers svg ---- */')
b = s.index('/* ============ construir ============ */', a)
s = s[:a] + rd('charts.js') + s[b:]
# 2. rótulos completos en el cruce materia × instrumento
s = s.replace("{cw:74,fmtc:c=>c.slice(0,4)+'.'}", "{cw:74,fmtc:c=>({'Comunicación':'Comunic.','Resolución':'Resol.'})[c]||c}")
# 3. estilos (al final del <head>, para que manden)
css = '<style id="capa-visual">\n' + rd('charts.css') + '\n' + rd('capa.css') + '\n</style>'
s = re.sub(r'<style id="capa-visual">.*?</style>\n?', '', s, flags=re.S)
s = s.replace('</head>', css + '\n</head>', 1)
# 4. comportamiento (al final del <body>)
js = '<script id="capa-visual-js">\n' + rd('capa.js') + '\n</script>'
s = re.sub(r'<script id="capa-visual-js">.*?</script>\n?', '', s, flags=re.S)
i = s.rindex('</body>')
s = s[:i] + js + '\n' + s[i:]
open(F, 'w', encoding='utf-8').write(s)
print('index.html: capa visual aplicada')
