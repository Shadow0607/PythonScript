import os
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time

# 創作者的 Shorts 和 Videos 頻道 URL 列表
shorts_urls_list = [
    'https://www.youtube.com/@yyyoungggggg/shorts'
]
videos_urls_list = [
    'https://www.youtube.com/@limyoona__official/videos'
]

# 指定下載目標路徑
download_path = r'C:\Users\GP66\Desktop\下載影片\\'  # 使用原始字串並確保以雙反斜線結尾

def load_cookies(driver, cookies):
    for cookie in cookies:
        cookie_dict = {
            'name': cookie['name'],
            'value': cookie['value'],
            'domain': cookie['domain'],
            'path': cookie['path']
        }
        if 'expiry' in cookie:
            cookie_dict['expiry'] = cookie['expiry']
        driver.add_cookie(cookie_dict)

def get_video_urls(url_list, video_type):
    all_video_urls = set()  # 使用集合以排除重複值

    # 使用 WebDriver Manager 安裝並啟動 ChromeDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    for url in url_list:
        driver.get('https://www.youtube.com')
        
        # 刷新頁面，以應用 Cookies
        driver.refresh()
        time.sleep(2)

        driver.get(url)
        
        # 模擬滾動，直到加載所有影片
        SCROLL_PAUSE_TIME = 2
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        
        while True:
            # 滾動到底部
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            
            # 等待新內容加載
            time.sleep(SCROLL_PAUSE_TIME)
            
            # 記錄滾動後的新高度，並檢查是否已達到頁面底部
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        # 獲取所有影片 URL
        a_tags = driver.find_elements(By.TAG_NAME, 'a')
        for a_tag in a_tags:
            href = a_tag.get_attribute('href')
            if href and f'/{video_type}/' in href and video_type == 'shorts':
                all_video_urls.add(href)
            elif href:
                all_video_urls.add(href)

    driver.quit()
    return list(all_video_urls)  # 將集合轉換為列表以返回

def download_videos(video_urls, download_path):
    for video_url in video_urls:
        command = f'yt-dlp "{video_url}" -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o "{download_path}%(title)s.%(ext)s" --write-thumbnail --write-subs --sub-langs zh --convert-sub srt --convert-thumbnail jpg'
        try:
            # Run the command
            subprocess.run(command, shell=True, check=True)
            print(f"Video downloaded successfully from {video_url}.")
        except subprocess.CalledProcessError as e:
            print(f"Error downloading video from {video_url}: {e}")

# 獲取 Shorts URL 並下載
shorts_urls = get_video_urls(shorts_urls_list, 'shorts')
# 獲取普通影片 URL 並下載
videos_urls = get_video_urls(videos_urls_list, 'videos')

# 確保下載目標目錄存在
os.makedirs(download_path, exist_ok=True)

# 下載所有 Shorts 和普通影片
# download_videos(shorts_urls, download_path)
download_videos(videos_urls, download_path)
