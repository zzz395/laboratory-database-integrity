CREATE TABLE `学院` (
    `学院编号` VARCHAR(32) NOT NULL,
    `学院名称` VARCHAR(100) NOT NULL,
    CONSTRAINT `pk_college` PRIMARY KEY (`学院编号`),
    CONSTRAINT `ck_college_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`学院编号`)) > 0),
    CONSTRAINT `ck_college_name_nonblank` CHECK (CHAR_LENGTH(TRIM(`学院名称`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `用户` (
    `用户id` VARCHAR(32) NOT NULL,
    `姓名` VARCHAR(100) NOT NULL,
    `用户状态` VARCHAR(16) NOT NULL,
    CONSTRAINT `pk_user` PRIMARY KEY (`用户id`),
    CONSTRAINT `ck_user_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`用户id`)) > 0),
    CONSTRAINT `ck_user_name_nonblank` CHECK (CHAR_LENGTH(TRIM(`姓名`)) > 0),
    CONSTRAINT `ck_user_status` CHECK (`用户状态` IN ('有效', '停用'))
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `学生` (
    `用户id` VARCHAR(32) NOT NULL,
    `学院编号` VARCHAR(32) NOT NULL,
    CONSTRAINT `pk_student` PRIMARY KEY (`用户id`),
    INDEX `ix_student_college` (`学院编号`),
    CONSTRAINT `fk_student_user` FOREIGN KEY (`用户id`) REFERENCES `用户` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_student_college` FOREIGN KEY (`学院编号`) REFERENCES `学院` (`学院编号`) ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `教师` (
    `用户id` VARCHAR(32) NOT NULL,
    `学院编号` VARCHAR(32) NOT NULL,
    CONSTRAINT `pk_teacher` PRIMARY KEY (`用户id`),
    INDEX `ix_teacher_college` (`学院编号`),
    CONSTRAINT `fk_teacher_user` FOREIGN KEY (`用户id`) REFERENCES `用户` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_teacher_college` FOREIGN KEY (`学院编号`) REFERENCES `学院` (`学院编号`) ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `实验室负责人` (
    `用户id` VARCHAR(32) NOT NULL,
    CONSTRAINT `pk_manager` PRIMARY KEY (`用户id`),
    CONSTRAINT `fk_manager_teacher` FOREIGN KEY (`用户id`) REFERENCES `教师` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `实验室` (
    `实验室编号` VARCHAR(32) NOT NULL,
    `学院编号` VARCHAR(32) NOT NULL,
    `负责人用户id` VARCHAR(32) NOT NULL,
    `实验室名称` VARCHAR(100) NOT NULL,
    `容纳人数` INT NOT NULL,
    `使用状态` VARCHAR(16) NOT NULL,
    `实验室照片` VARCHAR(512) NULL,
    CONSTRAINT `pk_laboratory` PRIMARY KEY (`实验室编号`),
    INDEX `ix_laboratory_college` (`学院编号`),
    INDEX `ix_laboratory_manager` (`负责人用户id`),
    CONSTRAINT `fk_laboratory_college` FOREIGN KEY (`学院编号`) REFERENCES `学院` (`学院编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_laboratory_manager` FOREIGN KEY (`负责人用户id`) REFERENCES `实验室负责人` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_laboratory_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`实验室编号`)) > 0),
    CONSTRAINT `ck_laboratory_name_nonblank` CHECK (CHAR_LENGTH(TRIM(`实验室名称`)) > 0),
    CONSTRAINT `ck_laboratory_capacity` CHECK (`容纳人数` > 0),
    CONSTRAINT `ck_laboratory_status` CHECK (`使用状态` IN ('可用', '停用', '维修中')),
    CONSTRAINT `ck_laboratory_photo` CHECK (`实验室照片` IS NULL OR CHAR_LENGTH(TRIM(`实验室照片`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `设备类别` (
    `类别码` VARCHAR(32) NOT NULL,
    `类别名称` VARCHAR(100) NOT NULL,
    CONSTRAINT `pk_equipment_category` PRIMARY KEY (`类别码`),
    CONSTRAINT `ck_equipment_category_id` CHECK (CHAR_LENGTH(TRIM(`类别码`)) > 0),
    CONSTRAINT `ck_equipment_category_name` CHECK (CHAR_LENGTH(TRIM(`类别名称`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `供应商` (
    `供应商编号` VARCHAR(32) NOT NULL,
    `供应商名称` VARCHAR(100) NOT NULL,
    `电话` VARCHAR(30) NULL,
    CONSTRAINT `pk_supplier` PRIMARY KEY (`供应商编号`),
    CONSTRAINT `ck_supplier_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`供应商编号`)) > 0),
    CONSTRAINT `ck_supplier_name_nonblank` CHECK (CHAR_LENGTH(TRIM(`供应商名称`)) > 0),
    CONSTRAINT `ck_supplier_phone` CHECK (`电话` IS NULL OR CHAR_LENGTH(TRIM(`电话`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `实验设备` (
    `设备编号` VARCHAR(32) NOT NULL,
    `类别码` VARCHAR(32) NOT NULL,
    `供应商编号` VARCHAR(32) NOT NULL,
    `实验室编号` VARCHAR(32) NOT NULL,
    `型号` VARCHAR(100) NOT NULL,
    `规格` VARCHAR(100) NOT NULL,
    `购置日期` DATE NOT NULL,
    `单价` DECIMAL(12,2) NOT NULL,
    `保修到期日` DATE NOT NULL,
    `设备状态` VARCHAR(16) NOT NULL,
    CONSTRAINT `pk_equipment` PRIMARY KEY (`设备编号`),
    INDEX `ix_equipment_category` (`类别码`),
    INDEX `ix_equipment_supplier` (`供应商编号`),
    INDEX `ix_equipment_laboratory` (`实验室编号`),
    CONSTRAINT `fk_equipment_category` FOREIGN KEY (`类别码`) REFERENCES `设备类别` (`类别码`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_equipment_supplier` FOREIGN KEY (`供应商编号`) REFERENCES `供应商` (`供应商编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_equipment_laboratory` FOREIGN KEY (`实验室编号`) REFERENCES `实验室` (`实验室编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_equipment_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`设备编号`)) > 0),
    CONSTRAINT `ck_equipment_model_nonblank` CHECK (CHAR_LENGTH(TRIM(`型号`)) > 0),
    CONSTRAINT `ck_equipment_spec_nonblank` CHECK (CHAR_LENGTH(TRIM(`规格`)) > 0),
    CONSTRAINT `ck_equipment_price` CHECK (`单价` >= 0),
    CONSTRAINT `ck_equipment_warranty` CHECK (`保修到期日` >= `购置日期`),
    CONSTRAINT `ck_equipment_status` CHECK (`设备状态` IN ('在用', '维修', '报废'))
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `维修人员` (
    `维修人员工号` VARCHAR(32) NOT NULL,
    `姓名` VARCHAR(100) NOT NULL,
    `电话` VARCHAR(30) NOT NULL,
    CONSTRAINT `pk_maintenance_worker` PRIMARY KEY (`维修人员工号`),
    CONSTRAINT `ck_worker_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`维修人员工号`)) > 0),
    CONSTRAINT `ck_worker_name_nonblank` CHECK (CHAR_LENGTH(TRIM(`姓名`)) > 0),
    CONSTRAINT `ck_worker_phone_nonblank` CHECK (CHAR_LENGTH(TRIM(`电话`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `学期` (
    `学期编号` VARCHAR(32) NOT NULL,
    `学期名称` VARCHAR(100) NOT NULL,
    `开始时间` DATETIME(6) NOT NULL,
    `结束时间` DATETIME(6) NOT NULL,
    `初始积分` INT NOT NULL DEFAULT 12,
    CONSTRAINT `pk_term` PRIMARY KEY (`学期编号`),
    CONSTRAINT `ck_term_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`学期编号`)) > 0),
    CONSTRAINT `ck_term_name_nonblank` CHECK (CHAR_LENGTH(TRIM(`学期名称`)) > 0),
    CONSTRAINT `ck_term_period` CHECK (`开始时间` < `结束时间`),
    CONSTRAINT `ck_term_initial_points` CHECK (`初始积分` >= 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `课程` (
    `课程编号` VARCHAR(32) NOT NULL,
    `授课教师用户id` VARCHAR(32) NOT NULL,
    `课程名称` VARCHAR(100) NOT NULL,
    CONSTRAINT `pk_course` PRIMARY KEY (`课程编号`),
    INDEX `ix_course_teacher` (`授课教师用户id`),
    CONSTRAINT `fk_course_teacher` FOREIGN KEY (`授课教师用户id`) REFERENCES `教师` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_course_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`课程编号`)) > 0),
    CONSTRAINT `ck_course_name_nonblank` CHECK (CHAR_LENGTH(TRIM(`课程名称`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `预约表` (
    `预约表单号` VARCHAR(32) NOT NULL,
    `实验室编号` VARCHAR(32) NOT NULL,
    `用户id` VARCHAR(32) NOT NULL,
    `学期编号` VARCHAR(32) NOT NULL,
    `课程编号` VARCHAR(32) NULL,
    `审核人用户id` VARCHAR(32) NULL,
    `预约类型` VARCHAR(16) NOT NULL,
    `开始时间` DATETIME(6) NOT NULL,
    `结束时间` DATETIME(6) NOT NULL,
    `人数` INT NOT NULL,
    `用途` VARCHAR(100) NOT NULL,
    `预约状态` VARCHAR(16) NOT NULL,
    `驳回原因` VARCHAR(1000) NULL,
    CONSTRAINT `pk_reservation` PRIMARY KEY (`预约表单号`),
    INDEX `ix_reservation_laboratory` (`实验室编号`),
    INDEX `ix_reservation_user` (`用户id`),
    INDEX `ix_reservation_term` (`学期编号`),
    INDEX `ix_reservation_course` (`课程编号`),
    INDEX `ix_reservation_reviewer` (`审核人用户id`),
    CONSTRAINT `fk_reservation_laboratory` FOREIGN KEY (`实验室编号`) REFERENCES `实验室` (`实验室编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_reservation_user` FOREIGN KEY (`用户id`) REFERENCES `用户` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_reservation_term` FOREIGN KEY (`学期编号`) REFERENCES `学期` (`学期编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_reservation_course` FOREIGN KEY (`课程编号`) REFERENCES `课程` (`课程编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_reservation_reviewer` FOREIGN KEY (`审核人用户id`) REFERENCES `实验室负责人` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_reservation_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`预约表单号`)) > 0),
    CONSTRAINT `ck_reservation_kind_course` CHECK ((`预约类型` = '个人' AND `课程编号` IS NULL) OR (`预约类型` = '课程' AND `课程编号` IS NOT NULL)),
    CONSTRAINT `ck_reservation_period` CHECK (`开始时间` < `结束时间`),
    CONSTRAINT `ck_reservation_people` CHECK (`人数` > 0),
    CONSTRAINT `ck_reservation_purpose` CHECK (CHAR_LENGTH(TRIM(`用途`)) > 0),
    CONSTRAINT `ck_reservation_state` CHECK (
        (`预约状态` = '待审核' AND `审核人用户id` IS NULL AND `驳回原因` IS NULL) OR
        (`预约状态` = '已驳回' AND `审核人用户id` IS NOT NULL AND `驳回原因` IS NOT NULL AND CHAR_LENGTH(TRIM(`驳回原因`)) > 0) OR
        (`预约状态` IN ('已通过', '已结束', '爽约') AND `审核人用户id` IS NOT NULL AND `驳回原因` IS NULL) OR
        (`预约状态` = '已取消' AND `驳回原因` IS NULL)
    )
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `签到记录` (
    `签到记录id` VARCHAR(32) NOT NULL,
    `预约表单号` VARCHAR(32) NOT NULL,
    `签到方式` VARCHAR(16) NOT NULL,
    `签到时间` DATETIME(6) NOT NULL,
    `签退时间` DATETIME(6) NULL,
    `超时备注` VARCHAR(1000) NULL,
    CONSTRAINT `pk_checkin` PRIMARY KEY (`签到记录id`),
    CONSTRAINT `uq_checkin_reservation` UNIQUE (`预约表单号`),
    CONSTRAINT `uq_checkin_reservation_id` UNIQUE (`预约表单号`, `签到记录id`),
    CONSTRAINT `fk_checkin_reservation` FOREIGN KEY (`预约表单号`) REFERENCES `预约表` (`预约表单号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_checkin_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`签到记录id`)) > 0),
    CONSTRAINT `ck_checkin_method` CHECK (`签到方式` IN ('手工', '扫码')),
    CONSTRAINT `ck_checkin_signout` CHECK (`签退时间` IS NULL OR `签退时间` >= `签到时间`),
    CONSTRAINT `ck_checkin_note` CHECK (`超时备注` IS NULL OR CHAR_LENGTH(TRIM(`超时备注`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `违规记录` (
    `违规id` VARCHAR(32) NOT NULL,
    `预约表单号` VARCHAR(32) NOT NULL,
    `签到记录id` VARCHAR(32) NULL,
    `违规类型` VARCHAR(16) NOT NULL,
    `扣分值` INT NOT NULL,
    `违规时间` DATETIME(6) NOT NULL,
    CONSTRAINT `pk_violation` PRIMARY KEY (`违规id`),
    CONSTRAINT `uq_violation_reservation_type` UNIQUE (`预约表单号`, `违规类型`),
    INDEX `ix_violation_checkin` (`预约表单号`, `签到记录id`),
    CONSTRAINT `fk_violation_reservation` FOREIGN KEY (`预约表单号`) REFERENCES `预约表` (`预约表单号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_violation_checkin` FOREIGN KEY (`预约表单号`, `签到记录id`) REFERENCES `签到记录` (`预约表单号`, `签到记录id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_violation_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`违规id`)) > 0),
    CONSTRAINT `ck_violation_type_score` CHECK ((`违规类型` = '爽约' AND `扣分值` = 2) OR (`违规类型` IN ('迟到', '早退', '超时使用') AND `扣分值` = 1)),
    CONSTRAINT `ck_violation_checkin_presence` CHECK ((`违规类型` = '爽约' AND `签到记录id` IS NULL) OR (`违规类型` IN ('迟到', '早退', '超时使用') AND `签到记录id` IS NOT NULL))
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `预约设备` (
    `使用记录编号` VARCHAR(32) NOT NULL,
    `预约表单号` VARCHAR(32) NOT NULL,
    `设备编号` VARCHAR(32) NOT NULL,
    CONSTRAINT `pk_reservation_equipment` PRIMARY KEY (`使用记录编号`),
    CONSTRAINT `uq_reservation_equipment_pair` UNIQUE (`预约表单号`, `设备编号`),
    INDEX `ix_reservation_equipment_device` (`设备编号`),
    CONSTRAINT `fk_reservation_equipment_reservation` FOREIGN KEY (`预约表单号`) REFERENCES `预约表` (`预约表单号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_reservation_equipment_device` FOREIGN KEY (`设备编号`) REFERENCES `实验设备` (`设备编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_reservation_equipment_id` CHECK (CHAR_LENGTH(TRIM(`使用记录编号`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `预约变更` (
    `变更记录编号` VARCHAR(32) NOT NULL,
    `预约表单号` VARCHAR(32) NOT NULL,
    `操作人用户id` VARCHAR(32) NOT NULL,
    `变更类型` VARCHAR(16) NOT NULL,
    `变更原因` VARCHAR(1000) NOT NULL,
    `变更时间` DATETIME(6) NOT NULL,
    CONSTRAINT `pk_reservation_change` PRIMARY KEY (`变更记录编号`),
    INDEX `ix_reservation_change_reservation` (`预约表单号`),
    INDEX `ix_reservation_change_actor` (`操作人用户id`),
    CONSTRAINT `fk_reservation_change_reservation` FOREIGN KEY (`预约表单号`) REFERENCES `预约表` (`预约表单号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_reservation_change_actor` FOREIGN KEY (`操作人用户id`) REFERENCES `用户` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_reservation_change_id` CHECK (CHAR_LENGTH(TRIM(`变更记录编号`)) > 0),
    CONSTRAINT `ck_reservation_change_type` CHECK (`变更类型` IN ('取消', '改期')),
    CONSTRAINT `ck_reservation_change_reason` CHECK (CHAR_LENGTH(TRIM(`变更原因`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `故障报修单` (
    `报修单ID` VARCHAR(32) NOT NULL,
    `设备编号` VARCHAR(32) NOT NULL,
    `报修人用户id` VARCHAR(32) NOT NULL,
    `责任负责人用户id` VARCHAR(32) NOT NULL,
    `指派维修人员工号` VARCHAR(32) NULL,
    `故障描述` VARCHAR(1000) NOT NULL,
    `故障图片` VARCHAR(512) NULL,
    `紧急程度` VARCHAR(16) NOT NULL,
    `单据状态` VARCHAR(16) NOT NULL,
    `报修时间` DATETIME(6) NOT NULL,
    `计划维修时间` DATETIME(6) NULL,
    `拒绝原因` VARCHAR(1000) NULL,
    CONSTRAINT `pk_fault_report` PRIMARY KEY (`报修单ID`),
    INDEX `ix_fault_report_equipment` (`设备编号`),
    INDEX `ix_fault_report_reporter` (`报修人用户id`),
    INDEX `ix_fault_report_manager` (`责任负责人用户id`),
    INDEX `ix_fault_report_assignee` (`指派维修人员工号`),
    CONSTRAINT `fk_fault_report_equipment` FOREIGN KEY (`设备编号`) REFERENCES `实验设备` (`设备编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_fault_report_reporter` FOREIGN KEY (`报修人用户id`) REFERENCES `用户` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_fault_report_manager` FOREIGN KEY (`责任负责人用户id`) REFERENCES `实验室负责人` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_fault_report_assignee` FOREIGN KEY (`指派维修人员工号`) REFERENCES `维修人员` (`维修人员工号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_fault_report_id` CHECK (CHAR_LENGTH(TRIM(`报修单ID`)) > 0),
    CONSTRAINT `ck_fault_report_description` CHECK (CHAR_LENGTH(TRIM(`故障描述`)) > 0),
    CONSTRAINT `ck_fault_report_image` CHECK (`故障图片` IS NULL OR CHAR_LENGTH(TRIM(`故障图片`)) > 0),
    CONSTRAINT `ck_fault_report_urgency` CHECK (`紧急程度` IN ('一般', '紧急')),
    CONSTRAINT `ck_fault_report_schedule` CHECK (`计划维修时间` IS NULL OR `计划维修时间` >= `报修时间`),
    CONSTRAINT `ck_fault_report_state` CHECK (
        (`单据状态` = '待指派' AND `指派维修人员工号` IS NULL AND `计划维修时间` IS NULL AND `拒绝原因` IS NULL) OR
        (`单据状态` IN ('维修中', '待验收', '已完成') AND `指派维修人员工号` IS NOT NULL AND `计划维修时间` IS NOT NULL AND `拒绝原因` IS NULL) OR
        (`单据状态` = '拒绝' AND `指派维修人员工号` IS NULL AND `计划维修时间` IS NULL AND `拒绝原因` IS NOT NULL AND CHAR_LENGTH(TRIM(`拒绝原因`)) > 0)
    )
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `执行维修` (
    `维修记录编号` VARCHAR(32) NOT NULL,
    `报修单ID` VARCHAR(32) NOT NULL,
    `维修人员工号` VARCHAR(32) NOT NULL,
    `维修内容` VARCHAR(1000) NOT NULL,
    `开始时间` DATETIME(6) NOT NULL,
    `完成时间` DATETIME(6) NULL,
    `维修费用` DECIMAL(12,2) NULL,
    `验收结果` VARCHAR(16) NULL,
    `验收人用户id` VARCHAR(32) NULL,
    `验收时间` DATETIME(6) NULL,
    CONSTRAINT `pk_maintenance_execution` PRIMARY KEY (`维修记录编号`),
    INDEX `ix_maintenance_execution_report` (`报修单ID`),
    INDEX `ix_maintenance_execution_worker` (`维修人员工号`),
    INDEX `ix_maintenance_execution_acceptor` (`验收人用户id`),
    CONSTRAINT `fk_maintenance_execution_report` FOREIGN KEY (`报修单ID`) REFERENCES `故障报修单` (`报修单ID`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_maintenance_execution_worker` FOREIGN KEY (`维修人员工号`) REFERENCES `维修人员` (`维修人员工号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_maintenance_execution_acceptor` FOREIGN KEY (`验收人用户id`) REFERENCES `用户` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_maintenance_execution_id` CHECK (CHAR_LENGTH(TRIM(`维修记录编号`)) > 0),
    CONSTRAINT `ck_maintenance_execution_content` CHECK (CHAR_LENGTH(TRIM(`维修内容`)) > 0),
    CONSTRAINT `ck_maintenance_execution_completion` CHECK (
        (`完成时间` IS NULL AND `维修费用` IS NULL) OR
        (`完成时间` IS NOT NULL AND `完成时间` >= `开始时间` AND `维修费用` IS NOT NULL AND `维修费用` >= 0)
    ),
    CONSTRAINT `ck_maintenance_execution_acceptance` CHECK (
        (`验收结果` IS NULL AND `验收人用户id` IS NULL AND `验收时间` IS NULL) OR
        (`验收结果` IN ('通过', '返修') AND `验收人用户id` IS NOT NULL AND `验收时间` IS NOT NULL AND `完成时间` IS NOT NULL AND `验收时间` >= `完成时间`)
    )
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `安全检查表` (
    `检查记录id` VARCHAR(32) NOT NULL,
    `实验室编号` VARCHAR(32) NOT NULL,
    `检查人用户id` VARCHAR(32) NOT NULL,
    `检查日期` DATE NOT NULL,
    `水电状态` VARCHAR(16) NOT NULL,
    `消防状态` VARCHAR(16) NOT NULL,
    `设备状态` VARCHAR(16) NOT NULL,
    `门窗状态` VARCHAR(16) NOT NULL,
    `隐患记录` VARCHAR(1000) NULL,
    `整改结果` VARCHAR(1000) NULL,
    CONSTRAINT `pk_safety_inspection` PRIMARY KEY (`检查记录id`),
    INDEX `ix_safety_inspection_laboratory` (`实验室编号`),
    INDEX `ix_safety_inspection_inspector` (`检查人用户id`),
    CONSTRAINT `fk_safety_inspection_laboratory` FOREIGN KEY (`实验室编号`) REFERENCES `实验室` (`实验室编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_safety_inspection_inspector` FOREIGN KEY (`检查人用户id`) REFERENCES `实验室负责人` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_safety_inspection_id` CHECK (CHAR_LENGTH(TRIM(`检查记录id`)) > 0),
    CONSTRAINT `ck_safety_inspection_states` CHECK (`水电状态` IN ('合格', '不合格') AND `消防状态` IN ('合格', '不合格') AND `设备状态` IN ('合格', '不合格') AND `门窗状态` IN ('合格', '不合格')),
    CONSTRAINT `ck_safety_inspection_findings` CHECK (
        (`水电状态` = '合格' AND `消防状态` = '合格' AND `设备状态` = '合格' AND `门窗状态` = '合格' AND `隐患记录` IS NULL AND `整改结果` IS NULL) OR
        ((`水电状态` = '不合格' OR `消防状态` = '不合格' OR `设备状态` = '不合格' OR `门窗状态` = '不合格') AND `隐患记录` IS NOT NULL AND CHAR_LENGTH(TRIM(`隐患记录`)) > 0 AND (`整改结果` IS NULL OR CHAR_LENGTH(TRIM(`整改结果`)) > 0))
    )
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `借用` (
    `借用记录编号` VARCHAR(32) NOT NULL,
    `经办负责人用户id` VARCHAR(32) NOT NULL,
    `借用人用户id` VARCHAR(32) NOT NULL,
    `设备编号` VARCHAR(32) NOT NULL,
    `借出时间` DATETIME(6) NOT NULL,
    `计划归还时间` DATETIME(6) NOT NULL,
    `实际归还时间` DATETIME(6) NULL,
    `损坏描述` VARCHAR(1000) NULL,
    `赔偿金额` DECIMAL(12,2) NULL,
    CONSTRAINT `pk_loan` PRIMARY KEY (`借用记录编号`),
    INDEX `ix_loan_manager` (`经办负责人用户id`),
    INDEX `ix_loan_borrower` (`借用人用户id`),
    INDEX `ix_loan_equipment` (`设备编号`),
    CONSTRAINT `fk_loan_manager` FOREIGN KEY (`经办负责人用户id`) REFERENCES `实验室负责人` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_loan_borrower` FOREIGN KEY (`借用人用户id`) REFERENCES `用户` (`用户id`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_loan_equipment` FOREIGN KEY (`设备编号`) REFERENCES `实验设备` (`设备编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_loan_id_nonblank` CHECK (CHAR_LENGTH(TRIM(`借用记录编号`)) > 0),
    CONSTRAINT `ck_loan_planned_return` CHECK (`计划归还时间` >= `借出时间`),
    CONSTRAINT `ck_loan_actual_return` CHECK (`实际归还时间` IS NULL OR `实际归还时间` >= `借出时间`),
    CONSTRAINT `ck_loan_damage` CHECK (`损坏描述` IS NULL OR CHAR_LENGTH(TRIM(`损坏描述`)) > 0),
    CONSTRAINT `ck_loan_compensation` CHECK (`赔偿金额` IS NULL OR `赔偿金额` >= 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;

CREATE TABLE `设备移库记录` (
    `移库记录编号` VARCHAR(32) NOT NULL,
    `设备编号` VARCHAR(32) NOT NULL,
    `原实验室编号` VARCHAR(32) NOT NULL,
    `目标实验室编号` VARCHAR(32) NOT NULL,
    `移动时间` DATETIME(6) NOT NULL,
    `移动原因` VARCHAR(1000) NOT NULL,
    CONSTRAINT `pk_equipment_transfer` PRIMARY KEY (`移库记录编号`),
    INDEX `ix_equipment_transfer_device` (`设备编号`),
    INDEX `ix_equipment_transfer_source` (`原实验室编号`),
    INDEX `ix_equipment_transfer_target` (`目标实验室编号`),
    CONSTRAINT `fk_equipment_transfer_device` FOREIGN KEY (`设备编号`) REFERENCES `实验设备` (`设备编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_equipment_transfer_source` FOREIGN KEY (`原实验室编号`) REFERENCES `实验室` (`实验室编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `fk_equipment_transfer_target` FOREIGN KEY (`目标实验室编号`) REFERENCES `实验室` (`实验室编号`) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT `ck_equipment_transfer_id` CHECK (CHAR_LENGTH(TRIM(`移库记录编号`)) > 0),
    CONSTRAINT `ck_equipment_transfer_distinct` CHECK (`原实验室编号` <> `目标实验室编号`),
    CONSTRAINT `ck_equipment_transfer_reason` CHECK (CHAR_LENGTH(TRIM(`移动原因`)) > 0)
) ENGINE=InnoDB DEFAULT CHARACTER SET=utf8mb4 COLLATE=utf8mb4_0900_as_cs;
