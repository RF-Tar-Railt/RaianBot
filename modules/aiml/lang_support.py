# -*- coding: utf-8 -*-

def is_chinese(c):
    """中文Unicode码范围参考：https://www.iteye.com/topic/558050     """
# 一，二，三9
# 123456789
    r = [
        # 标准CJK文字
        (0x3400, 0x4DB5), (0x4E00, 0x9FA5), (0x9FA6, 0x9FBB), (0xF900, 0xFA2D),
        (0xFA30, 0xFA6A), (0xFA70, 0xFAD9), (0x20000, 0x2A6D6), (0x2F800, 0x2FA1D),
        # 全角ASCII、全角中英文标点、半宽片假名、半宽平假名、半宽韩文字母
        (0xFF00, 0xFFEF),
        # CJK部首补充
        (0x2E80, 0x2EFF),
        # CJK标点符号
        (0x3000, 0x303F),
        # CJK笔划
        (0x31C0, 0x31EF)]
    return any(s <= ord(c) <= e for s, e in r)


def is_include_chinese(s: str):
    for c in s:
        if is_chinese(c):
            return True
    return False


def split_chinese(s):
    result = []
    for c in s:
        if is_chinese(c):
            result.extend([" ", c, " "])
        else:
            result.append(c)
    ret = ''.join(result)
    return ret.split()  # 字符串默认的分割就是按空格分词，返回list
