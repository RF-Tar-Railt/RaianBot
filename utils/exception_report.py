from graiax.mod.unwind import get_report, ReportFlag
from typing import List


def generate_reports(exception: BaseException) -> List[str]:
    strings = [f"报错: {exception.__class__.__name__} {exception}"]
    for index, report in enumerate(get_report(exception)):
        if report.flag == ReportFlag.ACTIVE:
            strings.append(
                f"----------report[{index}]----------\n"
                f"原因: 主动抛出异常 {report.flag}\n"
                f"位置: {report.info.file}, line {report.info.line}, in {report.info.name}\n"
                f"代码: {report.info.code}\n"
                f"错误类型: {report.type}\n"
            )
        elif report.flag in (ReportFlag.OPERATE, ReportFlag.UNKNOWN):
            strings.append(
                f"----------report[{index}]----------\n"
                f"原因: 操作出错 {report.flag}\n"
                f"位置: {report.info.file}, line {report.info.line}, in {report.info.name}\n"
                f"代码: {report.info.code}\n"
                f"参数: {report.args}\n"
            )
        else:
            strings.append(
                f"----------report[{index}]----------\n"
                f"原因: 执行代码 {report.flag}\n"
                f"位置: {report.info.file}, line {report.info.line}, in {report.info.name}\n"
                f"代码: {report.info.code}\n"
                f"执行对象: {report.callable}\n"
                f"参数: {report.args}\n"
            )
    return strings
