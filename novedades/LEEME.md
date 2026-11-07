# Novedades del Digesto Gilense

## Cargar ordenanzas nuevas

1. En GitHub, entrar a la carpeta `novedades/ordenanzas/`.
2. «Add file» → «Upload files» y arrastrar los Word (.docx) que entrega el H.C.D.
   Se mantiene el nombre de archivo de la Secretaría: `2026-Ord02848 (Asunto).docx`.
   Lo que va entre paréntesis es la sumilla que se ve en el sitio.
3. «Commit changes». En uno o dos minutos la acción **Actualizar novedades del Digesto**
   lee los textos, los suma al buscador, al Índice y a la pestaña Novedades, y publica.

## Qué hace sola todos los días (07:17)

- Revisa los boletines nuevos del SIBOM (municipio 111) y busca decretos que promulguen
  o veten ordenanzas. Al encontrarlos, cambia el estado y enlaza el decreto.
- Si pasaron diez días hábiles desde la sesión (más cinco de margen por la notificación)
  sin decreto publicado, marca la ordenanza como «promulgada de hecho (presunta)»
  (art. 108 inc. 2, Decreto-Ley 6769/58).

## Correcciones a mano: `relaciones.json`

- `clasificacion`: materia y categoría de cada ordenanza (si falta, se deduce del título).
- `efectos`: qué deroga o modifica cada ordenanza nueva. Si falta, se detecta en el texto
  («Derógase…», «Modifícase… la Ordenanza Nº …»).
- `promulgaciones`: para cargar un decreto que todavía no salió en el Boletín, por ejemplo
  `"2848-2026": {"estado": "promulgada", "decreto": "1720/26", "fecha": "2026-11-20"}`.
  Estados posibles: `promulgada`, `vetada_total`, `vetada_parcial`, `tacita_decreto`.

## Archivos que genera (no editar)

- `digesto-novedades.js`, junto a `index.html`.
- `novedades/estado-sibom.json`: boletines ya revisados y decretos encontrados.
