INSERT INTO `学院` (`学院编号`, `学院名称`) VALUES
('COL_TEST_A', '测试学院A'),
('COL_TEST_B', '测试学院B');

INSERT INTO `用户` (`用户id`, `姓名`, `用户状态`) VALUES
('USR_STUDENT_ONLY', '合成学生甲', '有效'),
('USR_DUAL_ROLE', '合成双角色用户', '有效'),
('USR_MANAGER_A', '合成负责人甲', '有效'),
('USR_MANAGER_B', '合成负责人乙', '有效'),
('USR_GENERAL', '合成普通用户', '有效');

INSERT INTO `学生` (`用户id`, `学院编号`) VALUES
('USR_STUDENT_ONLY', 'COL_TEST_A'),
('USR_DUAL_ROLE', 'COL_TEST_A');

INSERT INTO `教师` (`用户id`, `学院编号`) VALUES
('USR_DUAL_ROLE', 'COL_TEST_A'),
('USR_MANAGER_A', 'COL_TEST_A'),
('USR_MANAGER_B', 'COL_TEST_B');

INSERT INTO `实验室负责人` (`用户id`) VALUES
('USR_MANAGER_A'),
('USR_MANAGER_B');

INSERT INTO `实验室` (`实验室编号`, `学院编号`, `负责人用户id`, `实验室名称`, `容纳人数`, `使用状态`, `实验室照片`) VALUES
('LAB_TEST_A1', 'COL_TEST_A', 'USR_MANAGER_A', '测试实验室A1', 20, '可用', NULL),
('LAB_TEST_A2', 'COL_TEST_A', 'USR_MANAGER_A', '测试实验室A2', 8, '可用', NULL),
('LAB_TEST_B1', 'COL_TEST_B', 'USR_MANAGER_B', '测试实验室B1', 4, '维修中', NULL);

INSERT INTO `设备类别` (`类别码`, `类别名称`) VALUES
('CAT_TEST_BASIC', '测试基础设备类'),
('CAT_TEST_MEASURE', '测试测量设备类');

INSERT INTO `供应商` (`供应商编号`, `供应商名称`, `电话`) VALUES
('SUP_TEST_A', '测试供应商A', NULL),
('SUP_TEST_B', '测试供应商B', '000-TEST-0002');

INSERT INTO `实验设备` (`设备编号`, `类别码`, `供应商编号`, `实验室编号`, `型号`, `规格`, `购置日期`, `单价`, `保修到期日`, `设备状态`) VALUES
('EQ_TEST_01', 'CAT_TEST_BASIC', 'SUP_TEST_A', 'LAB_TEST_A2', 'SYN-MODEL-01', 'SYN-SPEC-01', '2025-01-01', 0.00, '2025-01-01', '在用'),
('EQ_TEST_02', 'CAT_TEST_BASIC', 'SUP_TEST_A', 'LAB_TEST_A1', 'SYN-MODEL-02', 'SYN-SPEC-02', '2025-02-01', 1250.00, '2027-02-01', '在用'),
('EQ_TEST_03', 'CAT_TEST_MEASURE', 'SUP_TEST_B', 'LAB_TEST_B1', 'SYN-MODEL-03', 'SYN-SPEC-03', '2025-03-01', 5600.00, '2028-03-01', '维修'),
('EQ_TEST_04', 'CAT_TEST_MEASURE', 'SUP_TEST_B', 'LAB_TEST_A2', 'SYN-MODEL-04', 'SYN-SPEC-04', '2025-04-01', 99.99, '2026-04-01', '在用');

INSERT INTO `维修人员` (`维修人员工号`, `姓名`, `电话`) VALUES
('WORKER_TEST_01', '合成维修员甲', '000-TEST-1001'),
('WORKER_TEST_02', '合成维修员乙', '000-TEST-1002');

INSERT INTO `学期` (`学期编号`, `学期名称`, `开始时间`, `结束时间`, `初始积分`) VALUES
('TERM_TEST_1', '测试学期一', '2026-01-01 00:00:00.000000', '2026-07-01 00:00:00.000000', 12),
('TERM_TEST_2', '测试学期二', '2026-09-01 00:00:00.000000', '2027-02-01 00:00:00.000000', 12);

INSERT INTO `课程` (`课程编号`, `授课教师用户id`, `课程名称`) VALUES
('COURSE_TEST_1', 'USR_DUAL_ROLE', '测试课程一'),
('COURSE_TEST_2', 'USR_MANAGER_A', '测试课程二');

