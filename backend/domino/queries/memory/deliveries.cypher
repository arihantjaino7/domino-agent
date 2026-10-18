// Delivery facts per source site (memory graph), oldest first, for learned reliability.
// An empty $site_ids list returns every site that has deliveries.
MATCH (d:Delivery)-[o:OF]->(n:Entity)
WHERE size($site_ids) = 0 OR n.id IN $site_ids
RETURN n.id AS site, n.name AS name, d.id AS id, d.po_id AS po_id, d.run_id AS run_id, d.decision_id AS decision_id,
       d.component AS component, d.plant AS plant, d.planned_day AS planned_day, d.arrived_day AS arrived_day,
       d.days_late AS days_late, d.learned_on AS learned_on
ORDER BY site, learned_on, id
