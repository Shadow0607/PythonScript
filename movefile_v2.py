#!/usr/bin/env python3
# coding:utf-8

import os
import re
import shutil
import time
import datetime
import logging
from typing import Generator, Any

# 配置
VIDEO_DIR = "/volume1/12311231123"
LOG_DIR = "/volume1/1231231231231231231231"
RECORD_TIME = 3600 * 10  # 10 hours

TO_REPLACE = [
    r"@jnty60\\.app", "@69館", r"@69av\\.me", r"aavv39\\.xyz@", "@九游@jy", r"@九游@5jy.cc",
    "@jnty4588.com_", "@九游@  jy", "5jy.cc-", "@江南-", "hhd800.com@", 
    "aavv38.xyz@435", "[gg5.co]", "@江南@", "jnty4588.com", "nyap2p.com",
    "aavv38.xyz@", "jn-89-9.vip", "_2K", "_4K", "_6K", "@江南@jnty4588.com", "@九游娛樂@ 5jy.cc",
    "aavv-3-8.xyz@", "@九游@", "mp-4", "kfa11.com@", "18bt.net", "@Milan@ml2074.com_","@Milan@ty999.me_"
]

DELETE_FILENAME = ["社區最新情報", "台妹子"]
FILE_EXTENSIONS = [".mp4", ".srt", ".wmv", ".jpg"]

def should_keep_file(file_path: str) -> bool:
    """
    檢查文件是否應該保留。
    如果文件名包含其父文件夾的名稱，則保留該文件。
    """
    file_name = os.path.basename(file_path)
    parent_dir = os.path.basename(os.path.dirname(file_path))
    return parent_dir.lower() in file_name.lower()

# 設置日誌
def setup_logging():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"log_{today}.txt")
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 文件操作函數
def get_recent_files(dir_path: str) -> Generator[str, None, None]:
    current_time = time.time()
    for root, _, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            if (any(file.lower().endswith(ext) for ext in FILE_EXTENSIONS) and
                (current_time - os.path.getmtime(file_path)) < RECORD_TIME):
                yield file_path

def clean_filename(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    for pattern in TO_REPLACE:
        name = name.replace(pattern, '')
    name = name.replace('_', '-').strip()
    name_parts = re.findall(r'[a-zA-Z]+|\d+', name)
    
    if len(name_parts) > 2:
        last_element = name_parts[-1].lower()
        if last_element in ['ch', 'ucmp4', 'chnyap2p.com', 'uc', 'mp4', 'hd']:
            name_parts[-1] = 'C'
        elif last_element in ['uncensored', 'ump4']:
            name_parts[-1] = 'U'
    
    new_name = '-'.join(name_parts).strip().upper()
    new_filename = f"{new_name}{ext}"
    
    if not is_valid_filename(new_filename):
        logging.error(f"Error: The filename '{new_filename}' does not match the expected pattern.")
        return filename
    return new_filename

def is_valid_filename(filename: str) -> bool:
    extensions_pattern = '|'.join([re.escape(ext) for ext in FILE_EXTENSIONS])
    pattern = rf'^[a-zA-Z]+-\d+(-[a-zA-Z]+)?({extensions_pattern})$'
    return bool(re.match(pattern, filename, re.IGNORECASE))

# 主要處理函數
def process_files():
    rename_files()
    move_files()
    clean_empty_folders()

def rename_files():
    for file_path in get_recent_files(VIDEO_DIR):
        if any(keyword in file_path for keyword in DELETE_FILENAME):
            logging.info(f"Removing file: {file_path}")
            os.remove(file_path)
            continue
        
        directory, filename = os.path.split(file_path)
        new_filename = clean_filename(filename)
        new_file_path = os.path.join(directory, new_filename)
        
        if new_file_path != file_path:
            logging.info(f"Renaming file: {file_path} -> {new_file_path}")
            shutil.move(file_path, new_file_path)

def move_files() -> None:
    files_to_move = [f for f in get_recent_files(VIDEO_DIR) if len(f.split("/")) >= 6]
    for file_path in files_to_move:
        components = file_path.split("/")
        new_file_path = "/".join(components[:4] + components[-1:])
        old_folder = "/".join(components[:4] + components[-2:-1])
        
        # 移動文件
        logging.info(f"Moving {file_path} to {new_file_path}")
        shutil.move(file_path, new_file_path)
        
        # 檢查並清理舊文件夾
        if os.path.exists(old_folder):
            try:
                # 檢查文件夾中的所有文件
                for root, _, files in os.walk(old_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if should_keep_file(file_path):
                            # 如果文件應該保留，將其移動到新位置
                            new_file_location = os.path.join("/".join(components[:4]), file)
                            logging.info(f"Keeping file and moving to: {new_file_location}")
                            shutil.move(file_path, new_file_location)
                        else:
                            # 如果文件不需要保留，刪除它
                            logging.info(f"Deleting file: {file_path}")
                            os.remove(file_path)
                
                # 刪除現在應該是空的文件夾
                shutil.rmtree(old_folder)
                logging.info(f"Deleted folder: {old_folder}")
            except Exception as e:
                logging.error(f"Error processing {old_folder}: {e}")

def clean_empty_folders():
    for root, dirs, _ in os.walk(VIDEO_DIR, topdown=False):
        dirs[:] = [d for d in dirs if d != "@eaDir"]
        for name in dirs:
            dir_path = os.path.join(root, name)
            if not os.listdir(dir_path) or os.listdir(dir_path) == ["@eaDir"]:
                try:
                    shutil.rmtree(dir_path)
                    logging.info(f"Deleted empty folder: {dir_path}")
                except Exception as e:
                    logging.error(f"Error deleting {dir_path}: {e}")

if __name__ == "__main__":
    setup_logging()
    process_files()