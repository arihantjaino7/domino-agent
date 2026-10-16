// One BOM level: units of each input per unit of the given components (BAT-4S -> 4 x CELL-21700).
MATCH (k:Component)-[m:MADE_FROM]->(c:Component)
WHERE k.id IN $component_ids
RETURN k.id AS component, c.id AS input, m.qty AS qty
ORDER BY component, input
