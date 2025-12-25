DO $$
DECLARE
    -- 1. DEFINE TARGET USERS
    user_ids uuid[] := ARRAY[
        '5de3f1fd-16ad-49c6-84f7-ad6c0f5d2daf',  -- quatomix@proton.me
        'ed2bb2a4-aa9d-44d5-bf9f-7a2d784c0fba' -- testtom
    ]::uuid[];
    
    target_id uuid;
BEGIN
    FOREACH target_id IN ARRAY user_ids
    LOOP
        -- 2. PURGE EXISTING DATA
        DELETE FROM entries WHERE user_id = target_id;
        DELETE FROM metrics WHERE user_id = target_id;
        DELETE FROM units WHERE user_id = target_id;
        DELETE FROM categories WHERE user_id = target_id;

        -- 3. SEED CATEGORIES
        INSERT INTO categories (name, user_id) VALUES 
            ('body', target_id), ('fitness', target_id), ('health', target_id);

        -- 4. SEED UNITS
        INSERT INTO units (name, unit_type, range_start, range_end, user_id) VALUES 
            ('kg', 'float', NULL, NULL, target_id),
            ('quality', 'int', 0, 10, target_id),
            ('reps', 'int', 0, NULL, target_id),
            ('minutes', 'int', NULL, NULL, target_id);

        -- 5. SEED METRICS
        INSERT INTO metrics (name, category_id, unit_id, user_id) VALUES 
            ('weight', (SELECT id FROM categories WHERE name='body' AND user_id=target_id), (SELECT id FROM units WHERE name='kg' AND user_id=target_id), target_id),
            ('floor press', (SELECT id FROM categories WHERE name='fitness' AND user_id=target_id), (SELECT id FROM units WHERE name='kg' AND user_id=target_id), target_id),
            ('sleep', (SELECT id FROM categories WHERE name='health' AND user_id=target_id), (SELECT id FROM units WHERE name='quality' AND user_id=target_id), target_id),
            ('yoga', (SELECT id FROM categories WHERE name='fitness' AND user_id=target_id), (SELECT id FROM units WHERE name='minutes' AND user_id=target_id), target_id);

        -- 6. SEED ENTRIES (With Random Values)
        INSERT INTO entries (metric_id, user_id, value, recorded_at)
        SELECT 
            m.id, 
            target_id, 
            (CASE 
                -- Weight: Random between 75.0 and 85.0
                WHEN m.name = 'weight' THEN random() * (85 - 75) + 75
                -- Floor Press: Random between 20.0 and 40.0
                WHEN m.name = 'floor press' THEN random() * (40 - 20) + 20
                -- Sleep Quality: Random integer between 1 and 10
                WHEN m.name = 'sleep' THEN floor(random() * (10 - 1 + 1) + 1)
                -- Yoga: Random integer between 15 and 60 minutes
                WHEN m.name = 'yoga' THEN floor(random() * (60 - 15 + 1) + 1)
            END),
            (CURRENT_DATE - (s.day || ' days')::interval)::date
        FROM metrics m
        CROSS JOIN generate_series(0, 6) AS s(day)
        WHERE m.user_id = target_id;

    END LOOP;
END $$;