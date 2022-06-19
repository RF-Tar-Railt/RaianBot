import random
from typing import List
from enum import IntEnum

Value_Err = ValueError("Input a wrong number")
Input_Err = ValueError("Input a wrong pattern")

ZeroDice_Err = ValueError("Can't input zero in dice")
ZeroType_Err = ValueError("Can't input zero in type")
DiceTooBig_Err = ValueError("Too big for dice")
TypeTooBig_Err = ValueError("Too big for type")
AddDiceVal_Err = ValueError("Input a wrong A number")
# Dice Type


class DiceType(IntEnum):
    Normal_Dice = 0
    B_Dice = 1
    P_Dice = 2
    Fudge_Dice = 3
    WW_Dice = 4


class RD:
    ww_count: int
    ww_add_value: int

    pattern: str
    result_record_matrix: List[List[int]]
    result_record: List[int]
    negative_record: List[bool]
    multiplier_record: List[int]
    divider_record: List[int]

    bnp_record: List[int]
    total: int

    def __init__(self, pattern: str, default_dice: int = 100):
        self.ww_count = 0
        self.ww_add_value = 10
        self.total = 0
        self.result_record_matrix = []
        self.result_record = []
        self.negative_record = []
        self.multiplier_record = []
        self.divider_record = []
        self.bnp_record = []

        _dice = ""
        cache = ''
        _opera = "+-X/"
        for c in pattern:
            if c in {"*", "x", "X"}:
                if cache in _opera:
                    _dice = _dice[:-1]
                    break
                c = 'X'
            if c == '/' and cache in _opera:
                _dice = _dice[:-1]
                break
            if c == '+' and cache in _opera:
                continue
            if c == '-':
                if cache in _opera:
                    if cache in {'+', '-'}:
                        _dice = _dice[:-1] + {'+': '-', '-': '+'}[cache]
                    elif cache in {'X', '/'}:
                        _dice = _dice[:-1]
                        break
                    continue
            elif c in {'a', 'A'}:
                c = c.lower()
            else:
                c = c.upper()
            cache = c
            _dice += c
        if not _dice:
            _dice += f"D{default_dice}"
        if _dice[0] == 'a':
            _dice = '1' + _dice
        if _dice[0] == 'D' and _dice[1] == 'F':
            _dice = '4' + _dice
        if _dice[0] == 'F':
            _dice = '4D' + _dice
        _dice = _dice.replace('XX', 'X', 2).replace('//', '/', 2)
        # -------
        #  一大堆处理...
        # -------
        if _dice.endswith('D'):
            _dice += f'{default_dice}'
        if _dice.endswith('K'):
            _dice += '1'
        if _dice.startswith('+'):
            _dice = _dice[1:]
        if _dice.isdigit():
            _dice = f'{_dice}D{default_dice}'
        self.pattern = _dice

    def roll(self):
        """
        运行一次掷骰, 不会捕捉报错
        """
        self.total = 0
        self.result_record_matrix.clear()
        self.negative_record.clear()
        self.multiplier_record.clear()
        self.result_record.clear()
        self.bnp_record.clear()
        dice = self.pattern
        int_read_dice_loc = 0
        if dice.startswith('-'):
            self.negative_record.append(True)
            int_read_dice_loc = 1
        else:
            self.negative_record.append(False)
        if dice.endswith(('+', '-', 'X', '/')):
            raise Input_Err
        while (
                (pos_add := dice.find('+', int_read_dice_loc)) > -1
                or (pos_sub := dice.find('-', int_read_dice_loc)) > -1
        ):
            int_symbol_position = min(pos_add, pos_sub)
            self._roll_dice(dice[int_read_dice_loc:int_symbol_position - int_read_dice_loc])
            int_read_dice_loc = int_symbol_position + 1
            if dice[int_symbol_position:int_read_dice_loc] == '+':
                self.negative_record.append(False)
            else:
                self.negative_record.append(True)
        self._roll_dice(dice[int_read_dice_loc:])
        if self.ww_count:
            self._roll_ww()
        return self

    def _roll_ww(self):
        _result_record = []
        _result = 0
        _negative = False
        if self.ww_count < 0:
            _negative = True
            self.ww_count = -self.ww_count
        while self.ww_count != 0:
            _result_record.append(self.ww_count)
            add_num = 0
            int_cnt = self.ww_count
            while int_cnt > 0:
                int_cnt -= 1
                result_once = random.randint(1, 10)
                _result_record.append(result_once)
                if result_once >= 8:
                    _result += 1
                if result_once >= self.ww_add_value:
                    add_num += 1
            if self.ww_count > 10:
                _result_record = _result_record[:-self.ww_count] + sorted(_result_record[-self.ww_count:])
            self.ww_count = add_num
        self.total += (-_result) if _negative else _result
        self.bnp_record.insert(0, DiceType.WW_Dice)
        self.negative_record.insert(0, _negative)
        self.result_record_matrix.insert(0, _result_record)
        self.result_record.insert(0, _result)
        self.multiplier_record.insert(0, 1)
        self.divider_record.insert(0, 1)
        return

    def _roll_dice(self, pattern: str):
        _negative = self.negative_record[-1]

        _divider = 1
        while (op_position := ''.join(reversed(pattern)).find('/')) > -1:
            _rate = pattern[op_position + 1:]
            rate = RD(_rate)
            try:
                rate.roll()
            except ValueError as e:
                raise Input_Err from e
            else:
                if not rate.total:
                    raise Input_Err
                _divider *= rate.total
            pattern = pattern[:op_position]
        _multiplier = 1
        while (op_position := ''.join(reversed(pattern)).find('X')) > -1:
            _rate = pattern[op_position + 1:]
            rate = RD(_rate)
            try:
                rate.roll()
                _multiplier *= rate.total
            except ValueError as e:
                raise Input_Err from e
            pattern = pattern[:op_position]
        self.divider_record.append(_divider)
        self.multiplier_record.append(_multiplier)
        if (pos_a := pattern.find('a')) > -1:
            _dice_cnt = pattern[:pos_a]
            if not _dice_cnt.isdigit():
                raise Input_Err
            if len(_dice_cnt) > 3:
                raise DiceTooBig_Err
            dice_cnt = int(_dice_cnt)
            if not dice_cnt:
                raise ZeroDice_Err
            if _negative:
                dice_cnt = (-dice_cnt)
            self.ww_count += dice_cnt
            _add_value = pattern[pos_a + 1:]
            if len(_add_value) > 2:
                raise AddDiceVal_Err
            if not _add_value.isdigit():
                raise Input_Err
            if _add_value:
                self.ww_add_value = int(_add_value)
                if self.ww_add_value < 5 or self.ww_add_value > 11:
                    raise AddDiceVal_Err
            self.negative_record.pop()
            return
        if pattern.endswith('F'):
            self.bnp_record.append(DiceType.Fudge_Dice)
            if pattern.endswith('DF'):
                _dice_num = pattern[:-2]
            else:
                _dice_num = pattern[:-1]
            if not _dice_num.isdigit():
                raise Value_Err
            if len(_dice_num) > 2:
                raise DiceTooBig_Err
            dice_num = int(_dice_num)
            if not dice_num:
                raise ZeroDice_Err
            temp_record = []
            while dice_num > 0:
                dice_num -= 1
                _sum = random.randint(0, 2) - 1
                temp_record.append(_sum)
            self.result_record_matrix.append(temp_record)
            self.result_record.append(sums := sum(temp_record))
            self.total += (-sums) if _negative else sums
            return
        # P
        # B
        self.bnp_record.append(DiceType.Normal_Dice)
        if pattern.startswith('X'):
            raise Input_Err
        exist_d = False
        exist_k = False
        for c in filter(lambda x: not x.isdigit(), pattern.upper()):
            if c == 'D':
                if exist_d:
                    raise Input_Err
                exist_d = True
            elif c == 'K':
                if (not exist_d) or exist_k:
                    raise Input_Err
                exist_k = True
            else:
                raise Input_Err
        if not exist_d:
            if len(pattern) > 5 or not pattern:
                raise Value_Err
            _res = int(pattern)
            res = _res * _multiplier // _divider
            self.total += (-res) if _negative else res
            self.result_record.append(res)
            self.result_record_matrix.append([_res])
            return
        if not exist_k:
            _dice_cnt = pattern[:pattern.find('D')]
            _dice_type = pattern[pattern.find('D') + 1:]
            if len(_dice_cnt) > 3 or (len(_dice_cnt) == 3 and _dice_cnt != '100'):
                raise DiceTooBig_Err
            if len(_dice_type) > 4 or (len(_dice_type) == 3 and _dice_type != '100'):
                raise TypeTooBig_Err
            dice_cnt = 1 if len(_dice_cnt) == 0 else int(_dice_cnt)
            dice_type = int(_dice_type)
            if not dice_cnt:
                raise ZeroDice_Err
            if not dice_type:
                raise ZeroType_Err
            temp_record = []
            _res = 0
            while dice_cnt > 0:
                dice_cnt -= 1
                res_once = random.randint(1, dice_type)
                temp_record.append(res_once)
                _res += res_once
            res = _res * _multiplier // _divider
            self.total += (-res) if _negative else res
            if len(temp_record) > 20:
                temp_record.sort()
            self.result_record_matrix.append(temp_record)
            self.result_record.append(res)
            return
        _k_num = pattern[pattern.find('K') + 1:]
        if len(_k_num) > 3:
            raise Value_Err
        k_num = int(_k_num)
        _dice_cnt = pattern[:pattern.find('K')][:pattern.find('D')]
        _dice_type = pattern[:pattern.find('K')][pattern.find('D') + 1:]
        if len(_dice_cnt) > 3 or (len(_dice_cnt) == 3 and _dice_cnt != '100'):
            raise DiceTooBig_Err
        if len(_dice_type) > 4:
            raise TypeTooBig_Err
        dice_cnt = 1 if len(_dice_cnt) == 0 else int(_dice_cnt)
        dice_type = int(_dice_type)
        if k_num <= 0 or dice_cnt == 0:
            raise ZeroDice_Err
        if k_num > dice_cnt:
            raise Value_Err
        if dice_type == 0:
            raise ZeroType_Err
        temp_record = []
        while dice_cnt > 0:
            dice_cnt -= 1
            res_once = random.randint(1, dice_type)
            if len(temp_record) != int(k_num):
                temp_record.append(res_once)
            elif res_once > min(*temp_record):
                temp_record[temp_record.index(min(*temp_record))] = res_once
        _res = sum(temp_record)
        res = _res * _multiplier // _divider
        self.total += (-res) if _negative else res
        self.result_record.append(_res)
        if len(temp_record) > 20:
            temp_record.sort()
        self.result_record_matrix.append(temp_record)
        return


if __name__ == '__main__':
    rd = RD("5d20")
    print(rd.pattern)
    rd.roll()
    print(rd.total)
    print(rd.result_record)
    print(rd.result_record_matrix)
