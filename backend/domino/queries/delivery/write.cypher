// Q-DELIVER: one atomic write after the simulated clock reaches delivery. Matches only if the world is still
// at the version the outcomes were computed on; bumps world_version and records the simulated day.
// Each PO becomes 'received' (on time) or 'delayed' (arrived days_late days after plan) and frees the spare
// it reserved; each order it protected becomes 'fulfilled', 'fulfilled_late' or 'unfulfilled'.
// The caller compares pos_updated / orders_updated with what it sent.
MATCH (m:Meta {id: 'META'})
WHERE m.world_version = $world_version
SET m.world_version = m.world_version + 1, m.day = $day
WITH m
UNWIND $pos AS x
MATCH (p:PurchaseOrder {id: x.id})
WHERE p.status = 'committed'
MATCH (s:Site {id: x.site})-[cs:CAN_SUPPLY]->(pl:Plant {id: x.plant})
WHERE cs.component_id = x.component
SET p.status = x.status, p.days_late = x.days_late, p.arrived_day = x.arrived_day,
    p.received_day = x.received_day,
    cs.reserved_wk = CASE WHEN coalesce(cs.reserved_wk, 0) > p.rate_wk THEN cs.reserved_wk - p.rate_wk ELSE 0 END
WITH m, count(DISTINCT p) AS pos_updated
UNWIND $orders AS y
MATCH (o:Order {id: y.id})
WHERE o.status = 'protected_projected'
SET o.status = y.status, o.delivered_day = y.delivered_day, o.late_days = y.late_days
WITH m, pos_updated, count(DISTINCT o) AS orders_updated
CREATE (act:Action {id: $action_id, type: 'deliver', actor: 'simulator', day: $day, payload_json: $payload_json})
RETURN pos_updated, orders_updated, m.world_version AS world_version, m.day AS day
