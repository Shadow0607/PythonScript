#!/usr/bin/env python3
# coding:utf-8

import os
import shutil
import time
from typing import Generator
from config_reader import load_NAS_config, load_log_config
from logger import log
from database_manager import DatabaseManager
from utils import clean_filename, FILE_EXTENSIONS, VIDEO_DIR,mount_NAS,delete_NAS_connect,split_string
import platform
import requests
from bs4 import BeautifulSoup
config = load_NAS_config()
config_log = load_log_config()
db_manager = DatabaseManager()

RECORD_TIME = 3600 * 12  # 10 hours
system = platform.system()

def logger_message(message):
    log(message, config_log['LOG_FOLDER'], 'move_file')

def get_recent_files(dir_path: str) -> Generator[str, None, None]:
    current_time = time.time()
    for root, _, files in os.walk(dir_path):
        if "@eaDir" in root:
            continue
        for file in files:
            if file == "SYNOVIDEO_VIDEO_SCREENSHOT.jpg":
                continue
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file)[1].lower()
            if file_extension not in FILE_EXTENSIONS:
                try:
                    delete_file_or_folder(file_path)
                    logger_message(f"刪除不符合副檔名的檔案: {file_path}")
                except Exception as e:
                    logger_message(f"刪除檔案 {file_path} 失敗: {e}")
                continue
            if (current_time - os.path.getmtime(file_path)) < RECORD_TIME:
                yield file_path
            
def get_video_num_actor_link(video_num):
    url = f'https://javdb.com/search?q={video_num}&f=all'
    found_links = []
    try:
        response = requests.get(url)
        response.raise_for_status()
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            video_divs = soup.find_all('div', class_='video-title')
            for video_div in video_divs:
                strong_tag = video_div.find('strong')

                if strong_tag and strong_tag.text.strip() == video_num:
                    parent_a = strong_tag.find_parent('a')
                    href = parent_a.get('href')
                    #print({parent_a})
                    found_links.append((href, video_num))
                #time.sleep(10)
        if not found_links:
            logger_message("沒有找到'今日新種'標籤")
            return None
        else:
            for link, code in found_links:
                path=download_video_link(link, code)
                return path

    except Exception as e:
        logger_message(f'Error occurred: {e}')

def compare_and_keep_smaller_file(file_path, new_file_path):
    if os.path.exists(new_file_path):
        # 比較檔案大小
        original_size = os.path.getsize(file_path)
        new_size = os.path.getsize(new_file_path)
        
        #logger_message(f"原始檔案大小: {original_size}, 新檔案大小: {new_size}")
        
        if original_size < new_size:
            # 如果原始檔案較小，刪除新檔案並重命名原始檔案
            
            #logger_message(f"保留較小的原始檔案: {file_path}")
            os.remove(new_file_path)
            os.rename(file_path, new_file_path)
            #logger_message(f"重命名後，新文件是否存在: {os.path.exists(new_file_path)}")
            logger_message(f"文件已成功重命名為: {new_file_path}")
        elif original_size >new_size:
            # 如果新檔案較小或相等，刪除原始檔案
            logger_message(f"保留較小的新檔案: {new_file_path}")
            os.remove(file_path)
        else:
            logger_message(f"大小一致，保留原始檔案: {file_path}")
            pass
    else:
        logger_message(f"新檔案不存在，直接重命名: {os.path.exists(new_file_path)}")
        # 如果新檔案不存在，直接重命名
        os.rename(file_path, new_file_path)
        

def download_video_link(link, video_code):
    logger_message(f"Link:{link}")
    child_url = f'https://javdb.com{link}'
    try:
        response = requests.get(child_url)
        response.raise_for_status()
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            actor_section = soup.find('strong', string='演員:')
            # time.sleep(10)
            if actor_section:
                value_span = actor_section.find_next_sibling('span', class_='value')
                if value_span:
                    actors = [a.text for a in value_span.find_all('a')]
                    for actor in actors:
                        actor_data = db_manager.get_pure_actor_by_dynamic_value('check_ch_name', actor) or db_manager.get_pure_actor_by_dynamic_value('check_jp_name', actor)
                        if actor_data:
                            #logger_message(f"actor:{actor_data}")
                            return actor_data
                            
    except Exception as e:
        logger_message(f'Error occurred: {e}')

def process_files():
    
    if system != 'Linux':
        mount_NAS()
    rename_files()
    clean_empty_folders(VIDEO_DIR)
    if system != 'Linux':
        delete_NAS_connect()

def get_database_root_path(dir_path):
    linux_path = dir_path.replace('Y:', '/volume1/video/').replace('\\', '/')
    linux_path = normalize_path(linux_path)
    return db_manager.get_pure_actor_by_dynamic_value('check_actor_path', linux_path)

