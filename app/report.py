from unwind import get_report, ReportFlag
from pprint import pformat
from typing import List, Iterable
from ujson import dumps
from pydantic import BaseModel


def save_iterable(data: Iterable):
    for i in data:
        if isinstance(i, BaseModel):
            yield i.json(ensure_ascii=False, indent=2)
        elif isinstance(i, dict):
            yield dict(save_dict(i))
        elif isinstance(i, (str, int, float, bool, type(None))):
            yield i
        elif isinstance(i, Iterable):
            yield list(save_iterable(i))
        else:
            yield str(i)


def save_dict(data: dict):
    for k, v in data.items():
        if isinstance(v, BaseModel):
            yield str(k), v.json(ensure_ascii=False, indent=2)
        elif isinstance(v,  (str, int, float, bool, type(None))):
            yield str(k), v
        elif isinstance(v, dict):
            yield str(k), dict(save_dict(v))
        elif isinstance(v, Iterable):
            yield str(k), list(save_iterable(v))
        else:
            yield str(k), str(v)


def reports_md(exception: BaseException) -> str:
    strings = [f"## 报错: \n- 异常类型: {exception.__class__.__name__}\n- 异常内容: {exception}", "## 异常追踪\n"]
    for index, report in enumerate(get_report(exception)):
        context = []
        for line in report.info.codes:
            if line.strip():
                context.append("\n  " + line.replace("    ", "\t").replace("\t", "│   "))
            elif context:
                context.append("\n  " + "│   " * context[-1].count("│"))

        context = "".join(context) + "\n"
        file = report.info.file.replace("\\", "/")
        if report.flag == ReportFlag.ACTIVE:
            strings.append(
                f"### Report [{index}]\n"
                f"- 错误类型: {report.type}\n"
                f"- 错误内容: {report.content}\n"
                f"- 报错代码: {report.info.code_line}\n"
                f"- 上下文:\n"
                f"```python\n"
                f"{file}: {report.info.line_index} in {report.info.name}"
                f"{context}\n"
                f"```"
            )
        else:
            strings.append(
                f"### Report [{index}]\n"
                f"- 报错代码: {report.info.code_line}\n"
                f"- 上下文:\n"
                f"```python\n"
                f"{file}: {report.info.line_index} in {report.info.name}"
                f"{context}\n"
                f"```\n"
                f"- 参数:\n"
                f"```json\n"
                f"{dumps(dict(save_dict(report.args)), ensure_ascii=False, indent=2)}\n"
                f"```"
            )
    return "\n".join(strings)


def generate_reports(exception: BaseException) -> List[str]:
    strings = [f"报错: {exception.__class__.__name__} \n{pformat(exception, indent=2)}"]
    for index, report in enumerate(get_report(exception)):
        if report.flag == ReportFlag.ACTIVE:
            strings.append(
                f"----------report[{index}]----------\n"
                f"原因: 主动抛出异常 {report.flag}\n"
                f"位置: {report.info.name}, line {report.info.line_index}, in {report.info.file}\n"
                f"代码: {report.info.code_line}\n"
                f"错误类型: {report.type}\n"
                f"错误内容: {report.content}\n"
            )
        elif report.flag in (ReportFlag.OPERATE, ReportFlag.UNKNOWN):
            strings.append(
                f"----------report[{index}]----------\n"
                f"原因: 操作出错 {report.flag}\n"
                f"位置: {report.info.name}, line {report.info.line_index}, in {report.info.file}\n"
                f"代码: {report.info.code_line}\n"
                f"参数: {pformat(report.args)}\n"
            )
        else:
            strings.append(
                f"----------report[{index}]----------\n"
                f"原因: 执行代码 {report.flag}\n"
                f"位置: {report.info.name}, line {report.info.line_index}, in {report.info.file}\n"
                f"代码: {report.info.code_line}\n"
                f"执行对象: {report.callable}\n"
                f"参数: {pformat(report.args)}\n"
            )
    return strings
