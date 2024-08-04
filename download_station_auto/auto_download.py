import time
from datetime import datetime, date
import requests
from bs4 import BeautifulSoup
from download import DownloadStation, download_specific_files
from logger import log
from config_reader import load_NAS_config, load_log_config
from utils import split_string, clean_filename, db_manager
from javdb_scraper import JavdbScraper
from actor_models import create_video_from_dict
from movefile_v2 import delete_files_with_string
config = load_NAS_config()
config_log = load_log_config()
scraper = JavdbScraper()
def logger_message(message):
    log(message, config_log['LOG_FOLDER'], 'auto_download')

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

def rename_file_by_video_code(file_name, video_code):
    # 將文件名和 video_code 轉換為小寫以進行不區分大小寫的比較
    file_name_lower = file_name.lower()
    video_code_lower = video_code.lower()
    
    # 查找 video_code 在文件名中的位置
    start_index = file_name_lower.find(video_code_lower)
    
    if start_index != -1:
        # 如果找到 video_code，提取它和後面的部分
        end_index = start_index + len(video_code)
        result = file_name[start_index:end_index]
        
        # 檢查是否有緊跟其後的 '-X' 部分
        if end_index < len(file_name) and file_name[end_index] == '-':
            additional_part = file_name[end_index:].split()[0]  # 獲取下一個空格之前的部分
            result += additional_part
        return result
    else:
        # 如果沒有找到 video_code，返回原始的 video_code
        return video_code

def process_and_download_video(actor_data, latest_item, torrent_url):
    ds = DownloadStation()
    try:
        result = insert_av_video(actor_data['id'], latest_item, torrent_url)
        if result == 1:
            logger_message(f"插入或更新成功: {latest_item}")
            ds.login()
            download_specific_files(ds, torrent_url, config['MIN_SIZE'], config['MAX_SIZE'], config['NAS_PATH'])
            ds.clear_completed_tasks()
        elif result == 0:
            logger_message(f"新增失敗: {latest_item}")
        elif result == 2:
            logger_message(f"更新失敗: {latest_item}")
        elif result == 3:
            logger_message(f"更新失敗，連結相同: {latest_item}")
    finally:
        ds.logout()
    
def download_video_link(link, video_code):
    video_info = scraper.get_video_info(link)
    try:
        if video_info and 'actors' in video_info and 'classes' in video_info:
            if 'VR' not in video_info['classes'] and '介紹影片' not in video_info['classes'] and '4小時以上作品' not in video_info['classes']:
                for actor in video_info['actors']:
                    actor_data = db_manager.get_pure_actor_by_dynamic_value('check_ch_name', actor) or db_manager.get_pure_actor_by_dynamic_value('check_jp_name', actor)
                    if actor_data:
                        today_items = video_info['magnet_links']
                        today_items.sort(key=lambda x: x['time'], reverse=True)
                        latest_item = today_items[0]
                        renamed_file = rename_file_by_video_code(latest_item['name'], video_code)
                        clean_name = clean_filename(renamed_file)
                        process_and_download_video(actor_data, clean_name, latest_item['hash'])
                        pass
    except Exception as e:
        logger_message(f'Error occurred: {e}')

def download_javdb_url_link():
    url_links = [
        'https://javdb.com/censored?page={num}',
    ]
    found_links = []
    for url_template in url_links:
        page = 1

        max_pages = 10  # 增加最大頁數，以確保能找到"昨日新種"
        template_links = []
        found_new = False

        while page <= max_pages:
            url = url_template.format(num=page)
            try:
                response = requests.get(url)
                response.raise_for_status()

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    today_new_tags = soup.find_all('span', class_='tag', string='昨日新種')
                    
                    video_links = soup.select('a.box')
                    for link in video_links:
                        href = link.get('href')
                        if href:
                            video_code = link.select_one('div.video-title strong')
                            if video_code:
                                video_code = video_code.text.strip()
                                found_links.append((href, video_code))
                    template_links.append(url)

                    if today_new_tags:
                        found_new = True
                        break
                    
                    page += 1
                else:
                    break
                
            except Exception as e:
                break

    logger_message(f"找到的所有鏈接：{found_links} {template_links}")
    for link, code in found_links:
        download_video_link(link, code)

if __name__ == "__main__":
    download_javdb_url_link()