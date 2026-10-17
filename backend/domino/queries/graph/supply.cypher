// Canvas: active contracts (SUPPLIES) and approved alternates (CAN_SUPPLY) into plants.
MATCH (s:Site)-[e:SUPPLIES|CAN_SUPPLY]->(pl:Plant)
RETURN s.id AS src, pl.id AS dst, type(e) AS kind, e.component_id AS component,
       coalesce(e.used_wk, e.spare_wk) AS volume_wk
ORDER BY src, dst, kind
