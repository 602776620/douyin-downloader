#!/usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import os
import sys
import json
import yaml
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import logging

# 配置logger
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
# 改名为douyin_logger以避免冲突
douyin_logger = logging.getLogger("DouYin")

# 现在可以安全使用douyin_logger
try:
    import asyncio
    import aiohttp
    ASYNC_SUPPORT = True
except ImportError:
    ASYNC_SUPPORT = False
    douyin_logger.warning("aiohttp 未安装，异步下载功能不可用")

from apiproxy.douyin.douyin import Douyin
from apiproxy.douyin.download import Download
from apiproxy.douyin import douyin_headers
from apiproxy.common import utils

@dataclass
class DownloadConfig:
    """下载配置类"""
    link: List[str]
    path: Path
    music: bool = True
    cover: bool = True
    avatar: bool = True
    json: bool = True
    start_time: str = ""
    end_time: str = ""
    folderstyle: bool = True
    mode: List[str] = field(default_factory=lambda: ["post"])
    thread: int = 5
    cookie: Optional[str] = None
    database: bool = True
    number: Dict[str, int] = field(default_factory=lambda: {
        "post": 0, "like": 0, "allmix": 0, "mix": 0, "music": 0
    })
    increase: Dict[str, bool] = field(default_factory=lambda: {
        "post": False, "like": False, "allmix": False, "mix": False, "music": False
    })
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "DownloadConfig":
        """从YAML文件加载配置"""
        # 实现YAML配置加载逻辑
        
    @classmethod 
    def from_args(cls, args) -> "DownloadConfig":
        """从命令行参数加载配置"""
        # 实现参数加载逻辑
        
    def validate(self) -> bool:
        """验证配置有效性"""
        # 实现验证逻辑


configModel = {
    # 基础配置组
    "link": [],             # 待处理链接列表（用户输入）
    "path": os.getcwd(),    # 文件保存基础路径（默认当前工作目录）
    "music": True,          # 是否下载音频文件
    "cover": True,          # 是否下载封面图片
    "avatar": True,         # 是否下载用户头像
    "json": True,           # 是否生成JSON元数据文件
    "start_time": "",       # 时间筛选范围起始（格式：YYYY-MM-DD HH:MM）
    "end_time": "",         # 时间筛选范围结束（格式同上）
    "folderstyle": True,    # 是否启用结构化文件夹存储
    "mode": ["post"],       # 运行模式选择（支持：post/like/mix/music等）
    "number": {         # 各类型内容的最大下载数量限制
        "post": 0,      # 普通帖子
        "like": 0,      # 点赞作品
        "allmix": 0,    # 全部合集
        "mix": 0,       # 单个合集
        "music": 0,     # 音乐作品
    },
    'database': True,   # 是否启用数据库存储
    "increase": {           # 各类型内容的增量更新开关
        "post": False,      # 普通帖子
        "like": False,      # 点赞作品
        "allmix": False,    # 全部合集
        "mix": False,       # 单个合集
        "music": False,     # 音乐作品
    },
    # 性能与认证配置
    "thread": 5,    # 下载线程数（并发控制）
    "cookie": os.environ.get("DOUYIN_COOKIE", "") # 抖音登录凭证（从环境变量DOUYIN_COOKIE获取）
}


"""
    初始化并配置命令行参数解析器

    该函数创建并配置一个argparse.ArgumentParser对象，定义抖音批量下载工具所需的命令行参数。
    支持从命令行直接指定参数或通过配置文件进行设置，包含下载配置、路径设置、线程控制等参数组。

    Returns:
        argparse.Namespace: 包含所有解析后的参数值的命名空间对象

    参数说明:
        -- 基础配置 --
        cmd     : 运行模式选择(命令行/配置文件)
        config  : 指定外部配置文件路径

        -- 下载设置 --
        link    : 支持多种抖音内容类型的URL，可添加多个链接
        path    : 自定义下载存储路径
        music   : 是否下载音频
        cover   : 是否下载封面
        avatar  : 是否下载作者头像
        json    : 是否保存原始数据

        -- 内容筛选 --
        mode        : 主页下载模式(post/like/mix)
        postnumber  : 主页作品下载数量
        likenumber  : 喜欢作品下载数量
        mixnumber   : 合集作品下载数量

        -- 增量更新 --
        database    : 是否启用数据库记录
        postincrease: 主页作品增量更新开关
        likeincrease: 喜欢作品增量更新开关

        -- 系统配置 --
        thread  : 下载线程数控制(默认5线程)
        cookie  : 用户认证cookie设置
    """
