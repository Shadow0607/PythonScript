# utils.py
import os
import re
from typing import Tuple, Optional
from config_reader import load_NAS_config, load_log_config,load_NAS_ROOT_config
from database_manager import DatabaseManager
from logger import log
import subprocess
import time

config = load_NAS_config()
config_log = load_log_config()
db_manager = DatabaseManager()

VIDEO_DIR = load_NAS_ROOT_config()
FILE_EXTENSIONS = [".mp4", ".srt", ".wmv", ".jpg",".mkv"]

TO_REPLACE = [
    r"@jnty60\\.app", "@69館", r"@69av\\.me", r"aavv39\\.xyz@", "@九游@jy", r"@九游@5jy.cc",
    "@jnty4588.com_", "@九游@  jy", "5jy.cc-", "@江南-", "hhd800.com@", 
    "aavv38.xyz@435", "[gg5.co]", "@江南@", "jnty4588.com", "nyap2p.com",
    "aavv38.xyz@", "jn-89-9.vip", "_2K", "_4K", "_6K", "@江南@jnty4588.com", "@九游娛樂@ 5jy.cc",
    "aavv-3-8.xyz@", "@九游@", "mp-4", "kfa11.com@", "18bt.net", "@Milan@ml2074.com_","@Milan@ty999.me_","kcf9.com@","kfa33.com@300","@"
]


def logger_message(message):
    log(message, config_log['LOG_FOLDER'], 'utils')


def split_string(s: str) -> Tuple[str, str]:
    match = re.match(r"(.*-.*)-([A-Z]*)$", s)
    if match:
        video_num = match.group(1)
        category = match.group(2)
        if category.upper() in ['UC','UCMP4']:
            return video_num, 'UC'
        elif category.upper() in ['C','CHNYAP2P.COM','MP4','HD','CH']:
            return video_num, 'C'
        elif category.upper() in ['U','UNCENSORED','UMP4']:
            return video_num, 'U'
        else:
            return video_num, 'N'
    else:
        return s, "N"

def is_valid_filename(filename: str) -> bool:
    extensions_pattern = '|'.join([re.escape(ext) for ext in FILE_EXTENSIONS])
    #pattern = rf'^[a-zA-Z]+-\d+(-[a-zA-Z]+)?({extensions_pattern})$'
    pattern = r'^[a-zA-Z]+-\d+(-[a-zA-Z]+)?$'
    return bool(re.match(pattern, filename, re.IGNORECASE))


def clean_filename(filename: str) -> str:

    # 應用現有的替換模式
    for pattern in TO_REPLACE:
        filename = filename.replace(pattern, '')
    # 移除文件擴展名
    name, ext = os.path.splitext(filename)
    
    # 移除所有方括號及其內容
    name = re.sub(r'\[.*?\]', '', name)
    
    # 替換下劃線為連字符，並去除首尾空白
    name = name.replace('_', '-').strip()
    
    # 使用正則表達式提取視頻編號和類別
    #match = re.search(r'([A-Za-z]+)-?(\d+)(?:-([CUH]|UC))?', name, re.IGNORECASE)
    match = re.search(r'([A-Za-z]+)-?(\d+)(?:-(UC|C|U|H))?', name, re.IGNORECASE)
    #logger_message(f'name:{name}，match:{match}')
    if match:
        video_code = match.group(1).upper()
        video_number = match.group(2)
        category = match.group(3).upper() if match.group(3) else ''
        
        new_name = f"{video_code}-{video_number}"
        if category:
            new_name += f"-{category}"
    else:
        # 如果沒有匹配到預期的格式，使用原有的清理邏輯
        name_parts = re.findall(r'[a-zA-Z]+|\d+', name)
        
        if len(name_parts) > 2:
            last_element = name_parts[-1].lower()
            if last_element in ['ch', 'chnyap2p.com', 'mp4', 'hd']:
                name_parts[-1] = 'C'
            elif last_element in ['uncensored', 'ump4']:
                name_parts[-1] = 'U'
            elif last_element in ['ucmp4','uc']:
                name_parts[-1] = 'UC'
        
        new_name = '-'.join(name_parts[:3]).strip().upper()
    
    return new_name

def mount_NAS():
    username = config['NAS_USERNAME']
    password = config['NAS_PASSWORD']
    nas_ip = config['NAS_IP']
    folder = config['ROOT_FOLDER']
    windows_path = config['WINDOWS_PATH'].rstrip('\\')
    nas_share = fr"\\{nas_ip}{folder}"

    # 先嘗試斷開現有連接
    subprocess.run(f"net use {windows_path} /delete /y", shell=True, check=False)

    # 映射網絡驅動器的命令
    map_command = f"net use {windows_path} {nas_share} /user:{username} {password} /persistent:no"
    
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            #logger_message(f"嘗試映射 NAS 共享 (嘗試 {attempt + 1}/{max_attempts})")
            result = subprocess.run(map_command, shell=True, check=True, capture_output=True, text=True)
            #logger_message(f"NAS 共享 {nas_share} 已成功映射到驅動器 {windows_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger_message(f"映射失敗 (嘗試 {attempt + 1}/{max_attempts}): {e}")
            logger_message(f"錯誤輸出: {e.stderr}")
            if attempt < max_attempts - 1:
                logger_message("等待 10 秒後重試...")
                time.sleep(10)
    
    logger_message("所有嘗試均失敗，無法映射 NAS 共享")
    return False

def delete_NAS_connect():
    try:
        subprocess.run("net use Y: /delete", shell=True, check=True)
        print("成功斷開 Y: 驅動器連接")
    except subprocess.CalledProcessError as e:
        print(f"斷開連接時發生錯誤: {e}")

