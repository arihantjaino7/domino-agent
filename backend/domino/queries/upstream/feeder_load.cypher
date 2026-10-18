// Capacity, health and existing outgoing volume of upstream sites. The edge is aliased so every
// outgoing FEEDS contract is summed.
MATCH (u:Site) WHERE u.id IN $site_ids
OPTIONAL MATCH (u)-[f:FEEDS]->(:Site)
RETURN u.id AS site, u.capacity_wk AS capacity_wk, u.capacity_factor AS factor,
       sum(coalesce(f.used_wk, 0)) AS used_out
ORDER BY site
