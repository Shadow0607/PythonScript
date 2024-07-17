# utils.py
import os
import re
from typing import Tuple, Optional
from config_reader import load_NAS_config, load_log_config
from database_manager import DatabaseManager

config = load_NAS_config()
config_log = load_log_config()
db_manager = DatabaseManager()

VIDEO_DIR = config['NAS_PATH']
FILE_EXTENSIONS = [".mp4", ".srt", ".wmv", ".jpg"]

TO_REPLACE = [
    r"@jnty60\\.app", "@69館", r"@69av\\.me", r"aavv39\\.xyz@", "@九游@jy", r"@九游@5jy.cc",
    "@jnty4588.com_", "@九游@  jy", "5jy.cc-", "@江南-", "hhd800.com@", 
    "aavv38.xyz@435", "[gg5.co]", "@江南@", "jnty4588.com", "nyap2p.com",
    "aavv38.xyz@", "jn-89-9.vip", "_2K", "_4K", "_6K", "@江南@jnty4588.com", "@九游娛樂@ 5jy.cc",
    "aavv-3-8.xyz@", "@九游@", "mp-4", "kfa11.com@", "18bt.net", "@Milan@ml2074.com_","@Milan@ty999.me_","kcf9.com"
]

def process_filename(filename: str) -> Tuple[str, str, bool]:
    name, ext = os.path.splitext(filename)
    video_num, category = split_string(name)
    is_valid = is_valid_filename(filename)
    return video_num, category, is_valid

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
    pattern = rf'^[a-zA-Z]+-\d+(-[a-zA-Z]+)?({extensions_pattern})$'
    return bool(re.match(pattern, filename, re.IGNORECASE))

def clean_filename(filename: str) -> Tuple[Optional[str], str]:
    name, ext = os.path.splitext(filename)
    for pattern in TO_REPLACE:
        name = name.replace(pattern, '')
    name = name.replace('_', '-').strip()
    name_parts = re.findall(r'[a-zA-Z]+|\d+', name)
    
    if len(name_parts) > 2:
        last_element = name_parts[-1].lower()
        if last_element in ['ch', 'chnyap2p.com', 'mp4', 'hd']:
            name_parts[-1] = 'C'
        elif last_element in ['uncensored', 'ump4']:
            name_parts[-1] = 'U'
        elif last_element in ['ucmp4','uc']:
            name_parts[-1] = 'UC'
    
    new_name = '-'.join(name_parts).strip().upper()
    video_num, category = split_string(new_name)
    path = db_manager.get_path_video_num(video_num)
    new_filename = f"{new_name}{ext}"
    
    if not is_valid_filename(new_filename):
        print(f"Error: The filename '{new_filename}' does not match the expected pattern.")
        return None, filename
    return path, new_filename