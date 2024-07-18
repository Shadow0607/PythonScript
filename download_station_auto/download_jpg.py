#!/usr/bin/env python3
import requests
import os
import time
from bs4 import BeautifulSoup
from utils import process_filename, clean_filename, FILE_EXTENSIONS, VIDEO_DIR
from config_reader import load_NAS_config, load_log_config
from logger import log
from database_manager import DatabaseManager
import platform

config = load_NAS_config()
config_log = load_log_config()
db_manager = DatabaseManager()

def logger_message(message):
    log(message, config_log['LOG_FOLDER'], 'download_jpg')

def get_actor_id(path):
    return db_manager.get_actor_id_by_path(path)

def insert_av_video(id, path):
    video_num, category, _ = process_filename(path)
    result = db_manager.insert_av_video(id, video_num, category)
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
    
    video_num, _, is_valid = process_filename(file_name)
    if not is_valid:
        logger_message(f"Invalid filename: {file_name}")
        return

    parts = video_num.split('-')
    result = '-'.join(parts[:2])
    url = f'https://javdb.com/search?q={result}&f=all'
    try:
        response = requests.get(url)
        logger_message(f'URL requested: {url}')
        logger_message(f'路徑: {dir_name}/{result}')
        response.raise_for_status()
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            video_divs = soup.find_all('div', class_='video-title')
            for video_div in video_divs:
                strong_tag = video_div.find('strong')
                if strong_tag and strong_tag.text.strip() == result:
                    cover_div = video_div.find_previous('div', class_='cover')
                    if cover_div:
                        img_tag = cover_div.find('img', {'loading': 'lazy'})
                        if img_tag and 'src' in img_tag.attrs:
                            img_url = img_tag['src']
                            logger_message(f'Image URL: {img_url}')
                            logger_message(f'{file_name_without_ext}.jpg')
                            download_image(img_url, dir_name, file_name_without_ext)
                            return
            logger_message('Image tag not found or no matching video found.')
            time.sleep(5)
        else:
            logger_message(f'Failed to retrieve the webpage. Status code: {response.status_code}')
            time.sleep(5)
    except Exception as e:
        logger_message(f'Error occurred: {e}')
    time.sleep(1)

def get_download_list():
    logger_message("DL....")
    
    for parent_dir in os.listdir(VIDEO_DIR):
        parent_path = os.path.join(VIDEO_DIR, parent_dir)
        
        if os.path.isdir(parent_path):
            system = platform.system()
            if system != 'Linux':
                parent_path = parent_path.replace('Y:\\\\', '/volume1/video/')
            logger_message(f"Processing path: {parent_path}") 
            actor_data = db_manager.get_pure_actor_by_dynamic_value('chech_actor_path', parent_path)
            if actor_data:
                id = actor_data['id']
            else:
                id = 0  # or handle this case as appropriate
            logger_message(parent_path)
            if system != 'Linux':
                parent_path = parent_path.replace('/volume1/video/','Y:\\\\')
            all_files = os.listdir(parent_path)
            if "@eaDir" in parent_path:
                continue
            
            base_names = set(os.path.splitext(f)[0] for f in all_files)
            
            for base_name in base_names:
                video_num, category, is_valid = process_filename(base_name + ".mp4")
                if not is_valid:
                    logger_message(f"Skipping invalid filename: {base_name}")
                    continue
                if base_name == "SYNOVIDEO_VIDEO_SCREENSHOT":
                    continue
                
                mp4_exists = any(f.lower() == f"{base_name}.mp4".lower() for f in all_files)
                jpg_exists = any(f.lower() == f"{base_name}.jpg".lower() for f in all_files)
                
                mp4_path = os.path.join(parent_path, f"{base_name}.mp4")
                jpg_path = os.path.join(parent_path, f"{base_name}.jpg")
                
                if mp4_exists and not jpg_exists:
                    if id != 0:
                        result = insert_av_video(id, base_name)
                    download_jpg(jpg_path)
                    logger_message(f"Downloaded JPG for: {base_name}")
                
                elif jpg_exists and not mp4_exists:
                    os.remove(jpg_path)
                    logger_message(f"Deleted JPG without MP4: {jpg_path}")
                
                elif mp4_exists and jpg_exists:
                    if id != 0:
                        result = insert_av_video(id, base_name)
                    logger_message(f"Both MP4 and JPG exist for: {base_name}")
                
                else:
                    logger_message(f"Neither MP4 nor JPG exist for: {base_name}")

if __name__ == "__main__":
    get_download_list()