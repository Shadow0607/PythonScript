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
            actor_section = soup.find('strong', text='演員:')
            if actor_section:
                value_span = actor_section.find_next_sibling('span', class_='value')
                if value_span:
                    actors = [a.text for a in value_span.find_all('a')]
                    for actor in actors:
                        id = db_manager.check_actor_id_exists(actor)
                        if id != 0:
                            today_items = []
                            items = soup.select('.item.columns')
                            for item in items:
                                time_element = item.select_one('.time')
                                if time_element:
                                    item_date = datetime.strptime(time_element.text, '%Y-%m-%d').date()
                                    if item_date == current_date:
                                        magnet = item.select_one('a[href^="magnet:?"]')
                                        if magnet:
                                            magnet_link = magnet['href']
                                            # 拆分磁力連結
                                            magnet_parts = magnet_link.split('&', 1)
                                            if len(magnet_parts) > 1:
                                                magnet_hash = magnet_parts[0]
                                                magnet_name = magnet_parts[1].split('=', 1)[-1]
                                                
                                                # 清理檔案名稱
                                                clean_name = clean_filename(magnet_name, video_code)
                                                
                                                today_items.append({
                                                    'time': time_element.text,
                                                    'magnet_hash': magnet_hash,
                                                    'file_name': clean_name
                                                })
                            
                            if today_items:
                                print(f"當天 ({current_date}) 的項目：")
                                for item in today_items:
                                    print(f"時間: {item['time']}")
                                    print(f"磁力哈希: {item['magnet_hash']}")
                                    print(f"檔案名稱: {item['file_name']}")
                                    print("---")
                                    log(f"磁力哈希: {item['magnet_hash']}",config_log['LOG_FOLDER'], 'auto_download')
                                    torrent_url = item['magnet_hash']
            
                                    ds = DownloadStation()
                                    try:
                                        ds.login()
                                        download_specific_files(ds, torrent_url, config['MIN_SIZE'], config['MAX_SIZE'], config['NAS_PATH'])
                                        ds.clear_completed_tasks()
                                    finally:
                                        ds.logout()
                            else:
                                print(f"沒有找到 {current_date} 的項目")
                else:
                    print("未找到演員信息")
            else:
                print("未找到演員部分")
    except Exception as e:
        log(f'Error occurred: {e}',config_log['LOG_FOLDER'], 'auto_download')

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
                                print(f"找到的鏈接: {href}, 影片編號: {video_code}")
                            else:
                                found_links.append((href, None))
                                print(f"找到的鏈接: {href}, 未找到影片編號")
                        else:
                            found_links.append((href, None))
                            print(f"找到的鏈接: {href}, 未找到影片標題")
            
            if not found_links:
                print("沒有找到'今日新種'標籤")
            
            print("\n存儲的鏈接數組:")
            for link, code in found_links:
                print(f"鏈接: {link}, 影片編號: {code}")
            
            for link, code in found_links:
                download_video_link(link, code)
    except Exception as e:
        log(f'Error occurred: {e}')
        print(f'Error occurred: {e}')

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
                    print(f"頁面 {url} 請求失敗")
                    break
                
            except Exception as e:
                print(f'Error occurred on page {url}: {e}')
                break

        if found_links:
            # 如果在當前URL模板中找到了符合條件的鏈接，就不再檢查下一個URL模板
            break

    print("找到的鏈接：", found_links)
    for page in found_links:
        download_today_link(page)
        time.sleep(10)

    
if __name__ == "__main__":
    download_javdb_url_link()