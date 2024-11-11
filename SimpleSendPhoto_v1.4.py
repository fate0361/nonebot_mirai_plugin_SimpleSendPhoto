"""
SimpleSendPhoto_v1.4
----------------------------
1、添加配置文件，防止变成难以修改的史山——v1.2
2、添加发图权重，使新图发送概率更高——v1.3
3、优化获取图片后存入dict的方式（仅保存名字，不存路径），防止图片太多写爆字典——v1.3
4、修复了因v1.3添加权重改变了字典储存形式而使得检查空字典重新获取方法失效的bug——v1.4
5、每日定点保存成json文档，以防止每次重启更新dict——v1.4
"""
from nonebot.adapters.mirai2 import Bot, MessageSegment
from nonebot.adapters.mirai2.event import GroupMessage, MessageEvent
from nonebot.matcher import Matcher
from nonebot import on_regex
from nonebot.params import RegexStr
from nonebot.plugin import PluginMetadata
from nonebot.log import logger
from typing import Annotated
import os
from os.path import getmtime
import random
import json
import threading
from datetime import datetime, time
import time as t


"""
todo
-------------------
1、配置文件分开写
2、await群友命令添加图库及图片
3、添加图库关键词列表
"""

__plugin_meta__ = PluginMetadata(
    name="来点库存",
    description="随机发送库存图片",
    usage="[来点xx] 抽取指定库存的图片",
    type="application",
    homepage="还没有上传github哦",
    config="还没分离开来写哦",
    extra={
        "author": "saya <785497966@qq.com>",
        "version": "SimpleSendPhoto_v1.1",
    },
)

# 配置文件1，填写对应关键词及对应图片路径
pic_pathway_dict = {
    "key": '/home/fate0361/mirai/image/key/',
    "库存": '/home/fate0361/mirai/image/R0/',
    "库特": '/home/fate0361/mirai/image/kudwafter/',
    "cl": '/home/fate0361/mirai/image/clannad/',
    "naga": '/home/fate0361/mirai/image/naga/',
    "saya": '/home/fate0361/mirai/image/saya/',
}
# folder_path = "/home/fate0361/mirai/image/"
# 配置文件2，允许发涩图的群
allow_gid = [
    "757163715",
    "1147675151",
    "727430961",
]
# 配置文件3，无放回采样（开启后在同一图库一轮下来读的文件不重复，第一轮读完之后再重新开始第二轮（简单的说就是用过的图片不再出现））
NoPutBackSampling = True

# 配置文件4，新老图概率（旧图, 去年, 今年）
probabilities_set = [0.2, 0.3, 0.5]

# 配置文件5，数据存档
json_pathway = r"./pic_data.json"  # 存档路径
json_time = time(2, 0)  # 每日自动保存时间

# 遍历路径中的所有文件，并存入字典
key_files_dict = {}
key_list = []
# 穿透获取文件列表方法
def all_listdir(path):  # v1.3弃用
    temp_list = []
    for root, dirs, files in os.listdir(path):
        for file in files:
            temp_list.append(file)
    return temp_list

def all_listdir_2(path):  # v1.3修改
    temp_dict = {}
    for files in os.listdir(path):
        key = change_datetime(getmtime(path + files))
        if key in temp_dict.keys():
            temp_dict[key].append(files)
        else:
            temp_dict[key] = [files]
    return temp_dict

def find_pics(ppd):
    # 从配置文件1的pic_pathway_dict里获取items
    # 格式为{"key": "pathway", ...}
    for k, v in ppd.items():
        # 格式为{"key": {"year": ["pic_name_1", ...], ...}, ...}
        key_files_dict[k] = all_listdir_2(v)
        key_list.append(k)

# 其他方法
def change_datetime(time):
    return datetime.fromtimestamp(time).year

def check_len(key_list):
    longest_key = max(key_list, key=len)
    return len(longest_key)

# 开机就获取文件列表并写入缓存
try:
    with open(json_pathway, "r", encoding="utf-8") as f:
        key_files_dict = json.load(f)
