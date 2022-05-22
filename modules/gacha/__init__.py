# import random
# import itertools
# import os
# import json
# from PIL import Image, ImageDraw, ImageFont
#

# def create_image_for_genshin(five_list, four_list, five_cnt, four_cnt, m_id, fp, cnt):
#     img = Image.new("RGBA", (1000, 220), 'white')
#     # 绘画对象
#     draw = ImageDraw.Draw(img)
#     new_font = ImageFont.truetype('simkai.ttf', 20)
#     five_text, four_text = "", ""
#     for five in five_list:
#         five_text = five_text + five + ' '
#     for four in four_list:
#         four_text = four_text + four + ' '
#     draw.text((20, 20), "本次一共祈愿了" + str(cnt) + "次", fill='black', font=new_font)
#     draw.text((20, 40), "共抽取" + str(five_cnt) + "个五星\n为" + five_text, fill='black', font=new_font)
#     draw.text((20, 100), "共抽取" + str(four_cnt) + "个四星\n为" + four_text, fill='black', font=new_font)
#     draw.text((20, 160), "当前已祈愿" + str(fp) + "次未出五星\n距离下一次保底还有" + str(90 - fp) + "次祈愿", fill='black', font=new_font)
#     img.save('userData/Draw/' + str(m_id) + '.png')
#

# def random_character(character_list, up_list_five, up_list_four, is_up):
#     json_filename = "botData/draw_cards_Genshin.json"
#     if os.path.exists(json_filename):
#         with open(json_filename, 'r', encoding='UTF-8') as f_obj:
#             this_card_dict = json.load(f_obj)
#     draw_ans = []
#     for character_type in character_list:
#         card_list = this_card_dict[character_type]
#         ans = random.choice(card_list)
#         if character_type == '五':
#             if is_up == 1:
#                 ans = up_list_five[0]
#                 is_up = 0
#             else:
#                 up_ans = up_list_five[0]
#                 if random.randint(1, 100) > 50:
#                     ans = up_ans
#                 if ans != up_ans:
#                     is_up = 1
#         if character_type == '四角':
#             if is_up == 1:
#                 ans = random.choice(up_list_four)
#                 is_up = 0
#             else:
#                 up_ans = random.choice(up_list_four)
#                 if random.randint(1, 100) > 50:
#                     ans = up_ans
#                 if ans not in up_list_four:
#                     is_up = 1
#         draw_ans.append(ans)
#     return draw_ans, is_up
#
#


# def wish(
#         user_info,
#         user_id=12345678,
#         counts=1,
#         up_list_five=None,
#         up_list_four=None
# ):
#     choice_list = [6, 51, 943]
#     cha_count = [0, 0]
#     five_per = user_info['draw_proba_genshin'][0]
#     four_per = user_info['draw_proba_genshin'][1]
#     is_five_up = user_info['draw_proba_genshin'][2]
#     is_four_up = user_info['draw_proba_genshin'][3]
#     choice_list[0] = user_info['draw_proba_genshin'][4]
#     draw_ans_five = []
#     draw_ans_four = []
#     for i in range(1, counts + 1):
#         x = cls().random_picks('五四三', choice_list)
#         ans = ''.join(itertools.islice(x, 1))
#         if ans != '五':
#             five_per += 1
#             if five_per > 73:
#                 choice_list[0] += 53
#             if five_per >= 90:
#                 ans = "五"
#                 five_per = 0
#                 choice_list[0] = 6
#         else:
#             five_per = 0
#             choice_list[0] = 6
#         four_per += 1
#         if four_per == 10:
#             if ans != '五':
#                 x = cls().random_picks('五四', [6, 994])
#                 ans = ''.join(itertools.islice(x, 1))
#             four_per = 0
#         if ans == '五':
#             cha_count[0] += 1
#             draw_ans_five.append(ans)
#         if ans == '四':
#             ans = random.choice(["四角", "四武"])
#             cha_count[1] += 1
#             draw_ans_four.append(ans)
#     draw_ans_five, is_five_up = random_character(draw_ans_five, up_list_five, up_list_four, is_five_up)
#     draw_ans_four, is_four_up = random_character(draw_ans_four, up_list_five, up_list_four, is_four_up)
#     user_info['draw_proba_genshin'] = [five_per, four_per, is_five_up, is_four_up, choice_list[0]]
#     create_image_for_genshin(draw_ans_five, draw_ans_four, cha_count[0], cha_count[1], user_id, five_per, counts)
