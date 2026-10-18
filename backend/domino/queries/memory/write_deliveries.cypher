// Delivery outcomes (memory graph): one Delivery fact per received purchase order, linked to the source site,
// so the allocator can learn that site's reliability. learned_on is the calendar date the fact was written.
// A name that is only the raw id never replaces a real name (as in write_incident).
UNWIND $deliveries AS x
MERGE (n:Entity {id: x.site})
SET n.kind = CASE WHEN n.kind IS NULL THEN x.kind ELSE n.kind END,
    n.name = CASE WHEN x.name = x.site AND n.name IS NOT NULL THEN n.name ELSE x.name END
MERGE (d:Delivery {id: x.id})
SET d.po_id = x.po_id, d.run_id = x.run_id, d.decision_id = x.decision_id, d.component = x.component,
    d.plant = x.plant, d.planned_day = x.planned_day, d.arrived_day = x.arrived_day, d.days_late = x.days_late,
    d.learned_on = x.learned_on
MERGE (d)-[o:OF]->(n)
RETURN count(o) AS linked
