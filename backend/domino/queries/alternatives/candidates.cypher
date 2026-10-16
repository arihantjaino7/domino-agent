// Q-ALTERNATIVES: approved-vendor-list sources into the plant, with the taint check.
// Any disrupted site 1-4 FEEDS hops upstream is returned as an evidence path. Exposure is a warning, not a rejection.
// nodes(null) after an OPTIONAL MATCH miss is null and collect() drops it, so clean sites get [] (SPIKE #9).
MATCH (alt:Site)-[cs:CAN_SUPPLY]->(pl:Plant {id: $plant_id})
WHERE cs.component_id IN $component_ids
OPTIONAL MATCH taint = (bad:Site)-[:FEEDS*1..4]->(alt)
WHERE bad.status = 'disrupted'
WITH alt, cs, collect(DISTINCT [n IN nodes(taint) | n.id]) AS tainted_paths
RETURN alt.id AS site, cs.component_id AS component, cs.spare_wk AS spare_wk,
       cs.unit_price_cents AS price_cents, cs.lead_days AS lead_days, cs.transit_days AS transit_days,
       cs.air_transit_days AS air_transit_days, cs.air_surcharge_cents AS air_surcharge_cents,
       cs.moq AS moq, cs.qualified AS qualified, cs.requal_days AS requal_days,
       alt.status AS site_status, tainted_paths
ORDER BY price_cents, site