except Exception as e:
    find_pics(pic_pathway_dict)
    logger.info(key_files_dict["key"][datetime.today().year][0])  # 测试用
    logger.info(e)
longest_len = check_len(key_list) + 1

# 每日自动保存
def save():
    with open(json_pathway, 'w', encoding='UTF-8') as f:
        json.dump(key_files_dict, f)

# 添加任务计划，每日定点执行保存
# stop = False
#
# def task():
#     global stop, record_time
#     while not stop:
#         now = datetime.now().time()  # 获取当前时间并输出“时:分”格式
#         if now >= json_time:
#             save()
#             stop = True
#             record_time = datetime.today()  # 记录停止日期
#             print(record_time)
#         t.sleep(3600)
#
# def stop_restart_task():
#     global stop
#     thread = threading.Thread(target=task)
#     thread.start()
#     while True:
#         if stop:
#             if datetime.today().strftime("%Y-%m-%d") == record_time.strftime("%Y-%m-%d"):
#                 print(f"还没到第二天哦，上一次停止时间为{record_time}")
#                 t.sleep(3600)
#             else:
#                 stop = False

def stop_restart_task():
    prev_time: datetime.date | None = None
    while True:


control_thread = threading.Thread(target=stop_restart_task)
control_thread.start()

# 开始异步，等待获取关键词
send_pic = on_regex(pattern=r"^来点(.*?)$", priority=8)
@send_pic.handle()
async def _(
    matcher: Matcher, event: GroupMessage, key: Annotated[str, RegexStr()]
):
    # 判断是否允许发涩图
    gid: str = str(event.sender.group.id)
    if gid not in allow_gid:
        await matcher.finish("不可以涩涩！")
    # 瞎几把抄的检验方式
    key: str = key[2:]
    logger.info(key)  # 控制台输出key值
    if len(key) < 1:
        await matcher.finish("输入参数错误")
    # 检验是否有这种关键词
    if key not in key_list and len(key) < longest_len:  # v1.3修改
        await send_pic.finish("还没有这种涩图喵~")

    # 开始正戏喵
    if key_files_dict[key] == {}:
        # 检验图片目录是否为空
        key_files_dict[key] = all_listdir(pic_pathway_dict[key])  # 更新字典
    # 随机抽取图片
    try:
        year_list = sorted(list(key_files_dict[key].keys()))
        # logger.info(year_list)
        probabilities = []
        # 是不是单独写成一个方法好一点？
        if len(year_list) >= 3:
            for i in year_list:
                if i == year_list[-1]:
                    probabilities.append(probabilities_set[-1])
                elif i == year_list[-2]:
                    probabilities.append(probabilities_set[-2])
                else:
                    probabilities.append(probabilities_set[0] * 1 / (len(year_list) - 2))
            results = random.choices(year_list, weights=probabilities, k=1)[0]  # 在列表中，按权重，抽一次，返回的是列表
            # logger.info(results)
        else:
            # 不足3个，不需要权重
            results = random.choices(year_list, k=1)[0]
            # logger.info(results)
        # 以上步骤先抽取到图片创建的年份，再抽该年份下的图片
        pic_num = random.randint(0, len(key_files_dict[key][results]))  # 抽取随机下标数字
        pic_file = key_files_dict[key][results][pic_num]  # 获取随机下标数字的文件名字
        logger.info(pic_file)
        # v1.3修改，后加路径，防止写爆字典
        pic_pathway_file = pic_pathway_dict[key] + pic_file
        msg = MessageSegment.image(path=pic_pathway_file)  # 写成nonebot发送图片的格式
        # 判断是否需要无放回采样
        if NoPutBackSampling:
            key_files_dict[key][results].pop(pic_num)
        # 判断字典年份下图片是否已抽空
        if key_files_dict[key][results] == []:
            del key_files_dict[key][results]
    except Exception as e:
        msg = MessageSegment.plain("发送图片出错...")
        logger.info(e)
    await send_pic.finish(msg)
