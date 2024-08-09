#!/usr/bin/env python3
import requests
import os
import time
from bs4 import BeautifulSoup
from utils import clean_filename, VIDEO_DIR,mount_NAS,delete_NAS_connect,split_string
from config_reader import load_NAS_config, load_log_config
from logger import log
from database_manager import DatabaseManager
import platform
from javdb_scraper import JavdbScraper
from actor_models import create_video_from_dict
from movefile_v2 import delete_files_with_string

scraper = JavdbScraper()

config = load_NAS_config()
config_log = load_log_config()
db_manager = DatabaseManager()

def logger_message(message):
    log(message, config_log['LOG_FOLDER'], 'download_jpg')

def insert_av_video(id, path):
    video_num, category = split_string(path)
    result = db_manager.insert_av_video(id, video_num, category)
    return result

def insert_av_video(id, file_name):
    video_num, category = split_string(file_name)
    result =0
    try:
        check_result = db_manager.check_and_update_video(id, video_num, category)
        if check_result:
            existing_video = create_video_from_dict(check_result) 
            new_priority = db_manager.get_category_priority(category)
            existing_priority = db_manager.get_category_priority(existing_video.category)

            if new_priority > existing_priority:
                result = db_manager.update_av_video(video_num, id, category)
                #delete_files_with_string(video_num)
            else:
                logger_message(f"Cannot update '{video_num}'. New category '{category}' does not have higher priority than existing '{existing_video.category}'.")
                result =2
        else:
            result = db_manager.insert_av_video(id, video_num, category)
    except Exception as e:
        logger_message(f"Exception :{e}")
        result =0
    return result

def download_image(img_url, dir_name, file_name_without_ext):
    img_response = requests.get(img_url)
    if img_response.status_code == 200:
        img_path = os.path.join(dir_name, f'{file_name_without_ext}.jpg')
        with open(img_path, 'wb') as img_file:
            img_file.write(img_response.content)
            logger_message(f'圖片下載完成並保存為 {img_path}')
        time.sleep(5)
    else:
        logger_message('Failed to download the image.')
        time.sleep(3)

def download_jpg(jpg_name):
    logger_message(f"Get full file path and name: {jpg_name}")
    dir_name = os.path.dirname(jpg_name)
    file_name = os.path.basename(jpg_name)
    file_name_without_ext = os.path.splitext(file_name)[0]
    logger_message(f'檔名: {file_name_without_ext}')
    
    video_num= clean_filename(file_name)

    parts = video_num.split('-')
    result = '-'.join(parts[:2])

    try:
        img_url = scraper.get_image_url(result)
        if img_url:
            download_image(img_url, dir_name, file_name_without_ext)
        else:
            logger_message('Image not found.')
    except Exception as e:
        logger_message(f'Error occurred: {e}')
    time.sleep(10)

def get_download_list():
    logger_message("DL....")
    system = platform.system()
    if system != 'Linux':
        mount_NAS()
    for parent_dir in os.listdir(VIDEO_DIR):
        parent_path = os.path.join(VIDEO_DIR, parent_dir)
        
        if os.path.isdir(parent_path):
            
            if system != 'Linux':
                parent_path = parent_path.replace('Y:\\\\', '/volume1/video/')
            logger_message(f"Processing path: {parent_path}") 
            actor_data = db_manager.get_pure_actor_by_dynamic_value('check_actor_path', parent_path)
            if actor_data:
                id = actor_data['id']
            else:
                id = 0  # or handle this case as appropriate
            video_data = db_manager.get_pure_video_by_dynamic_value('check_actor_id', id)
            if system != 'Linux':
                parent_path = parent_path.replace('/volume1/video/','Y:\\\\')
            all_files = os.listdir(parent_path)
            if "@eaDir" in parent_path:
                continue
            
            base_names = set(os.path.splitext(f)[0] for f in all_files if not f.lower().endswith('.jpg'))
            video_data_set = preprocess_video_data(video_data)
            for base_name in base_names:
                new_filename = clean_filename(base_name)
                video_num, category = split_string(new_filename)
                if base_name == "SYNOVIDEO_VIDEO_SCREENSHOT":
                    continue
                video_result =check_video_num_exists(video_data_set, id, video_num, category)

                mp4_exists = any(f.lower() == f"{base_name}.mp4".lower() for f in all_files)
                jpg_exists = any(f.lower() == f"{base_name}.jpg".lower() for f in all_files)
                
                jpg_path = os.path.join(parent_path, f"{base_name}.jpg")
                result =0
                if mp4_exists:
                    if not jpg_exists:
                        if id != 0 and not video_result:
                            result = insert_av_video(id, base_name)
                        download_jpg(jpg_path)
                        logger_message(f"Downloaded JPG for: {base_name}")
                    else:
                        if id != 0 and not video_result:
                            result = insert_av_video(id, base_name)
                elif jpg_exists:
                    os.remove(jpg_path)
                    logger_message(f"Deleted JPG without MP4: {jpg_path}")
                    #logger_message(f"Both MP4 and JPG exist for: {base_name}")
                
        
    if system != 'Linux':
        delete_NAS_connect()

def check_video_num_exists(video_data_set, actor_id, target_video_num, target_category):
    return (actor_id, target_video_num.lower(), target_category.lower()) in video_data_set

def preprocess_video_data(video_data):
    return {(video['actor_id'], video['video_num'].lower(), video['category'].lower()) 
            for video in video_data}

if __name__ == "__main__":
    get_download_list()