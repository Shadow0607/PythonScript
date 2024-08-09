#!/usr/bin/env python3
# coding:utf-8

import os
import shutil
import time
from typing import Generator
from config_reader import load_NAS_config, load_log_config
from logger import log
from utils import clean_filename, FILE_EXTENSIONS, VIDEO_DIR,mount_NAS,delete_NAS_connect,split_string,db_manager
import platform
import requests
from bs4 import BeautifulSoup
from javdb_scraper import JavdbScraper
from actor_models import create_video_from_dict
config = load_NAS_config()
config_log = load_log_config()

RECORD_TIME = 60* 60 * 10
system = platform.system()
scraper = JavdbScraper()

def logger_message(message):
    log(message, config_log['LOG_FOLDER'], 'move_file')

def get_recent_files(dir_path: str) -> Generator[str, None, None]:
    current_time = time.time()
    delete_mp4 =["台 妹 子 線 上 現 場 直 播 各 式 花 式 表 演.mp4","社 區 最 新 情 報.mp4"]
    for root, _, files in os.walk(dir_path):
        if "@eaDir" in root:
            continue
        for file in files:
            if file == "SYNOVIDEO_VIDEO_SCREENSHOT.jpg":
                continue
            file_path = os.path.join(root, file)
            file_extension = os.path.splitext(file)[1].lower()
            if file_extension not in FILE_EXTENSIONS or file in delete_mp4:
                try:
                    delete_file_or_folder(file_path)
                    logger_message(f"刪除不符合副檔名的檔案: {file_path}")
                except Exception as e:
                    logger_message(f"刪除檔案 {file_path} 失敗: {e}")
                continue
            if (current_time - os.path.getmtime(file_path)) < RECORD_TIME:
                yield file_path

def insert_av_video(id, file_name,magnet):
    video_num, category = split_string(file_name)
    result =0
    try:
        check_result = db_manager.check_and_update_video(id, video_num, category,magnet)
        if check_result:
            existing_video = create_video_from_dict(check_result) 
            new_priority = db_manager.get_category_priority(category)
            existing_priority = db_manager.get_category_priority(existing_video.category)
            logger_message(f"existing_video :{existing_video}，magnet :{magnet}")
            if existing_video.magnet!=magnet and magnet!='N':
                if new_priority > existing_priority:
                    result = db_manager.update_av_video(video_num, id, category)
                    delete_files_with_string(video_num)
                else:
                    logger_message(f"Cannot update '{video_num}'. New category '{category}' does not have higher priority than existing '{existing_video.category}'.")
                    result =2
            else:
                result =3
        else:
            result = db_manager.insert_av_video(id, video_num, category,magnet)
    except Exception as e:
        logger_message(f"Exception :{e}")
        result =0
    return result


def get_video_num_actor_link(video_num):
    video_url = scraper.search_video(video_num)
    if video_url:
        video_info = scraper.get_video_info(video_url)
        if video_info and 'actors' in video_info:
            for actor in video_info['actors']:
                actor_data = db_manager.get_pure_actor_by_dynamic_value('check_ch_name', actor) or db_manager.get_pure_actor_by_dynamic_value('check_jp_name', actor)
                if actor_data:
                    return actor_data
    return None

def compare_and_keep_smaller_file(file_path, new_file_path):
    if os.path.exists(new_file_path):
        # 比較檔案大小
        original_size = os.path.getsize(file_path)
        new_size = os.path.getsize(new_file_path)
        if original_size < new_size:
            os.remove(new_file_path)
            os.rename(file_path, new_file_path)
            logger_message(f"文件已成功重命名為: {new_file_path}")
        elif original_size >new_size:
            logger_message(f"保留較小的新檔案: {new_file_path}")
            os.remove(file_path)
        else:
            logger_message(f"大小一致，保留原始檔案: {file_path}")
            pass
    else:
        logger_message(f"新檔案不存在，直接重命名: {os.path.exists(new_file_path)}")
        os.rename(file_path, new_file_path)
        
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
    new_filename = clean_filename(filename)
    if (last_folder.upper() not in new_filename.upper() and new_filename.upper() not in last_folder.upper())and last_folder != os.path.basename(database_root_path['path']):
        delete_file_or_folder(file_path)
        return

    if not new_filename:
        delete_file_or_folder(file_path)
        logger_message(f"刪除不符合規則的檔案: {file_path}")
        return

    video_num, category = split_string(new_filename)
    path = db_manager.get_actor_by_video_num(video_num) or get_video_num_actor_link(video_num)

    if path:
        result =insert_av_video(path['id'], new_filename, 'N')
        new_file_path = os.path.join(path['path'], f"{new_filename}{file_extension}")
    else:
        new_file_path = os.path.join(directory, f"{new_filename}{file_extension}")

    if system != 'Linux':
        new_file_path = new_file_path.replace('/volume1/video/', 'Y:').replace('/', '\\')

    if new_file_path != file_path:
        try:
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
    for root, dirs, files in os.walk(directory, topdown=True):
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

def delete_files_with_string(target_string):
    try:
        if system != 'Linux':
            mount_NAS()
        for dirpath, dirnames, filenames in os.walk(VIDEO_DIR, topdown=True):
            for filename in filenames:
                if target_string in filename:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        os.remove(file_path)
                        logger_message(f"已刪除: {file_path}")
                    except Exception as e:
                        logger_message(f"無法刪除 {file_path}: {e}")
        if system != 'Linux':
            delete_NAS_connect()
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