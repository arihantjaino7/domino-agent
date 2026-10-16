// Q-FLOW-EXTRACT (a): supply edges into the plant for one component, current and alternate.
MATCH (t1:Site)-[e:SUPPLIES|CAN_SUPPLY]->(pl:Plant {id: $plant_id})
WHERE e.component_id = $component_id
RETURN t1.id AS site, type(e) AS kind, coalesce(e.used_wk, 0) AS used_wk, coalesce(e.spare_wk, 0) AS spare_wk,
       t1.capacity_wk AS site_cap, t1.capacity_factor AS factor, t1.status AS status
ORDER BY site, kind
