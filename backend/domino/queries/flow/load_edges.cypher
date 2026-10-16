// Scratch flow graph edges, in units of the target component per week.
// cap = with today's capacity factors; cap_nominal = every site healthy.
UNWIND $rows AS r
MATCH (a:F {id: r.src})
MATCH (b:F {id: r.dst})
CREATE (a)-[e:CAP {cap: r.cap, cap_nominal: r.cap_nominal}]->(b)
RETURN count(e) AS created
