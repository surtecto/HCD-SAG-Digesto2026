#!/usr/bin/env python3
"""Aplica a index.html la capa «Novedades» (una sola vez; si ya está, no hace nada).
Incorpora digesto-novedades.js al corpus, agrega la pestaña Novedades y el aviso en la portada."""
import os, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(R, 'index.html')
s = open(F, encoding='utf-8').read()
if 'id="pane-nov"' in s:
    print('index.html ya tiene la pestaña Novedades'); sys.exit(0)
def rep(a, b, n=1):
    global s
    c = s.count(a)
    if c != n:
        raise SystemExit(f'patrón encontrado {c} veces (se esperaban {n}): {a[:80]!r}')
    s = s.replace(a, b)
# 1. cargar el archivo de novedades antes que las adiciones de Edición
rep('<script src="digesto-adiciones.js"></script>',
    '<script src="digesto-novedades.js"></script>\n<script src="digesto-adiciones.js"></script>')
# 2. sumar novedades y efectos al conjunto publicado (Edición puede corregirlas: gana el ts mayor)
rep("(BASE.list||[]).forEach(function(e){ if(e&&e.id) pub.set(e.id,e); });",
    "(BASE.list||[]).forEach(function(e){ if(e&&e.id) pub.set(e.id,e); });\n"
    "var NOV=window.__DIGESTO_NOVEDADES||null;\n"
    "((NOV&&NOV.list)||[]).concat((NOV&&NOV.efectos)||[]).forEach(function(e){ if(!e||!e.id) return; e.nov=true; e.ts=e.ts||1; var o=pub.get(e.id); if(!o||(o.ts||0)<=1) pub.set(e.id,e); });")
# 3. lo que viene de novedades no se copia al archivo de Edición
rep("exportar:function(){ var l=[]; all.forEach(function(e){ l.push(e); });",
    "exportar:function(){ var l=[]; all.forEach(function(e){ if(!e.nov) l.push(e); });")
# 4. aplicar nota, vínculos y estado de promulgación
rep("['a','v','fe','se','au','vi'].forEach(function(k){ if(e[k]) r[k]=e[k]; });",
    "['a','v','fe','se','au','vi','nt','pr'].forEach(function(k){ if(e[k]) r[k]=e[k]; });\n"
    "        if(e.ri) r.ri=(r.ri||[]).concat(e.ri.filter(function(x){ return !(r.ri||[]).some(function(z){ return z[0]===x[0]&&z[1]===x[1]; }); }));")
rep("if(e.fe) n.fe=e.fe; if(e.se) n.se=e.se; if(e.vi) n.vi=e.vi;",
    "if(e.fe) n.fe=e.fe; if(e.se) n.se=e.se; if(e.vi) n.vi=e.vi; if(e.nt) n.nt=e.nt; if(e.pr) n.pr=e.pr; if(e.rf&&e.rf.length) n.rf=e.rf; if(e.nov) n.q='documentado (texto entregado por el H.C.D.)';")
rep("if(!e.y) return;\n      var n={t:e.t",
    "if(!e.y||e.efecto) return;\n      var n={t:e.t")
# 5. rótulo de la nota en la ficha
rep("if(r.nt) h += `<div class=\"block\"><h4>Nota de procedencia</h4>",
    "if(r.nt) h += `<div class=\"block\"><h4>${r.pr?'Promulgación y vigencia':'Nota de procedencia'}</h4>")
# 6. pestaña, panel y aviso de portada
rep('<button class="tab" id="tab-indice" role="tab"',
    '<button class="tab" id="tab-nov" role="tab" aria-selected="false" aria-controls="pane-nov">Novedades</button>\n'
    '  <button class="tab" id="tab-indice" role="tab"')
rep('<div id="bq-home">',
    '<div id="bq-home">\n    <aside id="nov-home" class="nov-home" aria-label="Últimas ordenanzas sancionadas" hidden></aside>')
rep('<div id="pane-ed" role="tabpanel" aria-labelledby="tab-ed" hidden>',
    '<div id="pane-nov" role="tabpanel" aria-labelledby="tab-nov" hidden><div id="nov-root"></div></div>\n\n'
    '<div id="pane-ed" role="tabpanel" aria-labelledby="tab-ed" hidden>')
rep("const TB = {bus:['tab-bus','pane-bus'], idx:",
    "const TB = {bus:['tab-bus','pane-bus'], nov:['tab-nov','pane-nov'], idx:")
# 7. Edición no cuenta ni lista lo que viene de novedades
rep('const n=ED.list.length, p=ED.pend.size',
    'const n=ED.list.filter(e=>!e.nov).length, p=ED.pend.size')
rep("const l=ED.list.slice().sort((a,b)=>(b.ts||0)-(a.ts||0)), box=$('ed-inc');",
    "const l=ED.list.filter(e=>!e.nov).sort((a,b)=>(b.ts||0)-(a.ts||0)), box=$('ed-inc');")
rep("con ${nf.format(ED.list.length)} norma${ED.list.length===1?'':'s'}.",
    "con ${nf.format(ED.list.filter(e=>!e.nov).length)} norma${ED.list.filter(e=>!e.nov).length===1?'':'s'}.")
mod = open(os.path.join(R, 'herramientas', 'novedades_modulo.html'), encoding='utf-8').read()
i = s.rindex('</body>')
s = s[:i] + mod + '\n' + s[i:]
open(F, 'w', encoding='utf-8').write(s)
print('index.html: pestaña Novedades aplicada')
