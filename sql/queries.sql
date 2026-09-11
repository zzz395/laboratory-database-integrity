SELECT
    s.`用户id` AS `学生用户id`,
    t.`学期编号`,
    t.`初始积分`,
    COALESCE(d.`扣分合计`, 0) AS `扣分合计`,
    GREATEST(0, t.`初始积分` - COALESCE(d.`扣分合计`, 0)) AS `剩余积分`
FROM `学生` AS s
CROSS JOIN `学期` AS t
LEFT JOIN (
    SELECT
        r.`用户id`,
        r.`学期编号`,
        SUM(v.`扣分值`) AS `扣分合计`
    FROM `预约表` AS r
    INNER JOIN `违规记录` AS v
        ON v.`预约表单号` = r.`预约表单号`
    GROUP BY r.`用户id`, r.`学期编号`
) AS d
    ON d.`用户id` = s.`用户id`
    AND d.`学期编号` = t.`学期编号`
ORDER BY s.`用户id`, t.`学期编号`;
