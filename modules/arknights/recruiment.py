from typing import List

professor_1 = {'先锋': 32, '近卫': 16, '狙击': 8, '重装': 4, '医疗': 2, '辅助': 1}
professor_2 = {'术师': 32, '特种': 16}
position_3 = {'近战位': 8, '远程位': 4}
exp_4 = {'新手': 16, '资深干员': 8, '高级资深干员': 4, '高资': 4}

others_5 = {'治疗': 4, '支援': 2, '输出': 1}
others_6 = {'群攻': 32, '减速': 16, '生存': 8, '防护': 4, '削弱': 2, '位移': 1}
others_7 = {'控制': 32, '控场': 32, '爆发': 16, '召唤': 8, '快速复活': 4, '费用回复': 2, '支援机械': 1}

alphabet = {
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10, 'L': 11, 'M': 12,
    'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19, 'U': 20, 'V': 21, "W": 22, 'X': 23, 'Y': 24,
    'Z': 25, 'a': 26, 'b': 27, 'c': 28, 'd': 29, 'e': 30, 'f': 31, 'g': 32, 'h': 33, 'i': 34, 'j': 35, 'k': 36,
    'l': 37, 'm': 38, 'n': 39, 'o': 40, 'p': 41, 'q': 42, 'r': 43, 's': 44, 't': 45, 'u': 46, 'v': 47, 'w': 48,
    'x': 49, 'y': 50, 'z': 51, '0': 52, '1': 53, '2': 54, '3': 55, '4': 56, '5': 57, '6': 58, '7': 59, '8': 60,
    '9': 61, '+': 62, ',': 63
}

base_url = 'https://prts.wiki/w/CHAR?filter='
base_str = 'FQAAAAAAAAAAAAAAAAAAAAAAA'


def recruitment(tags: List[str]):
    add_str = [0, 0, 0, 2, 0, 0, 0]
    for val in tags:
        if val in professor_1:
            add_str[0] += professor_1[val]
        if val in professor_2:
            add_str[1] += professor_2[val]
        if val in position_3:
            add_str[2] += position_3[val]
        if val in exp_4:
            add_str[3] += exp_4[val]
        if val in others_5:
            add_str[4] += others_5[val]
        if val in others_6:
            add_str[5] += others_6[val]
        if val in others_7:
            add_str[6] += others_7[val]

    for word in alphabet:
        for i in range(0, 7):
            if alphabet[word] == add_str[i]:
                add_str[i] = word
    return base_url + "".join(add_str) + base_str


if __name__ == '__main__':
    print(recruitment(["高资", "支援", "近卫"]))
