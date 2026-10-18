// Q-EXECUTE: one atomic write. Matches only if the decision is approved with this plan_hash and the
// world is still at the version the plan was simulated on; bumps world_version; creates every PO with
// its links and PROTECTS allocations; marks orders protected (projected); logs an Action.
// The unique constraint on PurchaseOrder.id rolls the whole query back on a duplicate.
// The executor compares pos_created / protects_created with the plan (invariant V9).
MATCH (d:Decision {id: $decision_id})
WHERE d.status = 'approved' AND d.plan_hash = $plan_hash
MATCH (m:Meta {id: 'META'})
WHERE m.world_version = $world_version
SET m.world_version = m.world_version + 1
WITH d, m
UNWIND $pos AS po
MATCH (s:Site {id: po.site_id})-[cs:CAN_SUPPLY]->(pl:Plant {id: po.plant_id})
WHERE cs.component_id = po.component_id
MATCH (k:Component {id: po.component_id})
CREATE (p:PurchaseOrder {id: po.id, qty: po.qty, rate_wk: po.rate_wk, unit_price_cents: po.unit_price_cents,
                         mode: po.mode, first_arrival_day: po.first_arrival_day, status: 'committed',
                         created_by: 'domino'})
CREATE (d)-[:CREATED]->(p), (p)-[:FROM_SITE]->(s), (p)-[:FOR_COMPONENT]->(k), (p)-[:DELIVERS_TO]->(pl)
SET cs.reserved_wk = coalesce(cs.reserved_wk, 0) + po.rate_wk
WITH d, m, p, po
UNWIND po.allocations AS a
MATCH (o:Order {id: a.order_id})
CREATE (p)-[pr:PROTECTS {qty: a.qty, arrival_day: a.arrival_day}]->(o)
SET o.status = 'protected_projected'
WITH d, m, count(DISTINCT p) AS pos_created, count(pr) AS protects_created, collect(DISTINCT o.id) AS orders
SET d.status = 'executed', d.executed_day = $day
CREATE (d)-[:LOGGED]->(act:Action {id: $action_id, type: 'execute', actor: 'executor', day: $day,
                                    payload_json: $payload_json})
RETURN d.id AS decision, pos_created, protects_created, orders, m.world_version AS world_version
