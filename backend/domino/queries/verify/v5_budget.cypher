// V5: total PO spend per decision stays within its budget. Expected: no rows.
MATCH (d:Decision)-[c:CREATED]->(po:PurchaseOrder)
WITH d, sum(po.qty * po.unit_price_cents) AS spend
WHERE spend > d.budget_cents
RETURN d.id AS decision, spend, d.budget_cents AS budget_cents
