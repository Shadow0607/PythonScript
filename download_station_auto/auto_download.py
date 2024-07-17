import os
import time
from datetime import datetime, date
import requests
from bs4 import BeautifulSoup
import platform
import mysql.connector
import re
from download import DownloadStation, download_specific_files
from logger import log
from database_manager import DatabaseManager
from config_reader import load_NAS_config,load_log_config

db_manager = DatabaseManager()
config = load_NAS_config()
config_log =load_log_config()

connection = None


def logger_message(message):
    log(message,config_log['LOG_FOLDER'], 'auto_download')

connection = None

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
    result = db_manager.insert_av_video(id, video_num, category)
    return result

def clean_filename(filename, video_code):
    # 移除開頭的方括號內容
    filename = re.sub(r'^\[.*?\]', '', filename)
    
    # 尋找影片編號在檔案名中的位置
    code_position = filename.find(video_code)
    
    if code_position != -1:
        # 如果找到影片編號，只保留從編號開始到結尾的部分
        cleaned = filename[code_position:]
        
        # 移除結尾的多餘內容（如 .torrent 或其他）
        cleaned = re.sub(r'\.(?:torrent|mp4|avi|mkv).*$', '', cleaned)
        
        return cleaned.strip()
    else:
        # 如果沒有找到影片編號，返回原始檔名
        return filename.strip()


def download_video_link(link, video_code):
    current_date = date.today()
    child_url = f'https://javdb.com{link}'
    try:
        response = requests.get(child_url)
        response.raise_for_status()

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            actor_section = soup.find('strong', string='演員:')
            if actor_section:
                value_span = actor_section.find_next_sibling('span', class_='value')
                if value_span:
                    actors = [a.text for a in value_span.find_all('a')]
                    for actor in actors:
                        id = db_manager.check_actor_id_exists(actor)
                        logger_message(f"actor:{actor},id:{id}")
                        if id != 0:
                            today_items = []
                            items = soup.select('.item.columns')
                            for item in items:
                                time_element = item.select_one('.time')
                                if time_element:
                                    magnet = item.select_one('a[href^="magnet:?"]')
                                    if magnet:
                                        magnet_link = magnet['href']
                                        magnet_parts = magnet_link.split('&', 1)
                                        if len(magnet_parts) > 1:
                                            magnet_hash = magnet_parts[0]
                                            magnet_name = magnet_parts[1].split('=', 1)[-1]
                                            clean_name = clean_filename(magnet_name, video_code)                         
                                            today_items.append({
                                                'time': datetime.strptime(time_element.text, '%Y-%m-%d'),
                                                'magnet_hash': magnet_hash,
                                                'file_name': clean_name
                                            })
                                    logger_message(f"today_items")
                            
                            if today_items:
                                # 按時間排序，最新的在前
                                today_items.sort(key=lambda x: x['time'], reverse=True)
                                
                                # 只取最新的一筆
                                latest_item = today_items[0]
                                
                                logger_message(f"最新的項目 ({latest_item['time'].date()})：")
                                logger_message(f"時間: {latest_item['time']}")
                                logger_message(f"磁力哈希: {latest_item['magnet_hash']}")
                                logger_message(f"檔案名稱: {latest_item['file_name']}")
                                logger_message("---")
                                
                                torrent_url = latest_item['magnet_hash']
            
                                ds = DownloadStation()
                                try:                                        
                                    result = insert_av_video(id, latest_item['file_name'])
                                    if result == 1:
                                        ds.login()
                                        download_specific_files(ds, torrent_url, config['MIN_SIZE'], config['MAX_SIZE'], config['NAS_PATH'])
                                        ds.clear_completed_tasks()
                                    else:
                                        pass
                                finally:
                                    ds.logout()
                            else:
                                logger_message(f"沒有找到 {current_date} 的項目")
                else:
                    logger_message("未找到演員信息")
            else:
                logger_message("未找到演員部分")
    except Exception as e:
        logger_message(f'Error occurred: {e}')

def download_today_link(page):
    url = page
    found_links = []
    try:
        response = requests.get(url)
        response.raise_for_status()

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            today_new_tags = soup.find_all('span', class_='tag', string='今日新種')
            
            for tag in today_new_tags:
                parent_a = tag.find_parent('a')
                if parent_a:
                    href = parent_a.get('href')
                    if href:
                        # 找到包含影片標題的 div
                        title_div = parent_a.find('div', class_='video-title')
                        if title_div:
                            # 提取 strong 標籤中的文本（影片編號）
                            video_code = title_div.find('strong')
                            if video_code:
                                video_code = video_code.text.strip()
                                found_links.append((href, video_code))
                                logger_message(f"找到的鏈接: {href}, 影片編號: {video_code}")
                            else:
                                found_links.append((href, None))
                                logger_message(f"找到的鏈接: {href}, 未找到影片編號")
                        else:
                            found_links.append((href, None))
                            logger_message(f"找到的鏈接: {href}, 未找到影片標題")
            
            if not found_links:
                logger_message("沒有找到'今日新種'標籤")
            
            logger_message("\n存儲的鏈接數組:")
            
            for link, code in found_links:
                download_video_link(link, code)
    except Exception as e:
        logger_message(f'Error occurred: {e}')

def download_javdb_url_link():
    url_links = [
        'https://javdb.com/censored?page={num}',
        'https://javdb.com/censored?vft={num}'
    ]
    found_links = []

    for url_template in url_links:
        page = 1
        max_pages = 5  # 設置一個最大頁數，以防無限循環

        while page <= max_pages:
            url = url_template.format(num=page)
            try:
                response = requests.get(url)
                response.raise_for_status()

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    today_new_tags = soup.find_all('span', class_='tag', string='昨日新種')
                    found_links.append(url)
                    if today_new_tags:
                        break
                    else:
                        page += 1
                else:
                    logger_message(f"頁面 {url} 請求失敗")
                    break
                
            except Exception as e:
                logger_message(f'Error occurred on page {url}: {e}')
                break

        if found_links:
            # 如果在當前URL模板中找到了符合條件的鏈接，就不再檢查下一個URL模板
            break

    logger_message(f"找到的鏈接：{ found_links}" )
    for page in found_links:
        download_today_link(page)
        time.sleep(10)

    
if __name__ == "__main__":
    download_javdb_url_link()