def argument():

    parser = argparse.ArgumentParser(description='抖音批量下载工具 使用帮助')
    # 基础运行模式配置
    parser.add_argument("--cmd", "-C", help="使用命令行(True)或者配置文件(False), 默认为False",
                        type=utils.str2bool, required=False, default=False)
    # 下载内容配置组
    parser.add_argument("--link", "-l",
                        help="作品(视频或图集)、直播、合集、音乐集合、个人主页的分享链接或者电脑浏览器网址",
                        type=str, required=False, default=[], action="append")
    parser.add_argument("--path", "-p", help="下载保存位置, 默认当前文件位置",
                        type=str, required=False, default=os.getcwd())
    # 资源下载开关组
    parser.add_argument("--music", "-m", help="是否下载视频中的音乐(True/False), 默认为True",
                        type=utils.str2bool, required=False, default=True)
    parser.add_argument("--cover", "-c", help="是否下载视频的封面(True/False), 默认为True",
                        type=utils.str2bool, required=False, default=True)
    parser.add_argument("--avatar", "-a", help="是否下载作者的头像(True/False), 默认为True",
                        type=utils.str2bool, required=False, default=True)
    # 数据存储配置
    parser.add_argument("--json", "-j", help="是否保存获取到的数据(True/False), 默认为True",
                        type=utils.str2bool, required=False, default=True)
    parser.add_argument("--folderstyle", "-fs", help="文件保存风格, 默认为True",
                        type=utils.str2bool, required=False, default=True)
    # 内容筛选配置组
    parser.add_argument("--mode", "-M", help="个人主页下载模式(post/like/mix)",
                        type=str, required=False, default=[], action="append")
    parser.add_argument("--postnumber", help="主页作品下载数量设置",
                        type=int, required=False, default=0)
    parser.add_argument("--likenumber", help="主页喜欢作品下载数量设置",
                        type=int, required=False, default=0)
    # 数据库配置组
    parser.add_argument("--database", "-d", help="是否使用数据库, 默认为True",
                        type=utils.str2bool, required=False, default=True)
    # 线程控制参数
    parser.add_argument("--thread", "-t", help="设置线程数, 默认5个线程",
                        type=int, required=False, default=5)
    # 用户认证配置
    parser.add_argument("--cookie", help="设置cookie信息",
                        type=str, required=False, default='')
    # 配置文件参数
    parser.add_argument("--config", "-F",
                       type=argparse.FileType('r', encoding='utf-8'),
                       help="配置文件路径")
    args = parser.parse_args()
    # 确保线程数最小为5
    if args.thread <= 0:
        args.thread = 5

    return args


def yamlConfig():
    """
    从当前脚本所在目录加载并解析 `config.yml` 配置文件，更新全局配置模型 `configModel`。
    该函数会处理以下特殊情况：
    1. 如果配置文件中包含 `cookies` 字段，会将其转换为字符串格式并更新到 `configModel` 中。
    2. 如果配置文件中 `end_time` 字段的值为 "now"，会将其替换为当前日期的字符串格式。
    如果配置文件不存在或解析出错，会记录相应的警告日志。
    """
    # 获取当前脚本所在目录的路径
    curPath = os.path.dirname(os.path.realpath(sys.argv[0]))
    # 拼接配置文件的完整路径
    yamlPath = os.path.join(curPath, "config.yml")
    try:
        # 打开并读取配置文件
        with open(yamlPath, 'r', encoding='utf-8') as f:
            configDict = yaml.safe_load(f)

        # 使用字典推导式简化配置更新
        for key in configModel:
            if key in configDict:
                if isinstance(configModel[key], dict):
                    # 如果配置模型中的值是字典，则更新字典内容
                    configModel[key].update(configDict[key] or {})
                else:
                    # 否则直接更新值
                    configModel[key] = configDict[key]

        # 特殊处理cookie字段，将其转换为字符串格式
        if configDict.get("cookies"):
            cookieStr = "; ".join(f"{k}={v}" for k,v in configDict["cookies"].items())
            configModel["cookie"] = cookieStr

        # 特殊处理end_time字段，如果值为 "now"，则替换为当前日期
        if configDict.get("end_time") == "now":
                configModel["end_time"] = time.strftime("%Y-%m-%d", time.localtime())

    except FileNotFoundError:
        # 如果配置文件不存在，记录警告日志
        douyin_logger.warning("未找到配置文件config.yml")
    except Exception as e:
        # 如果配置文件解析出错，记录警告日志
        douyin_logger.warning(f"配置文件解析出错: {str(e)}")


