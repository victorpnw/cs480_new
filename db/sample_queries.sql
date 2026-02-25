WITH defect_stats AS (
    SELECT 
        d.defect_code,
        COUNT(DISTINCT ir.lot_id) AS num_lots,
        COUNT(DISTINCT DATE_TRUNC('week', ir.inspection_date)) AS num_weeks,
        MIN(ir.inspection_date) AS first_seen,
        MAX(ir.inspection_date) AS last_seen,
        SUM(ir.qty_defects) AS total_qty,
        BOOL_AND(ir.is_data_complete) AS data_is_complete
    FROM inspection_records ir
    JOIN defects d ON ir.defect_id = d.id
    WHERE ir.qty_defects > 0  -- AC3: Ignore zero-defect records
    GROUP BY d.defect_code
)
SELECT 
    defect_code,
    CASE 
        WHEN data_is_complete = FALSE THEN 'Insufficient data' -- AC4
        WHEN num_weeks > 1 AND num_lots > 1 THEN 'Recurring'    -- AC1
        ELSE 'Not recurring'                                   -- AC2
    END AS status,
    num_weeks,
    num_lots,
    first_seen,
    last_seen,
    total_qty
FROM defect_stats
ORDER BY 
    -- AC9: Default sorting logic
    (CASE 
        WHEN (num_weeks > 1 AND num_lots > 1 AND data_is_complete = TRUE) THEN 1 
        WHEN data_is_complete = FALSE THEN 2 
        ELSE 3 
     END) ASC,
    num_weeks DESC, 
    num_lots DESC;




SELECT 
    DATE_TRUNC('week', ir.inspection_date) AS week_starting,
    COUNT(DISTINCT l.lot_id) AS lots_in_week,
    SUM(ir.qty_defects) AS total_qty_this_week,
    STRING_AGG(DISTINCT l.lot_id, ', ') AS lot_list
FROM inspection_records ir
JOIN defects d ON ir.defect_id = d.id
JOIN lots l ON ir.lot_id = l.id
WHERE d.defect_code = 'DEF-001' -- Example input
  AND ir.qty_defects > 0
GROUP BY week_starting
ORDER BY week_starting DESC;
