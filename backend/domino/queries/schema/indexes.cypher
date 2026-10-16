// Range indexes on every id we look up (PLAN §5.9), plus the Place full-text index.
// Place.id lets one loader query attach LOCATED_IN/SHIPS_VIA/DELIVERS_TO to any location.
// The PurchaseOrder.id exact-match index must exist before the unique constraint (SPIKE #10).
CREATE INDEX FOR (n:Site) ON (n.id);
CREATE INDEX FOR (n:Order) ON (n.id);
CREATE INDEX FOR (n:Component) ON (n.id);
CREATE INDEX FOR (n:Plant) ON (n.id);
CREATE INDEX FOR (n:PurchaseOrder) ON (n.id);
CREATE INDEX FOR (n:Incident) ON (n.id);
CREATE INDEX FOR (n:Place) ON (n.id);
CREATE INDEX FOR (n:Supplier) ON (n.id);
CREATE INDEX FOR (n:Product) ON (n.id);
CREATE INDEX FOR (n:Customer) ON (n.id);
CALL db.idx.fulltext.createNodeIndex('Place', 'name', 'aliases')
