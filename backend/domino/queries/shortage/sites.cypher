// Health and timing attributes of the sites in the projection.
MATCH (s:Site) WHERE s.id IN $site_ids
RETURN s.id AS site, s.capacity_factor AS factor, s.status AS status,
       s.disrupted_until AS disrupted_until, s.input_buffer_days AS input_buffer_days
ORDER BY site
