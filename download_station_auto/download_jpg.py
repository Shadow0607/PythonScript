#!/usr/bin/env python3
import os
import time
import datetime
import requests
from bs4 import BeautifulSoup
import mysql.connector
import re
from config_reader import load_NAS_config,load_log_config,load_MYSQL_config
from logger import log
from database_manager import DatabaseManager
connection = None
config = load_NAS_config()
config_log =load_log_config()

# 設定根目錄
root_dir = config['NAS']['PATH']
db_manager = DatabaseManager()

def logger_message(message):
    log(message,config_log['LOG_FOLDER'], 'download_jpg')

def get_actor_id(path):
    return db_manager.get_actor_id_by_path(path)

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

def insert_av_video(id, path):
    video_num, category = split_string(path)
    db_manager.insert_av_video(id, video_num, category)

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
    parts = file_name_without_ext.split('-')
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
    for parent_dir in os.listdir(root_dir):
        parent_path = os.path.join(root_dir, parent_dir)
        if os.path.isdir(parent_path):
            id = get_actor_id(parent_path)
            logger_message(parent_path)
            mp4_files = sorted([filename for filename in os.listdir(parent_path) if filename.lower().endswith(".mp4")])
            mp4_files.sort(key=lambda x: (x.split('-')[0], int(''.join(filter(str.isdigit, x)))))
            for filename in mp4_files:
                base_name = os.path.splitext(filename)[0]
                jpg_filename = f"{base_name}.jpg"
                jpg_path = os.path.join(parent_path, jpg_filename)
                mp4_path = os.path.join(parent_path, filename)
                if os.path.exists(jpg_path):
                    pass
                else:
                    insert_av_video(id,base_name)
                    download_jpg(jpg_path)
    

if __name__ == "__main__":
    get_download_list()
