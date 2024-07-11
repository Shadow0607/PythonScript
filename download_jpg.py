
import os
import time
import datetime
import requests
from bs4 import BeautifulSoup

# 設定根目錄
root_dir = "/volume1/video"

def log(message):
    # 获取当前日期
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    # 构建日志文件名
    log_file = f"/volume1/homes/123123123/Python/log_folder/jpg_{today}.txt"
    log_folder = "/volume1/homes/123123123/Python/log_folder"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    # 检查日志文件是否存在，如果不存在则创建
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            pass
    # 写入日志
    with open(log_file, "a") as f:
        log_entry = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
        f.write(log_entry)

def download_image(img_url, dir_name, file_name_without_ext):
    img_response = requests.get(img_url)
    if img_response.status_code == 200:
        img_path = os.path.join(dir_name, f'{file_name_without_ext}.jpg')
        # 保存圖片到本地
        with open(img_path, 'wb') as img_file:
            img_file.write(img_response.content)
            print(f'圖片下載完成並保存為 {img_path}')
        log(f'圖片下載完成並保存為 {img_path}')
        time.sleep(5)
    else:
        log('Failed to download the image.')
        time.sleep(3)

def download_jpg(jpg_name):
    log(f"Get full file path and name: {jpg_name}")
    dir_name = os.path.dirname(jpg_name)
    file_name = os.path.basename(jpg_name)
    file_name_without_ext = os.path.splitext(file_name)[0]
    print(f'檔名: {file_name_without_ext}')
    parts = file_name_without_ext.split('-')
    result = '-'.join(parts[:2])
    url = f'https://javdb.com/search?q={result}&f=all'
    try:
        response = requests.get(url)
        log(f'URL requested: {url}')
        print(f'路徑: {dir_name}/{result}')
        response.raise_for_status()  # 確認請求成功

        if response.status_code == 200:
            # 使用BeautifulSoup解析HTML内容
            soup = BeautifulSoup(response.content, 'html.parser')
            video_divs = soup.find_all('div', class_='video-title')
            for video_div in video_divs:
                strong_tag = video_div.find('strong')
                if strong_tag and strong_tag.text.strip() == result:  # 確保匹配條件正確
                    cover_div = video_div.find_previous('div', class_='cover')
                    if cover_div:
                        img_tag = cover_div.find('img', {'loading': 'lazy'})
                        if img_tag and 'src' in img_tag.attrs:
                            img_url = img_tag['src']
                            print(f'Image URL: {img_url}')
                            log(f'Image URL: {img_url}')
                            print(f'{file_name_without_ext}.jpg')
                            download_image(img_url, dir_name, file_name_without_ext)
                            return
            log('Image tag not found or no matching video found.')
            time.sleep(5)
        else:
            log(f'Failed to retrieve the webpage. Status code: {response.status_code}')
            time.sleep(5)

    except Exception as e:
        log(f'Error occurred: {e}')
        print(f'Error occurred: {e}')
    # 暫停1秒
    time.sleep(1)


def get_download_list():
    for parent_dir in os.listdir(root_dir):
        parent_path = os.path.join(root_dir, parent_dir)
        if os.path.isdir(parent_path):
            # 获取当前目录下的所有 MP4 文件，并按字母顺序排序
            mp4_files = sorted([filename for filename in os.listdir(parent_path) if filename.lower().endswith(".mp4")])
            # 自定义排序规则：按照文件名的字母顺序，然后按照文件名中的数字大小进行排序
            mp4_files.sort(key=lambda x: (x.split('-')[0], int(''.join(filter(str.isdigit, x)))))
            # 遍历排序后的文件列表
            for filename in mp4_files:
                base_name = os.path.splitext(filename)[0]
                jpg_filename = f"{base_name}.jpg"
                jpg_path = os.path.join(parent_path, jpg_filename)
                mp4_path = os.path.join(parent_path, filename)
                if os.path.exists(jpg_path):
                    pass
                else:
                    download_jpg(jpg_path)

if __name__ == "__main__":
    get_download_list() 