INSERT INTO `预约表` (`预约表单号`, `实验室编号`, `用户id`, `学期编号`, `课程编号`, `审核人用户id`, `预约类型`, `开始时间`, `结束时间`, `人数`, `用途`, `预约状态`, `驳回原因`) VALUES
('RES_TEST_01', 'LAB_TEST_A1', 'USR_DUAL_ROLE', 'TERM_TEST_1', NULL, 'USR_MANAGER_A', '个人', '2026-03-01 10:00:00.000000', '2026-03-01 11:00:00.000000', 2, '合成个人预约一', '已通过', NULL),
('RES_TEST_02', 'LAB_TEST_A1', 'USR_DUAL_ROLE', 'TERM_TEST_1', NULL, 'USR_MANAGER_A', '个人', '2026-03-02 12:00:00.000000', '2026-03-02 13:00:00.000000', 3, '合成个人预约二', '已结束', NULL),
('RES_TEST_03', 'LAB_TEST_A2', 'USR_DUAL_ROLE', 'TERM_TEST_1', NULL, 'USR_MANAGER_A', '个人', '2026-03-03 14:00:00.000000', '2026-03-03 15:00:00.000000', 1, '合成爽约场景', '爽约', NULL),
('RES_TEST_04', 'LAB_TEST_A1', 'USR_DUAL_ROLE', 'TERM_TEST_2', 'COURSE_TEST_1', 'USR_MANAGER_A', '课程', '2026-10-01 10:00:00.000000', '2026-10-01 11:00:00.000000', 10, '合成课程预约一', '已结束', NULL),
('RES_TEST_05', 'LAB_TEST_A2', 'USR_GENERAL', 'TERM_TEST_2', NULL, NULL, '个人', '2026-10-02 09:00:00.000000', '2026-10-02 10:00:00.000000', 2, '合成待审核预约', '待审核', NULL),
('RES_TEST_06', 'LAB_TEST_B1', 'USR_GENERAL', 'TERM_TEST_2', NULL, 'USR_MANAGER_B', '个人', '2026-10-03 09:00:00.000000', '2026-10-03 10:00:00.000000', 2, '合成驳回预约', '已驳回', '合成测试驳回原因'),
('RES_TEST_07', 'LAB_TEST_A2', 'USR_GENERAL', 'TERM_TEST_2', NULL, 'USR_MANAGER_A', '个人', '2026-10-04 09:00:00.000000', '2026-10-04 10:00:00.000000', 2, '合成取消预约', '已取消', NULL),
('RES_TEST_08', 'LAB_TEST_A1', 'USR_MANAGER_A', 'TERM_TEST_2', 'COURSE_TEST_2', 'USR_MANAGER_B', '课程', '2026-10-05 15:00:00.000000', '2026-10-05 16:00:00.000000', 12, '合成课程预约二', '已通过', NULL);

INSERT INTO `签到记录` (`签到记录id`, `预约表单号`, `签到方式`, `签到时间`, `签退时间`, `超时备注`) VALUES
('CHECKIN_TEST_01', 'RES_TEST_01', '扫码', '2026-03-01 09:50:00.000000', NULL, NULL),
('CHECKIN_TEST_02', 'RES_TEST_02', '手工', '2026-03-02 12:05:00.000000', '2026-03-02 12:50:00.000000', NULL),
('CHECKIN_TEST_03', 'RES_TEST_04', '扫码', '2026-10-01 09:55:00.000000', '2026-10-01 11:10:00.000000', '合成超时说明');

INSERT INTO `违规记录` (`违规id`, `预约表单号`, `签到记录id`, `违规类型`, `扣分值`, `违规时间`) VALUES
('VIOL_TEST_01', 'RES_TEST_03', NULL, '爽约', 2, '2026-03-03 14:20:00.000000'),
('VIOL_TEST_02', 'RES_TEST_02', 'CHECKIN_TEST_02', '迟到', 1, '2026-03-02 12:05:00.000000'),
('VIOL_TEST_03', 'RES_TEST_02', 'CHECKIN_TEST_02', '早退', 1, '2026-03-02 12:50:00.000000'),
('VIOL_TEST_04', 'RES_TEST_04', 'CHECKIN_TEST_03', '超时使用', 1, '2026-10-01 11:10:00.000000');

INSERT INTO `预约设备` (`使用记录编号`, `预约表单号`, `设备编号`) VALUES
('RESEQ_TEST_01', 'RES_TEST_01', 'EQ_TEST_01'),
('RESEQ_TEST_02', 'RES_TEST_01', 'EQ_TEST_02'),
('RESEQ_TEST_03', 'RES_TEST_02', 'EQ_TEST_01'),
('RESEQ_TEST_04', 'RES_TEST_04', 'EQ_TEST_03'),
('RESEQ_TEST_05', 'RES_TEST_08', 'EQ_TEST_02'),
('RESEQ_TEST_06', 'RES_TEST_08', 'EQ_TEST_04');

INSERT INTO `预约变更` (`变更记录编号`, `预约表单号`, `操作人用户id`, `变更类型`, `变更原因`, `变更时间`) VALUES
('CHANGE_TEST_01', 'RES_TEST_07', 'USR_MANAGER_A', '取消', '合成取消原因', '2026-09-20 08:00:00.000000'),
('CHANGE_TEST_02', 'RES_TEST_08', 'USR_MANAGER_B', '改期', '合成改期原因', '2026-09-21 08:00:00.000000');

