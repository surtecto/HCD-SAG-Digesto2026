#!/usr/bin/env python3
"""Agrega a index.html el bloque «Actualización y alcance» en cada sección (o lo reemplaza si ya está)."""
import os
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(R, 'index.html')
s = open(F, encoding='utf-8').read()
mod = open(os.path.join(R, 'herramientas', 'alcance_modulo.html'), encoding='utf-8').read().strip()
if '<style id="alc-css">' in s:
    a = s.index('<style id="alc-css">'); b = s.index('</script>', s.index('/* ===================== actualización y alcance')) + len('</script>')
    s = s[:a] + mod + s[b:]
else:
    slots = [
        ('<aside id="nov-home" class="nov-home" aria-label="Últimas ordenanzas sancionadas" hidden></aside>',
         '<aside id="nov-home" class="nov-home" aria-label="Últimas ordenanzas sancionadas" hidden></aside>\n    <div data-alc-slot="bus"></div>'),
        ('<div id="pane-nov" role="tabpanel" aria-labelledby="tab-nov" hidden><div id="nov-root"></div></div>',
         '<div id="pane-nov" role="tabpanel" aria-labelledby="tab-nov" hidden><div data-alc-slot="nov"></div><div id="nov-root"></div></div>'),
        ('  <main>\n    <div class="bar">', '  <main>\n    <div data-alc-slot="idx"></div>\n    <div class="bar">'),
        ('  <div class="dg-kpis" id="dg-kpis"></div>', '  <div data-alc-slot="dig"></div>\n  <div class="dg-kpis" id="dg-kpis"></div>'),
        ('<div id="pane-estad" role="tabpanel" aria-labelledby="tab-estad" hidden><div class="shell" style="display:block">',
         '<div id="pane-estad" role="tabpanel" aria-labelledby="tab-estad" hidden><div class="shell" style="display:block">\n  <div data-alc-slot="est"></div>'),
    ]
    for a, b in slots:
        if s.count(a) != 1:
            raise SystemExit(f'patrón {s.count(a)} veces: {a[:70]!r}')
        s = s.replace(a, b)
    i = s.rindex('</body>')
    s = s[:i] + mod + '\n' + s[i:]
open(F, 'w', encoding='utf-8').write(s)
print('index.html: bloques de alcance aplicados')
