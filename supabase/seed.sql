DO $$
DECLARE
    -- 1. DEFINE TARGET USERS
    user_ids uuid[] := ARRAY[
        '5de3f1fd-16ad-49c6-84f7-ad6c0f5d2daf',  -- quatomix@proton.me
        'ed2bb2a4-aa9d-44d5-bf9f-7a2d784c0fba'  -- testtom
    ]::uuid[];
    
    target_id uuid;
BEGIN
    FOREACH target_id IN ARRAY user_ids
    LOOP
        -- 2. PURGE EXISTING DATA (Removed units table from purge)
        DELETE FROM entries WHERE user_id = target_id;
        DELETE FROM metrics WHERE user_id = target_id;
        DELETE FROM categories WHERE user_id = target_id;

        -- 3. SEED CATEGORIES
        INSERT INTO categories (name, user_id) VALUES 
            ('body', target_id), ('fitness', target_id), ('health', target_id);

        -- 4. SEED METRICS (Now contains Unit data directly)
        -- We no longer need to select IDs from a separate units table.
        INSERT INTO metrics (name, unit_name, unit_type, range_start, range_end, category_id, user_id) VALUES 
            ('weight', 'kg', 'float', NULL, NULL, 
                (SELECT id FROM categories WHERE name='body' AND user_id=target_id), target_id),
            ('floor press', 'kg', 'float', NULL, NULL, 
                (SELECT id FROM categories WHERE name='fitness' AND user_id=target_id), target_id),
            ('sleep', 'quality', 'integer_range', 0, 10, 
                (SELECT id FROM categories WHERE name='health' AND user_id=target_id), target_id),
            ('yoga', 'minutes', 'integer', NULL, NULL, 
                (SELECT id FROM categories WHERE name='fitness' AND user_id=target_id), target_id);

        -- 5. SEED ENTRIES (logic remains identical)
        INSERT INTO entries (metric_id, user_id, value, recorded_at)
        SELECT 
            m.id, 
            target_id, 
            (CASE 
                WHEN m.name = 'weight' THEN random() * (85 - 75) + 75
                WHEN m.name = 'floor press' THEN random() * (40 - 20) + 20
                WHEN m.name = 'sleep' THEN floor(random() * (10 - 1 + 1) + 1)
                WHEN m.name = 'yoga' THEN floor(random() * (60 - 15 + 1) + 1)
            END),
            (CURRENT_DATE - (s.day || ' days')::interval)::date
        FROM metrics m
        CROSS JOIN generate_series(0, 6) AS s(day)
        WHERE m.user_id = target_id;

    END LOOP;
END $$;