INSERT INTO `故障报修单` (`报修单ID`, `设备编号`, `报修人用户id`, `责任负责人用户id`, `指派维修人员工号`, `故障描述`, `故障图片`, `紧急程度`, `单据状态`, `报修时间`, `计划维修时间`, `拒绝原因`) VALUES
('REPAIR_TEST_01', 'EQ_TEST_01', 'USR_GENERAL', 'USR_MANAGER_A', NULL, '合成待指派故障', NULL, '一般', '待指派', '2026-04-01 08:00:00.000000', NULL, NULL),
('REPAIR_TEST_02', 'EQ_TEST_02', 'USR_GENERAL', 'USR_MANAGER_A', 'WORKER_TEST_01', '合成维修中故障', NULL, '一般', '维修中', '2026-04-02 08:00:00.000000', '2026-04-02 10:00:00.000000', NULL),
('REPAIR_TEST_03', 'EQ_TEST_03', 'USR_GENERAL', 'USR_MANAGER_B', 'WORKER_TEST_02', '合成待验收故障', NULL, '紧急', '待验收', '2026-04-03 08:00:00.000000', '2026-04-03 10:00:00.000000', NULL),
('REPAIR_TEST_04', 'EQ_TEST_04', 'USR_GENERAL', 'USR_MANAGER_A', 'WORKER_TEST_02', '合成已完成故障', NULL, '一般', '已完成', '2026-04-04 08:00:00.000000', '2026-04-04 10:00:00.000000', NULL),
('REPAIR_TEST_05', 'EQ_TEST_01', 'USR_DUAL_ROLE', 'USR_MANAGER_A', NULL, '合成拒绝故障', NULL, '一般', '拒绝', '2026-04-05 08:00:00.000000', NULL, '合成拒绝原因');

INSERT INTO `执行维修` (`维修记录编号`, `报修单ID`, `维修人员工号`, `维修内容`, `开始时间`, `完成时间`, `维修费用`, `验收结果`, `验收人用户id`, `验收时间`) VALUES
('EXEC_TEST_01', 'REPAIR_TEST_02', 'WORKER_TEST_01', '合成未完成维修', '2026-04-02 10:00:00.000000', NULL, NULL, NULL, NULL, NULL),
('EXEC_TEST_02', 'REPAIR_TEST_03', 'WORKER_TEST_02', '合成待验收维修', '2026-04-03 10:00:00.000000', '2026-04-03 11:00:00.000000', 25.00, NULL, NULL, NULL),
('EXEC_TEST_03', 'REPAIR_TEST_04', 'WORKER_TEST_01', '合成首次返修', '2026-04-04 10:00:00.000000', '2026-04-04 11:00:00.000000', 10.00, '返修', 'USR_MANAGER_A', '2026-04-04 12:00:00.000000'),
('EXEC_TEST_04', 'REPAIR_TEST_04', 'WORKER_TEST_02', '合成再次维修并通过', '2026-04-04 13:00:00.000000', '2026-04-04 14:00:00.000000', 15.00, '通过', 'USR_MANAGER_A', '2026-04-04 15:00:00.000000');

INSERT INTO `安全检查表` (`检查记录id`, `实验室编号`, `检查人用户id`, `检查日期`, `水电状态`, `消防状态`, `设备状态`, `门窗状态`, `隐患记录`, `整改结果`) VALUES
('SAFE_TEST_01', 'LAB_TEST_A1', 'USR_MANAGER_A', '2026-05-01', '合格', '合格', '合格', '合格', NULL, NULL),
('SAFE_TEST_02', 'LAB_TEST_B1', 'USR_MANAGER_B', '2026-05-02', '合格', '不合格', '合格', '合格', '合成消防检查隐患', '合成整改已完成');

INSERT INTO `借用` (`借用记录编号`, `经办负责人用户id`, `借用人用户id`, `设备编号`, `借出时间`, `计划归还时间`, `实际归还时间`, `损坏描述`, `赔偿金额`) VALUES
('LOAN_TEST_01', 'USR_MANAGER_A', 'USR_GENERAL', 'EQ_TEST_01', '2026-05-10 08:00:00.000000', '2026-05-12 08:00:00.000000', NULL, NULL, NULL),
('LOAN_TEST_02', 'USR_MANAGER_B', 'USR_DUAL_ROLE', 'EQ_TEST_03', '2026-05-11 08:00:00.000000', '2026-05-13 08:00:00.000000', '2026-05-13 07:00:00.000000', '合成轻微损坏说明', 0.00);

INSERT INTO `设备移库记录` (`移库记录编号`, `设备编号`, `原实验室编号`, `目标实验室编号`, `移动时间`, `移动原因`) VALUES
('MOVE_TEST_01', 'EQ_TEST_01', 'LAB_TEST_A1', 'LAB_TEST_A2', '2026-02-01 08:00:00.000000', '合成位置调整');
