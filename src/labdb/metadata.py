"""Independent structural contract for the modern schema."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnSpec:
    column_type: str
    nullable: bool = False


@dataclass(frozen=True)
class ForeignKeySpec:
    name: str
    child_table: str
    child_columns: tuple[str, ...]
    parent_table: str
    parent_columns: tuple[str, ...]
    update_rule: str = "RESTRICT"
    delete_rule: str = "RESTRICT"


def c(column_type: str, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(column_type, nullable)


EXPECTED_COLUMNS: dict[str, dict[str, ColumnSpec]] = {
    "学院": {"学院编号": c("varchar(32)"), "学院名称": c("varchar(100)")},
    "用户": {"用户id": c("varchar(32)"), "姓名": c("varchar(100)"), "用户状态": c("varchar(16)")},
    "学生": {"用户id": c("varchar(32)"), "学院编号": c("varchar(32)")},
    "教师": {"用户id": c("varchar(32)"), "学院编号": c("varchar(32)")},
    "实验室负责人": {"用户id": c("varchar(32)")},
    "实验室": {
        "实验室编号": c("varchar(32)"), "学院编号": c("varchar(32)"),
        "负责人用户id": c("varchar(32)"), "实验室名称": c("varchar(100)"),
        "容纳人数": c("int"), "使用状态": c("varchar(16)"),
        "实验室照片": c("varchar(512)", True),
    },
    "设备类别": {"类别码": c("varchar(32)"), "类别名称": c("varchar(100)")},
    "供应商": {
        "供应商编号": c("varchar(32)"), "供应商名称": c("varchar(100)"),
        "电话": c("varchar(30)", True),
    },
    "实验设备": {
        "设备编号": c("varchar(32)"), "类别码": c("varchar(32)"),
        "供应商编号": c("varchar(32)"), "实验室编号": c("varchar(32)"),
        "型号": c("varchar(100)"), "规格": c("varchar(100)"),
        "购置日期": c("date"), "单价": c("decimal(12,2)"),
        "保修到期日": c("date"), "设备状态": c("varchar(16)"),
    },
    "维修人员": {
        "维修人员工号": c("varchar(32)"), "姓名": c("varchar(100)"),
        "电话": c("varchar(30)"),
    },
    "学期": {
        "学期编号": c("varchar(32)"), "学期名称": c("varchar(100)"),
        "开始时间": c("datetime(6)"), "结束时间": c("datetime(6)"),
        "初始积分": c("int"),
    },
    "课程": {
        "课程编号": c("varchar(32)"), "授课教师用户id": c("varchar(32)"),
        "课程名称": c("varchar(100)"),
    },
    "预约表": {
        "预约表单号": c("varchar(32)"), "实验室编号": c("varchar(32)"),
        "用户id": c("varchar(32)"), "学期编号": c("varchar(32)"),
        "课程编号": c("varchar(32)", True), "审核人用户id": c("varchar(32)", True),
        "预约类型": c("varchar(16)"), "开始时间": c("datetime(6)"),
        "结束时间": c("datetime(6)"), "人数": c("int"),
        "用途": c("varchar(100)"), "预约状态": c("varchar(16)"),
        "驳回原因": c("varchar(1000)", True),
    },
    "签到记录": {
        "签到记录id": c("varchar(32)"), "预约表单号": c("varchar(32)"),
        "签到方式": c("varchar(16)"), "签到时间": c("datetime(6)"),
        "签退时间": c("datetime(6)", True), "超时备注": c("varchar(1000)", True),
    },
    "违规记录": {
        "违规id": c("varchar(32)"), "预约表单号": c("varchar(32)"),
        "签到记录id": c("varchar(32)", True), "违规类型": c("varchar(16)"),
        "扣分值": c("int"), "违规时间": c("datetime(6)"),
    },
    "预约设备": {
        "使用记录编号": c("varchar(32)"), "预约表单号": c("varchar(32)"),
        "设备编号": c("varchar(32)"),
    },
    "预约变更": {
        "变更记录编号": c("varchar(32)"), "预约表单号": c("varchar(32)"),
        "操作人用户id": c("varchar(32)"), "变更类型": c("varchar(16)"),
        "变更原因": c("varchar(1000)"), "变更时间": c("datetime(6)"),
    },
    "故障报修单": {
        "报修单ID": c("varchar(32)"), "设备编号": c("varchar(32)"),
        "报修人用户id": c("varchar(32)"), "责任负责人用户id": c("varchar(32)"),
        "指派维修人员工号": c("varchar(32)", True), "故障描述": c("varchar(1000)"),
        "故障图片": c("varchar(512)", True), "紧急程度": c("varchar(16)"),
        "单据状态": c("varchar(16)"), "报修时间": c("datetime(6)"),
        "计划维修时间": c("datetime(6)", True), "拒绝原因": c("varchar(1000)", True),
    },
    "执行维修": {
        "维修记录编号": c("varchar(32)"), "报修单ID": c("varchar(32)"),
        "维修人员工号": c("varchar(32)"), "维修内容": c("varchar(1000)"),
        "开始时间": c("datetime(6)"), "完成时间": c("datetime(6)", True),
        "维修费用": c("decimal(12,2)", True), "验收结果": c("varchar(16)", True),
        "验收人用户id": c("varchar(32)", True), "验收时间": c("datetime(6)", True),
    },
    "安全检查表": {
        "检查记录id": c("varchar(32)"), "实验室编号": c("varchar(32)"),
        "检查人用户id": c("varchar(32)"), "检查日期": c("date"),
        "水电状态": c("varchar(16)"), "消防状态": c("varchar(16)"),
        "设备状态": c("varchar(16)"), "门窗状态": c("varchar(16)"),
        "隐患记录": c("varchar(1000)", True), "整改结果": c("varchar(1000)", True),
    },
    "借用": {
        "借用记录编号": c("varchar(32)"), "经办负责人用户id": c("varchar(32)"),
        "借用人用户id": c("varchar(32)"), "设备编号": c("varchar(32)"),
        "借出时间": c("datetime(6)"), "计划归还时间": c("datetime(6)"),
        "实际归还时间": c("datetime(6)", True), "损坏描述": c("varchar(1000)", True),
        "赔偿金额": c("decimal(12,2)", True),
    },
    "设备移库记录": {
        "移库记录编号": c("varchar(32)"), "设备编号": c("varchar(32)"),
        "原实验室编号": c("varchar(32)"), "目标实验室编号": c("varchar(32)"),
        "移动时间": c("datetime(6)"), "移动原因": c("varchar(1000)"),
    },
}

EXPECTED_PRIMARY_KEYS = {table: (next(iter(columns)),) for table, columns in EXPECTED_COLUMNS.items()}

EXPECTED_UNIQUES: dict[str, tuple[str, tuple[str, ...]]] = {
    "uq_checkin_reservation": ("签到记录", ("预约表单号",)),
    "uq_checkin_reservation_id": ("签到记录", ("预约表单号", "签到记录id")),
    "uq_violation_reservation_type": ("违规记录", ("预约表单号", "违规类型")),
    "uq_reservation_equipment_pair": ("预约设备", ("预约表单号", "设备编号")),
}


def fk(name: str, child: str, child_columns: str | tuple[str, ...], parent: str, parent_columns: str | tuple[str, ...]) -> ForeignKeySpec:
    if isinstance(child_columns, str):
        child_columns = (child_columns,)
    if isinstance(parent_columns, str):
        parent_columns = (parent_columns,)
    return ForeignKeySpec(name, child, child_columns, parent, parent_columns)


EXPECTED_FOREIGN_KEYS = (
    fk("fk_student_user", "学生", "用户id", "用户", "用户id"),
    fk("fk_student_college", "学生", "学院编号", "学院", "学院编号"),
    fk("fk_teacher_user", "教师", "用户id", "用户", "用户id"),
    fk("fk_teacher_college", "教师", "学院编号", "学院", "学院编号"),
    fk("fk_manager_teacher", "实验室负责人", "用户id", "教师", "用户id"),
    fk("fk_laboratory_college", "实验室", "学院编号", "学院", "学院编号"),
    fk("fk_laboratory_manager", "实验室", "负责人用户id", "实验室负责人", "用户id"),
    fk("fk_equipment_category", "实验设备", "类别码", "设备类别", "类别码"),
    fk("fk_equipment_supplier", "实验设备", "供应商编号", "供应商", "供应商编号"),
    fk("fk_equipment_laboratory", "实验设备", "实验室编号", "实验室", "实验室编号"),
    fk("fk_course_teacher", "课程", "授课教师用户id", "教师", "用户id"),
    fk("fk_reservation_laboratory", "预约表", "实验室编号", "实验室", "实验室编号"),
    fk("fk_reservation_user", "预约表", "用户id", "用户", "用户id"),
    fk("fk_reservation_term", "预约表", "学期编号", "学期", "学期编号"),
    fk("fk_reservation_course", "预约表", "课程编号", "课程", "课程编号"),
    fk("fk_reservation_reviewer", "预约表", "审核人用户id", "实验室负责人", "用户id"),
    fk("fk_checkin_reservation", "签到记录", "预约表单号", "预约表", "预约表单号"),
    fk("fk_violation_reservation", "违规记录", "预约表单号", "预约表", "预约表单号"),
    fk("fk_violation_checkin", "违规记录", ("预约表单号", "签到记录id"), "签到记录", ("预约表单号", "签到记录id")),
    fk("fk_reservation_equipment_reservation", "预约设备", "预约表单号", "预约表", "预约表单号"),
    fk("fk_reservation_equipment_device", "预约设备", "设备编号", "实验设备", "设备编号"),
    fk("fk_reservation_change_reservation", "预约变更", "预约表单号", "预约表", "预约表单号"),
    fk("fk_reservation_change_actor", "预约变更", "操作人用户id", "用户", "用户id"),
    fk("fk_fault_report_equipment", "故障报修单", "设备编号", "实验设备", "设备编号"),
    fk("fk_fault_report_reporter", "故障报修单", "报修人用户id", "用户", "用户id"),
    fk("fk_fault_report_manager", "故障报修单", "责任负责人用户id", "实验室负责人", "用户id"),
    fk("fk_fault_report_assignee", "故障报修单", "指派维修人员工号", "维修人员", "维修人员工号"),
    fk("fk_maintenance_execution_report", "执行维修", "报修单ID", "故障报修单", "报修单ID"),
    fk("fk_maintenance_execution_worker", "执行维修", "维修人员工号", "维修人员", "维修人员工号"),
    fk("fk_maintenance_execution_acceptor", "执行维修", "验收人用户id", "用户", "用户id"),
    fk("fk_safety_inspection_laboratory", "安全检查表", "实验室编号", "实验室", "实验室编号"),
    fk("fk_safety_inspection_inspector", "安全检查表", "检查人用户id", "实验室负责人", "用户id"),
    fk("fk_loan_borrower", "借用", "借用人用户id", "用户", "用户id"),
    fk("fk_loan_equipment", "借用", "设备编号", "实验设备", "设备编号"),
    fk("fk_loan_manager", "借用", "经办负责人用户id", "实验室负责人", "用户id"),
    fk("fk_equipment_transfer_device", "设备移库记录", "设备编号", "实验设备", "设备编号"),
    fk("fk_equipment_transfer_source", "设备移库记录", "原实验室编号", "实验室", "实验室编号"),
    fk("fk_equipment_transfer_target", "设备移库记录", "目标实验室编号", "实验室", "实验室编号"),
)

EXPECTED_CHECKS = {
    "ck_college_id_nonblank", "ck_college_name_nonblank",
    "ck_user_id_nonblank", "ck_user_name_nonblank", "ck_user_status",
    "ck_laboratory_id_nonblank", "ck_laboratory_name_nonblank", "ck_laboratory_capacity", "ck_laboratory_status", "ck_laboratory_photo",
    "ck_equipment_category_id", "ck_equipment_category_name",
    "ck_supplier_id_nonblank", "ck_supplier_name_nonblank", "ck_supplier_phone",
    "ck_equipment_id_nonblank", "ck_equipment_model_nonblank", "ck_equipment_spec_nonblank", "ck_equipment_price", "ck_equipment_warranty", "ck_equipment_status",
    "ck_worker_id_nonblank", "ck_worker_name_nonblank", "ck_worker_phone_nonblank",
    "ck_term_id_nonblank", "ck_term_name_nonblank", "ck_term_period", "ck_term_initial_points",
    "ck_course_id_nonblank", "ck_course_name_nonblank",
    "ck_reservation_id_nonblank", "ck_reservation_kind_course", "ck_reservation_period", "ck_reservation_people", "ck_reservation_purpose", "ck_reservation_state",
    "ck_checkin_id_nonblank", "ck_checkin_method", "ck_checkin_signout", "ck_checkin_note",
    "ck_violation_id_nonblank", "ck_violation_type_score", "ck_violation_checkin_presence",
    "ck_reservation_equipment_id",
    "ck_reservation_change_id", "ck_reservation_change_type", "ck_reservation_change_reason",
    "ck_fault_report_id", "ck_fault_report_description", "ck_fault_report_image", "ck_fault_report_urgency", "ck_fault_report_schedule", "ck_fault_report_state",
    "ck_maintenance_execution_id", "ck_maintenance_execution_content", "ck_maintenance_execution_completion", "ck_maintenance_execution_acceptance",
    "ck_safety_inspection_id", "ck_safety_inspection_states", "ck_safety_inspection_findings",
    "ck_loan_id_nonblank", "ck_loan_planned_return", "ck_loan_actual_return", "ck_loan_damage", "ck_loan_compensation",
    "ck_equipment_transfer_id", "ck_equipment_transfer_distinct", "ck_equipment_transfer_reason",
}

EXPECTED_TABLES = frozenset(EXPECTED_COLUMNS)
EXPECTED_COLLATION = "utf8mb4_0900_as_cs"
EXPECTED_ENGINE = "InnoDB"
