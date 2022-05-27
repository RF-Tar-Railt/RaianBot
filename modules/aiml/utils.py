# -*- coding: utf-8 -*-
"""该文件包含PyAIML包中其他模块使用的各种通用实用函数。    """

from .lang_support import split_chinese


def sentences_split(s: str):
    """将一堆字符串切分成一个句子列表。"""
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    pos = 0
    sentence_list = []
    length = len(s)
    while pos < length:
        try:
            p = s.index('.', pos)
        except:
            p = length + 1
        try:
            q = s.index('?', pos)
        except:
            q = length + 1
        try:
            e = s.index('!', pos)
        except:
            e = length + 1
        end = min(p, q, e)
        sentence_list.append(s[pos:end].strip())
        pos = end + 1
    # 如果没有找到句子，则返回一个包含整个输入字符串的单条目列表。
    if len(sentence_list) == 0:
        sentence_list.append(s)
        # 自动转换中文！
    return map(lambda x: u' '.join(split_chinese(x)), sentence_list)
