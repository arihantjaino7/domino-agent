// On-hand inventory per plant and component.
MATCH (pl:Plant)-[st:STOCKS]->(k:Component)
RETURN pl.id AS plant, k.id AS component, st.on_hand AS on_hand
ORDER BY plant, component