def validate_config(config: dict) -> bool:
    """
    验证配置字典的有效性。

    该函数检查传入的配置字典是否包含所有必需的键，并且每个键对应的值是否符合预期的类型。
    如果配置无效，函数会记录错误日志并返回 False；否则返回 True。

    参数:
        config (dict): 需要验证的配置字典。

    返回值:
        bool: 如果配置有效返回 True，否则返回 False。
    """
    # 定义必需的键及其对应的类型
    required_keys = {
        'link': list,
        'path': str,
        'thread': int
    }

    # 检查配置字典是否包含所有必需的键，并且类型是否正确
    for key, typ in required_keys.items():
        if key not in config or not isinstance(config[key], typ):
            douyin_logger.error(f"无效配置项: {key}")
            return False

    # 检查 'link' 键对应的值是否为字符串列表
    if not all(isinstance(url, str) for url in config['link']):
        douyin_logger.error("链接配置格式错误")
        return False

    return True


def main():
    """
    主函数，负责整个程序的执行流程。包括配置初始化、参数验证、路径处理、下载器初始化、链接处理以及耗时计算。
    流程概述：
    1. 记录程序开始时间。
    2. 初始化配置，根据命令行参数或YAML文件更新配置。
    3. 验证配置的有效性，若无效则退出。
    4. 检查下载链接是否设置，若未设置则记录错误并退出。
    5. 处理Cookie信息，若配置中有Cookie则更新请求头。
    6. 处理保存路径，确保路径存在并记录路径信息。
    7. 初始化下载器和相关配置。
    8. 遍历所有下载链接，逐个处理。
    9. 计算并记录程序总耗时。
    """
    start = time.time()

    # 配置初始化
    args = argument()
    if args.cmd:
        update_config_from_args(args)
    else:
        yamlConfig()

    if not validate_config(configModel):
        return

    if not configModel["link"]:
        douyin_logger.error("未设置下载链接")
        return

    # Cookie处理
    if configModel["cookie"]:
        douyin_headers["Cookie"] = configModel["cookie"]

    # 路径处理
    configModel["path"] = os.path.abspath(configModel["path"])
    os.makedirs(configModel["path"], exist_ok=True)
    douyin_logger.info(f"数据保存路径 {configModel['path']}")

    # 初始化下载器
    dy = Douyin(database=configModel["database"])
    dl = Download(
        thread=configModel["thread"],
        music=configModel["music"],
        cover=configModel["cover"],
        avatar=configModel["avatar"],
        resjson=configModel["json"],
        folderstyle=configModel["folderstyle"]
    )

    # 处理每个链接
    for link in configModel["link"]:
        process_link(dy, dl, link)

    # 计算耗时
    duration = time.time() - start
    douyin_logger.info(f'\n[下载完成]:总耗时: {int(duration/60)}分钟{int(duration%60)}秒\n')


def process_link(dy, dl, link):
    """
    处理单个链接的下载逻辑。

    该函数负责解析并处理给定的抖音链接，根据链接类型调用相应的处理函数进行下载操作。

    参数:
    - dy: 抖音操作对象，用于获取分享链接和解析链接类型。
    - dl: 下载操作对象，用于执行具体的下载任务。
    - link: 需要处理的抖音链接。

    返回值:
    无返回值。函数执行过程中会记录日志信息，并在出错时记录错误信息。
    """
    # 打印分隔线，表示开始处理一个新的链接
    douyin_logger.info("-" * 80)
    douyin_logger.info(f"[  提示  ]:正在请求的链接: {link}")

    try:
        # 获取分享链接并解析链接类型和关键信息
        url = dy.getShareLink(link)
        key_type, key = dy.getKey(url)

        # 定义不同类型链接的处理函数映射
        handlers = {
            "user": handle_user_download,
            "mix": handle_mix_download,
            "music": handle_music_download,
            "aweme": handle_aweme_download,
            "live": handle_live_download
        }

        # 根据链接类型获取对应的处理函数并执行
        handler = handlers.get(key_type)
        if handler:
            handler(dy, dl, key)
        else:
            # 如果链接类型未知，记录警告信息
            douyin_logger.warning(f"[  警告  ]:未知的链接类型: {key_type}")
    except Exception as e:
        # 捕获并记录处理链接过程中出现的任何异常
        douyin_logger.error(f"处理链接时出错: {str(e)}")


