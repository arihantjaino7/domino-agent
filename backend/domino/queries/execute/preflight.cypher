// Q-EXECUTE-PREFLIGHT (read). One row per planned PO. The executor requires: N rows for N POs, the
// CAN_SUPPLY edge and component exist, the PO id is new, the PO has allocations, every allocation's
// order exists, and the edge still has free spare for the rate. (DECISIONS: M1 review)
UNWIND $pos AS po
OPTIONAL MATCH (s:Site {id: po.site_id})-[cs:CAN_SUPPLY]->(pl:Plant {id: po.plant_id})
WHERE cs.component_id = po.component_id
OPTIONAL MATCH (k:Component {id: po.component_id})
OPTIONAL MATCH (existing:PurchaseOrder {id: po.id})
OPTIONAL MATCH (o:Order) WHERE o.id IN po.order_ids
RETURN po.id AS po_id, count(DISTINCT cs) AS edges, count(DISTINCT k) AS components,
       count(DISTINCT existing) AS existing, count(DISTINCT o) AS orders_found, size(po.order_ids) AS orders_planned,
       size(po.allocations) AS allocations, max(cs.spare_wk - coalesce(cs.reserved_wk, 0)) AS free_wk, po.rate_wk AS rate_wk
ORDER BY po_id
