// Current supply into every plant (active contracts only; alternates are not flowing yet).
MATCH (s:Site)-[sup:SUPPLIES]->(pl:Plant)
RETURN s.id AS site, pl.id AS plant, sup.component_id AS component, sup.used_wk AS used_wk,
       sup.transit_days AS transit_days
ORDER BY site, plant, component