def handle_user_download(dy, dl, key):
    """
    处理用户主页下载功能。

    该函数负责从抖音用户主页下载用户的作品、喜欢的内容或合集。首先获取用户详细信息，
    然后根据配置的模式（如 'post', 'like', 'mix'）分别处理不同的下载任务。

    参数:
    - dy: 抖音API的实例，用于获取用户信息和内容。
    - dl: 下载器实例，用于执行具体的下载操作。
    - key: 用户的sec_uid，用于唯一标识用户。

    返回值:
    无返回值。
    """
    # 记录日志，提示正在请求用户主页下的作品
    douyin_logger.info("[  提示  ]:正在请求用户主页下作品")

    # 获取用户详细信息
    data = dy.getUserDetailInfo(sec_uid=key)
    nickname = ""

    # 如果获取到用户信息，提取并处理用户昵称
    if data and data.get('user'):
        nickname = utils.replaceStr(data['user']['nickname'])

    # 创建用户下载目录，目录名为 "user_昵称_sec_uid"
    userPath = os.path.join(configModel["path"], f"user_{nickname}_{key}")
    os.makedirs(userPath, exist_ok=True)

    # 根据配置的模式，分别处理不同的下载任务
    for mode in configModel["mode"]:
        douyin_logger.info("-" * 80)
        douyin_logger.info(f"[  提示  ]:正在请求用户主页模式: {mode}")

        # 处理 'post' 或 'like' 模式
        if mode in ('post', 'like'):
            _handle_post_like_mode(dy, dl, key, mode, userPath)
        # 处理 'mix' 模式
        elif mode == 'mix':
            _handle_mix_mode(dy, dl, key, userPath)


def _handle_post_like_mode(dy, dl, key, mode, userPath):
    """处理发布/喜欢模式的下载"""
    datalist = dy.getUserInfo(
        key, 
        mode, 
        35, 
        configModel["number"][mode], 
        configModel["increase"][mode],
        start_time=configModel.get("start_time", ""),
        end_time=configModel.get("end_time", "")
    )
    
    if not datalist:
        return
        
    modePath = os.path.join(userPath, mode)
    os.makedirs(modePath, exist_ok=True)
    
    dl.userDownload(awemeList=datalist, savePath=modePath)

def _handle_mix_mode(dy, dl, key, userPath):
    """处理合集模式的下载"""
    mixIdNameDict = dy.getUserAllMixInfo(key, 35, configModel["number"]["allmix"])
    if not mixIdNameDict:
        return

    modePath = os.path.join(userPath, "mix")
    os.makedirs(modePath, exist_ok=True)

    for mix_id, mix_name in mixIdNameDict.items():
        douyin_logger.info(f'[  提示  ]:正在下载合集 [{mix_name}] 中的作品')
        mix_file_name = utils.replaceStr(mix_name)
        datalist = dy.getMixInfo(
            mix_id, 
            35, 
            0, 
            configModel["increase"]["allmix"], 
            key,
            start_time=configModel.get("start_time", ""),
            end_time=configModel.get("end_time", "")
        )
        
        if datalist:
            dl.userDownload(awemeList=datalist, savePath=os.path.join(modePath, mix_file_name))
            douyin_logger.info(f'[  提示  ]:合集 [{mix_name}] 中的作品下载完成')

def handle_mix_download(dy, dl, key):
    """处理单个合集下载"""
    douyin_logger.info("[  提示  ]:正在请求单个合集下作品")
    try:
        datalist = dy.getMixInfo(
            key, 
            35, 
            configModel["number"]["mix"], 
            configModel["increase"]["mix"], 
            "",
            start_time=configModel.get("start_time", ""),
            end_time=configModel.get("end_time", "")
        )
        
        if not datalist:
            douyin_logger.error("获取合集信息失败")
            return
            
        mixname = utils.replaceStr(datalist[0]["mix_info"]["mix_name"])
        mixPath = os.path.join(configModel["path"], f"mix_{mixname}_{key}")
        os.makedirs(mixPath, exist_ok=True)
        dl.userDownload(awemeList=datalist, savePath=mixPath)
    except Exception as e:
        douyin_logger.error(f"处理合集时出错: {str(e)}")

def handle_music_download(dy, dl, key):
    """处理音乐作品下载"""
    douyin_logger.info("[  提示  ]:正在请求音乐(原声)下作品")
    datalist = dy.getMusicInfo(key, 35, configModel["number"]["music"], configModel["increase"]["music"])

    if datalist:
        musicname = utils.replaceStr(datalist[0]["music"]["title"])
        musicPath = os.path.join(configModel["path"], f"music_{musicname}_{key}")
        os.makedirs(musicPath, exist_ok=True)
        dl.userDownload(awemeList=datalist, savePath=musicPath)

