# -*- coding: utf-8 -*-
import os
import argparse
import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import yt_dlp

# 設置最大重試次數和最大失敗次數
MAX_RETRIES = 3
MAX_FAILURES = 3

def check_or_create_database():
    db_path = 'database.txt'
    if not os.path.exists(db_path):
        # 如果文件不存在，創建一個空白文件
        with open(db_path, 'w') as db:
            pass  # 空文件
    return db_path

def get_existing_mp4_files(save_path):
    mp4_files = [f for f in os.listdir(save_path) if f.endswith('.mp4')]
    return mp4_files

def update_database(video_url, video_id, video_title, save_path, download_status):
    db_path = check_or_create_database()
    existing_files = get_existing_mp4_files(save_path)
    
    # 檢查標題是否與現有的 .mp4 文件匹配
    match_found = any(video_title in f for f in existing_files)
    
    # 根據條件更新狀態
    if download_status == 'error':
        status = 'E'
    elif match_found:
        status = 'Y' if '#李雅英' in video_title or '@yyyoungggggg' in video_title else 'D'
    else:
        status = 'N' if '#李雅英' in video_title or '@yyyoungggggg' in video_title else 'D'
    
    # 將結果寫入 database.txt
    with open(db_path, 'a') as db:
        db.write(f"{video_url},{video_id},{status}\n")

def get_videos_to_download():
    db_path = check_or_create_database()
    videos_to_download = []
    
    with open(db_path, 'r') as db:
        lines = db.readlines()
        for line in lines:
            video_url, video_id, status = line.strip().split(',')
            if status in ['N', 'E']:
                videos_to_download.append((video_url, video_id))
    
    return videos_to_download

def setup_webdriver():
    # 設置瀏覽器選項
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 無頭模式，不打開瀏覽器界面
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    # 指定當前目錄下的 ChromeDriver 路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    chromedriver_path = os.path.join(current_dir, 'chromedriver.exe')
    
    service = Service(chromedriver_path)

    # 初始化 Chrome WebDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# 添加重試機制的函數，帶有最大重試次數
def extract_video_info_with_retry(ydl, video_url, retries=MAX_RETRIES):
    attempt = 0
    video_info = None
    
    while attempt < retries:
        try:
            # 嘗試獲取視頻信息
            video_info = ydl.extract_info(video_url, download=False)
            if video_info:
                return video_info  # 成功獲取視頻信息，直接返回
        except yt_dlp.utils.DownloadError as e:
            error_message = str(e)
            if "Video unavailable" in error_message or "This content isn't available" in error_message:
                print(f"視頻 {video_url} 不可用，嘗試第 {attempt + 1} 次")
            else:
                print(f"獲取視頻 {video_url} 信息時發生錯誤：{e}")
            
            attempt += 1
            if attempt < retries:
                print(f"正在重試（第 {attempt}/{retries} 次）...")
                time.sleep(2 * attempt)  # 每次重試時等待時間增加
            else:
                print(f"多次嘗試後仍無法獲取視頻 {video_url} 的信息，標記為失敗並記錄。")
                return None  # 多次失敗返回 None
    return video_info



def get_video_urls(channel_url, driver):
    driver.get(channel_url)
    time.sleep(5)  # 等待頁面加載完畢

    # 滾動頁面以加載更多視頻
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(5)  # 等待新的內容加載
        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    video_urls = set()

    # 獲取 Shorts 視頻鏈接
    shorts_elements = driver.find_elements('xpath', '//a[contains(@class, "reel-item-endpoint")]')
    for elem in shorts_elements:
        href = elem.get_attribute('href')
        if href and '/shorts/' in href:
            if 'https' not in href:
                full_url = f"https://www.youtube.com{href}"
            else:
                full_url = href
            video_urls.add(full_url)

    # 獲取普通視頻鏈接
    video_elements = driver.find_elements('xpath', '//a[@id="thumbnail"]')
    for elem in video_elements:
        href = elem.get_attribute('href')
        if href and 'watch' in href:
            if 'https' not in href:
                full_url = f"https://www.youtube.com{href}"
            else:
                full_url = href
            video_urls.add(full_url)

    return list(video_urls)

