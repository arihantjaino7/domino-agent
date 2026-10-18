// Q-XRAY-SITES: every site that feeds another site or holds a contract with a plant, with its operator,
// region and whether Kestrel holds a direct contract with it (a SUPPLIES or CAN_SUPPLY edge to a plant).
MATCH (s:Site)
OPTIONAL MATCH (s)-[f:FEEDS]->(:Site)
WITH s, count(f) AS feeds_out
OPTIONAL MATCH (s)-[c:SUPPLIES|CAN_SUPPLY]->(:Plant)
WITH s, feeds_out, count(c) AS contracts
WHERE feeds_out > 0 OR contracts > 0
OPTIONAL MATCH (sup:Supplier)-[op:OPERATES]->(s)
OPTIONAL MATCH (s)-[li:LOCATED_IN]->(r:Region)
RETURN s.id AS site, s.name AS name, s.tier AS tier, s.kind AS kind, s.status AS status,
       sup.id AS operator_id, sup.name AS operator, r.id AS region, r.name AS region_name, r.country AS country,
       feeds_out, contracts, contracts > 0 AS direct_contract
ORDER BY site