def handle_aweme_download(dy, dl, key):
    """处理单个作品下载"""
    douyin_logger.info("[  提示  ]:正在请求单个作品")
    
    # 最大重试次数
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            douyin_logger.info(f"[  提示  ]:第 {retry_count+1} 次尝试获取作品信息")
            result = dy.getAwemeInfo(key)
            
            if not result:
                douyin_logger.error("[  错误  ]:获取作品信息失败")
                retry_count += 1
                if retry_count < max_retries:
                    douyin_logger.info("[  提示  ]:等待 5 秒后重试...")
                    time.sleep(5)
                continue
            
            # 直接使用返回的字典，不需要解包
            datanew = result
            
            if datanew:
                awemePath = os.path.join(configModel["path"], "aweme")
                os.makedirs(awemePath, exist_ok=True)
                
                # 下载前检查视频URL
                video_url = datanew.get("video", {}).get("play_addr", {}).get("url_list", [])
                if not video_url or len(video_url) == 0:
                    douyin_logger.error("[  错误  ]:无法获取视频URL")
                    retry_count += 1
                    if retry_count < max_retries:
                        douyin_logger.info("[  提示  ]:等待 5 秒后重试...")
                        time.sleep(5)
                    continue
                    
                douyin_logger.info(f"[  提示  ]:获取到视频URL，准备下载")
                dl.userDownload(awemeList=[datanew], savePath=awemePath)
                douyin_logger.info(f"[  成功  ]:视频下载完成")
                return True
            else:
                douyin_logger.error("[  错误  ]:作品数据为空")
                
            retry_count += 1
            if retry_count < max_retries:
                douyin_logger.info("[  提示  ]:等待 5 秒后重试...")
                time.sleep(5)
                
        except Exception as e:
            douyin_logger.error(f"[  错误  ]:处理作品时出错: {str(e)}")
            retry_count += 1
            if retry_count < max_retries:
                douyin_logger.info("[  提示  ]:等待 5 秒后重试...")
                time.sleep(5)
    
    douyin_logger.error("[  失败  ]:已达到最大重试次数，无法下载视频")

def handle_live_download(dy, dl, key):
    """处理直播下载"""
    douyin_logger.info("[  提示  ]:正在进行直播解析")
    live_json = dy.getLiveInfo(key)
    
    if configModel["json"] and live_json:
        livePath = os.path.join(configModel["path"], "live")
        os.makedirs(livePath, exist_ok=True)
        
        live_file_name = utils.replaceStr(f"{key}{live_json['nickname']}")
        json_path = os.path.join(livePath, f"{live_file_name}.json")
        
        douyin_logger.info("[  提示  ]:正在保存获取到的信息到result.json")
        with open(json_path, "w", encoding='utf-8') as f:
            json.dump(live_json, f, ensure_ascii=False, indent=2)

# 条件定义异步函数
if ASYNC_SUPPORT:
    async def download_file(url, path):
        """
        异步下载文件并保存到指定路径。
        参数:
        - url (str): 要下载的文件的URL地址。
        - path (str): 文件保存的本地路径。
        返回值:
        - bool: 如果文件成功下载并保存，返回True；否则返回False。
        """
        async with aiohttp.ClientSession() as session:
            # 发起GET请求获取文件内容
            async with session.get(url) as response:
                # 检查响应状态码是否为200（成功）
                if response.status == 200:
                    # 将文件内容写入本地文件
                    with open(path, 'wb') as f:
                        f.write(await response.read())
                    return True
        # 如果下载失败，返回False
        return False


def update_config_from_args(args):
    """从命令行参数更新配置"""
    configModel["link"] = args.link
    configModel["path"] = args.path
    configModel["music"] = args.music
    configModel["cover"] = args.cover
    configModel["avatar"] = args.avatar
    configModel["json"] = args.json
    configModel["folderstyle"] = args.folderstyle
    configModel["mode"] = args.mode if args.mode else ["post"]
    configModel["thread"] = args.thread
    configModel["cookie"] = args.cookie
    configModel["database"] = args.database
    
    # 更新number字典
    configModel["number"]["post"] = args.postnumber
    configModel["number"]["like"] = args.likenumber
    configModel["number"]["allmix"] = args.allmixnumber
    configModel["number"]["mix"] = args.mixnumber
    configModel["number"]["music"] = args.musicnumber
    
    # 更新increase字典
    configModel["increase"]["post"] = args.postincrease
    configModel["increase"]["like"] = args.likeincrease
    configModel["increase"]["allmix"] = args.allmixincrease
    configModel["increase"]["mix"] = args.mixincrease
    configModel["increase"]["music"] = args.musicincrease

if __name__ == "__main__":
    main()