def process_recent_file(file_path, filename, file_extension, database_root_path):
    directory = os.path.dirname(file_path)
    last_folder = os.path.basename(directory)
    #logger_message(f"目錄: {directory}")
    #logger_message(f"文件名: {filename}")
    #logger_message(f"副檔名: {file_extension}")
    #logger_message(f"最後一層資料夾: {last_folder}")

    if last_folder.upper() not in filename.upper():
        delete_file_or_folder(file_path)
        #logger_message(f"刪除不符合規則的檔案: {file_path}")
        return

    new_filename = clean_filename(filename)
    if not new_filename:
        delete_file_or_folder(file_path)
        logger_message(f"刪除不符合規則的檔案: {file_path}")
        return

    video_num, category = split_string(new_filename)
    path = db_manager.get_actor_by_video_num(video_num) or get_video_num_actor_link(video_num)

    if path:
        db_manager.insert_av_video(path['id'], video_num, category, 'N')
        new_file_path = os.path.join(path['path'], f"{new_filename}{file_extension}")
    else:
        new_file_path = os.path.join(directory, f"{new_filename}{file_extension}")

    if system != 'Linux':
        new_file_path = new_file_path.replace('/volume1/video/', 'Y:').replace('/', '\\')

    if new_file_path != file_path:
        try:
            #logger_message(f"正在重命名文件: {file_path} -> {new_file_path}")
            #logger_message(f"源文件是否存在: {os.path.exists(file_path)}")
            #logger_message(f"目標路徑是否存在: {os.path.exists(os.path.dirname(new_file_path))}")
            compare_and_keep_smaller_file(file_path, new_file_path)
        except Exception as e:
            logger_message(f"重命名文件 {file_path} 時出錯: {e}")

def handle_database_root_file(file_path, filename, database_root_path,file_extension):
    new_filename = clean_filename(filename)
    video_num, category = split_string(new_filename)
    logger_message(f"video_num:{video_num}")   
    path = get_video_num_actor_link(video_num) or db_manager.get_actor_by_video_num(video_num)
    #logger_message(f"path:{path}")  
    new_filename_directory=path['path']
    #logger_message(f"new_filename_directory:{new_filename_directory}，filename:{filename}")    
    if path and path != os.path.basename(database_root_path['path']):
        if system != 'Linux':
            new_filename_directory = new_filename_directory.replace('/volume1/video/', 'Y:\\\\')
        try:
            new_filename_directory = os.path.join(new_filename_directory, f"{new_filename}{file_extension}")
            compare_and_keep_smaller_file(file_path, new_filename_directory)
            logger_message(f"處理數據庫根目錄文件: {file_path} -> {new_filename_directory}")
        except Exception as e:
            logger_message(f"處理數據庫根目錄文件 {file_path} 時出錯: {e}")
        finally:
            pass
    else:
        logger_message(f"跳過數據庫根目錄文件: {file_path}")
    
def rename_files():
    for file_path in get_recent_files(VIDEO_DIR):
        directory, full_filename = os.path.split(file_path)
        filename, file_extension = os.path.splitext(full_filename)
        
        dir_path = normalize_path(directory)
        database_root_path = get_database_root_path(dir_path)

        last_folder = os.path.basename(directory)
        if database_root_path and last_folder == os.path.basename(database_root_path['path']):
            handle_database_root_file(file_path, filename, database_root_path,file_extension)
        else:
            process_recent_file(file_path, filename, file_extension, database_root_path)

def clean_empty_folders(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            dir_path = normalize_path(dir_path)
            database_root_path = None
            if "@eaDir" in dir_path:
                #logger_message(f"Skipping @eaDir root path : {dir_path}")
                continue
            #logger_message(f"dir_path:{dir_path}")
            # 統一處理路徑轉換
            linux_path = dir_path.replace('Y:', '/volume1/video/').replace('\\', '/')
            linux_path = normalize_path(linux_path)

            database_root_path = db_manager.get_pure_actor_by_dynamic_value('check_actor_path', linux_path)
            #logger_message(f"dir_path:{dir_path}, database_root_path:{database_root_path}, linux_path:{linux_path}, root:{root}")
            
            # 檢查是否為數據庫中的根目錄
            if database_root_path:
                if normalize_path(linux_path) == normalize_path(database_root_path['path']):
                    continue
                else:
                    #logger_message(f"Skipping database root path: {dir_path}")
                    continue

            # 處理只包含 @eaDir 的資料夾
            if os.listdir(dir_path) == ["@eaDir"]:
                try:
                    shutil.rmtree(os.path.join(dir_path, "@eaDir"))
                    os.rmdir(dir_path)
                    #logger_message(f"Deleted folder with only @eaDir: {dir_path}")
                    #print(f"Deleted folder with only @eaDir: {dir_path}")
                except Exception as e:
                    logger_message(f"Error deleting folder {dir_path}: {e}")
            
            # 處理空資料夾
            elif not os.listdir(dir_path):
                try:
                    delete_file_or_folder(dir_path)
                    #logger_message(f"Deleted empty folder: {dir_path}")
                    #print(f"Deleted empty folder: {dir_path}")
                except Exception as e:
                    logger_message(f"Error deleting empty folder {dir_path}: {e}")
            else:
                logger_message(f"Skipping non-empty folder: {dir_path}")

def delete_file_or_folder(path):
    try:
        if os.path.isfile(path):
            # 如果是檔案，直接刪除
            os.remove(path)
            logger_message(f"檔案已成功刪除: {path}")
        elif os.path.isdir(path):
            # 如果是資料夾，使用 shutil.rmtree() 刪除整個資料夾及其內容
            shutil.rmtree(path)
            logger_message(f"資料夾已成功刪除: {path}")
        else:
            # 如果既不是檔案也不是資料夾
            logger_message(f"指定的路徑既不是檔案也不是資料夾: {path}")
            return False
        return True
    except Exception as e:
        logger_message(f"刪除時發生錯誤: {e}")
        return False

def normalize_path(path):
    # 替換所有的反斜線為正斜線
    path = path.replace('\\', '/')
    # 移除重複的斜線
    path = os.path.normpath(path)
    # 確保使用正斜線（為了統一性）
    path = path.replace('\\', '/')
    return path

if __name__ == "__main__":
    process_files()