def main():
    parser = argparse.ArgumentParser(description='從YouTube頻道下載包含特定關鍵字的視頻。')
    parser.add_argument('--save-path', type=str, default='videos', help='指定視頻保存路徑。')
    args = parser.parse_args()
    save_path = r"C:\Users\123\Desktop\YouTube下载"

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # 檢查和更新暫時性資料庫
    db_path = 'database.txt'
    if not os.path.exists(db_path):
        with open(db_path, 'w') as db:
            pass  # 創建一個空白的暫時性資料庫

    # 測試頻道的URL
    channel_urls = [
        'https://www.youtube.com/@cheng.han_ayoung/shorts',
        'https://www.youtube.com/@cheng.han_ayoung/videos'
    ]

    ydl_opts_download = {
        'format': 'bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'embedsubtitles': True,
        'subtitleslangs': ['zh-Hant'],
        'writesubtitles': True,
        'writeautomaticsub': True,
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'EmbedThumbnail'},
            {'key': 'FFmpegMetadata'},
            {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            },
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'aac',
                'preferredquality': '192',
            },
        ],
        'paths': {'home': save_path},
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
    }

    driver = setup_webdriver()

    try:
        existing_files = get_existing_mp4_files(save_path)
        all_video_urls = []
        for channel_url in channel_urls:
            print(f'正在獲取頻道 {channel_url} 的視頻鏈接...')
            video_urls = get_video_urls(channel_url, driver)
            all_video_urls.extend(video_urls)
            print(f'獲取到 {len(video_urls)} 個視頻鏈接。')

        print('開始過濾包含指定關鍵字的視頻...')

        
        videos_to_download = []

        with yt_dlp.YoutubeDL({'ignoreerrors': True, 'quiet': True}) as ydl:
            for video_url in all_video_urls:
                try:
                    if 'watch?v=' in video_url:
                        video_id = video_url.split('watch?v=')[-1]
                    elif 'shorts/' in video_url:
                        video_id = video_url.split('shorts/')[-1]
                    else:
                        continue

                    video_info = extract_video_info_with_retry(ydl, video_url)

                    if not video_info:
                        # 無法獲取視頻信息，記錄為錯誤
                        with open(db_path, 'a') as db:
                            db.write(f"{video_url},{video_id},E\n")
                        print(f'無法獲取視頻 {video_url} 的信息，加入錯誤列表。')
                        continue

                    video_title = video_info.get('title', '').strip()

                    # 檢查文件是否已經存在
                    match_found = any(video_title in f for f in existing_files)

                    if match_found:
                        # 如果文件已經存在，標記為 Y
                        with open(db_path, 'a') as db:
                            db.write(f"{video_url},{video_id},Y\n")
                        print(f'視頻 {video_title} 已經存在，跳過下載。')
                    else:
                        # 檢查是否包含關鍵字
                        if re.search(r'(#李雅英|@yyyoungggggg)', video_title):
                            with open(db_path, 'a') as db:
                                db.write(f"{video_url},{video_id},N\n")
                            print(f'含有關鍵字 {video_title}，加入下載列表。')
                        else:
                            with open(db_path, 'a') as db:
                                db.write(f"{video_url},{video_id},D\n")
                            print(f'不含關鍵字 {video_title}，跳過下載。')

                except Exception as e:
                    print(f'獲取視頻 {video_url} 信息時出錯：{e}')
                    with open(db_path, 'a') as db:
                        db.write(f"{video_url},{video_id},E\n")

        # 從資料庫中篩選出需要下載的視頻
        videos_to_download = get_videos_to_download()

        print('開始下載視頻...')
        with yt_dlp.YoutubeDL(ydl_opts_download) as ydl_download:
            for video_url, video_id in videos_to_download:
                try:
                    print(f'正在下載視頻 {video_url}...')
                    ydl_download.download([video_url])
                    # 下載成功後更新為 Y
                    with open(db_path, 'a') as db:
                        db.write(f"{video_url},{video_id},Y\n")
                except Exception as e:
                    print(f'下載視頻 {video_url} 時出錯：{e}')
                    # 如果下載失敗，標記為 E
                    with open(db_path, 'a') as db:
                        db.write(f"{video_url},{video_id},E\n")

    finally:
        driver.quit()


if __name__ == '__main__':
    main() 