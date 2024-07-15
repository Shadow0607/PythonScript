#!/usr/bin/env python3
# coding:utf-8

import os
import re
import shutil
import time
from typing import Generator, Any
from config_reader import load_NAS_config,load_log_config,load_MYSQL_config
from logger import log
from database_manager import DatabaseManager
config = load_NAS_config()
config_log =load_log_config()
db_manager = DatabaseManager()
# 配置
VIDEO_DIR = config['NAS_PATH']
LOG_DIR = load_log_config()

RECORD_TIME = 3600 * 10  # 10 hours

def logger_message(message):
    log(message,config_log['LOG_FOLDER'], 'move_file')

TO_REPLACE = [
    r"@jnty60\\.app", "@69館", r"@69av\\.me", r"aavv39\\.xyz@", "@九游@jy", r"@九游@5jy.cc",
    "@jnty4588.com_", "@九游@  jy", "5jy.cc-", "@江南-", "hhd800.com@", 
    "aavv38.xyz@435", "[gg5.co]", "@江南@", "jnty4588.com", "nyap2p.com",
    "aavv38.xyz@", "jn-89-9.vip", "_2K", "_4K", "_6K", "@江南@jnty4588.com", "@九游娛樂@ 5jy.cc",
    "aavv-3-8.xyz@", "@九游@", "mp-4", "kfa11.com@", "18bt.net", "@Milan@ml2074.com_","@Milan@ty999.me_","kcf9.com"
]

FILE_EXTENSIONS = [".mp4", ".srt", ".wmv", ".jpg"]

def should_keep_file(file_path: str) -> bool:
    file_name = os.path.basename(file_path)
    parent_dir = os.path.basename(os.path.dirname(file_path))
    return parent_dir.lower() in file_name.lower()

# 文件操作函數
def get_recent_files(dir_path: str) -> Generator[str, None, None]:
    current_time = time.time()
    for root, _, files in os.walk(dir_path):
        # 跳過包含 @eaDir 的目錄
        if "@eaDir" in root:
            continue
        for file in files:
            # 跳過 SYNOVIDEO_VIDEO_SCREENSHOT.jpg 文件
            if file == "SYNOVIDEO_VIDEO_SCREENSHOT.jpg":
                continue
            file_path = os.path.join(root, file)
            if (any(file.lower().endswith(ext) for ext in FILE_EXTENSIONS) and
                (current_time - os.path.getmtime(file_path)) < RECORD_TIME):
                yield file_path


def split_string(s):
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

def clean_filename(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    print(f"name:{name},ext:{ext}")
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
    path=db_manager.get_path_video_num(video_num)
    print(f"video_num:{video_num},category:{category},path:{path}")
    new_filename = f"{new_name}{ext}"
    
    if not is_valid_filename(new_filename):
        print(f"Error: The filename '{new_filename}' does not match the expected pattern.")
        return filename
    return path,new_filename

def is_valid_filename(filename: str) -> bool:
    extensions_pattern = '|'.join([re.escape(ext) for ext in FILE_EXTENSIONS])
    pattern = rf'^[a-zA-Z]+-\d+(-[a-zA-Z]+)?({extensions_pattern})$'
    return bool(re.match(pattern, filename, re.IGNORECASE))

# 主要處理函數
def process_files():
    rename_files()
    move_files()
    delete_unnecessary_files_and_folders(VIDEO_DIR)
    clean_empty_folders(VIDEO_DIR)

def rename_files():
    for file_path in get_recent_files(VIDEO_DIR):
        directory, filename = os.path.split(file_path)
        print(f"directory:{directory}, filename:{filename}")
        path,new_filename = clean_filename(filename)
        print(f"path:{path},filename:{new_filename}")
        if path == None:
            # 如果找不到對應的路徑，就使用原始目錄
            new_file_path = os.path.join(directory, new_filename)
        else:
            new_file_path = os.path.join(path, new_filename)
        
        if new_file_path != file_path:
            try:
                print(f"Renaming file: {file_path} -> {new_file_path}")
                shutil.move(file_path, new_file_path)
            except Exception as e:
                logger_message(f"Error renaming file {file_path}: {e}")

def move_files() -> None:
    files_to_move = [f for f in get_recent_files(VIDEO_DIR)]
    for file_path in files_to_move:
        print(files_to_move)
        components = file_path.split("/")
        name, ext = os.path.splitext(components[-1])
        video_num, category = split_string(name)
        print(f"name:{name},ext:{ext},video_num:{video_num},category:{category}")
        path=db_manager.get_path_video_num(video_num)
        if path == None:
            new_file_path = os.path.join(file_path, components[-1])
        else:
            new_file_path = os.path.join(path, components[-1])
                
        # 移動文件
        print(f"Moving {file_path} to {new_file_path}")
        shutil.move(file_path, new_file_path)        
        old_folder = "/".join(components[:4])
        print(old_folder)
        # 檢查並清理舊文件夾

def delete_unnecessary_files_and_folders(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        # 跳过 @eaDir 文件夹
        if "@eaDir" in root:
            continue

        for file in files:
            # 跳过 SYNOVIDEO_VIDEO_SCREENSHOT.jpg 文件
            if file == "SYNOVIDEO_VIDEO_SCREENSHOT.jpg":
                continue

            file_path = os.path.join(root, file)
            name, ext = os.path.splitext(file)
            video_num, _ = split_string(name)
            
            # 检查文件是否在数据库中
            if db_manager.check_video_num(video_num) is None:
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                    logger_message(f"Deleted file: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
                    logger_message(f"Error deleting file {file_path}: {e}")

        # 处理文件夹
        if not any(files) and not any(dirs):
            try:
                shutil.rmtree(root)
                logger_message(f"Deleted empty folder: {root}")
            except Exception as e:
                logger_message(f"Error deleting folder {root}: {e}")

def clean_empty_folders(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            
            # 检查是否只包含 @eaDir
            if os.listdir(dir_path) == ["@eaDir"]:
                try:
                    shutil.rmtree(os.path.join(dir_path, "@eaDir"))
                    os.rmdir(dir_path)
                    logger_message(f"Deleted folder with only @eaDir: {dir_path}")
                    print(f"Deleted folder with only @eaDir: {dir_path}")
                except Exception as e:
                    logger_message(f"Error deleting folder {dir_path}: {e}")
            
            # 检查是否为空文件夹
            elif not os.listdir(dir_path):
                try:
                    #os.rmdir(dir_path)
                    logger_message(f"Deleted empty folder: {dir_path}")
                    print(f"Deleted empty folder: {dir_path}")
                except Exception as e:
                    #logger_message(f"Error deleting empty folder {dir_path}: {e}")      
                    print(f"Error deleting empty folder {dir_path}: {e}")

if __name__ == "__main__":
    process_files()