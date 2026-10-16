// flag_orders_at_risk: a reversible, internal mark on orders (policy: auto).
MATCH (o:Order) WHERE o.id IN $order_ids
SET o.risk_flag = true, o.risk_reason = $reason
RETURN count(o) AS flagged
