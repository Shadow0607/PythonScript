import requests
from bs4 import BeautifulSoup
import time
from logger import log
from config_reader import load_log_config
from requests.exceptions import RequestException
config_log = load_log_config()

class JavdbScraper:
    BASE_URL = 'https://javdb.com'

    def __init__(self):
        self.session = requests.Session()

    def logger_message(self, message):
        log(message, config_log['LOG_FOLDER'], 'javdb_scraper')

    def get_soup(self, url, max_retries=3, delay=5):
        for attempt in range(max_retries):
            try:
                response = self.session.get(url)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except RequestException as e:
                self.logger_message(f'Error occurred while fetching {url}: {e}')
                if attempt < max_retries - 1:
                    self.logger_message(f'Retrying in {delay} seconds...')
                    time.sleep(delay)
                else:
                    self.logger_message('Max retries reached. Giving up.')
                    return None

    def search_video(self, video_num):
        url = f'{self.BASE_URL}/search?q={video_num}&f=all'
        soup = self.get_soup(url)
        if not soup:
            return None

        video_divs = soup.find_all('div', class_='video-title')
        for video_div in video_divs:
            strong_tag = video_div.find('strong')
            if strong_tag and strong_tag.text.strip() == video_num:
                parent_a = strong_tag.find_parent('a')
                href = parent_a.get('href')
                return href
        return None

    def get_video_info(self, video_url):
        soup = self.get_soup(f'{self.BASE_URL}{video_url}')
        if not soup:
            return None

        info = {}
        
        # 獲取演員信息
        actor_section = soup.find('strong', string='演員:')
        if actor_section:
            value_span = actor_section.find_next_sibling('span', class_='value')
            if value_span:
                info['actors'] = [a.text for a in value_span.find_all('a')]

        # 獲取類別信息
        class_section = soup.find('strong', string='類別:')
        if class_section:
            class_value_span = class_section.find_next_sibling('span', class_='value')
            if class_value_span:
                info['classes'] = [a.text for a in class_value_span.find_all('a')]

        # 獲取磁力鏈接
        items = soup.select('.item.columns')
        info['magnet_links'] = []
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
                        info['magnet_links'].append({
                            'time': time_element.text,
                            'hash': magnet_hash,
                            'name': magnet_name
                        })

        return info

    def get_image_url(self, video_num):
        url = f'{self.BASE_URL}/search?q={video_num}&f=all'
        soup = self.get_soup(url)
        if not soup:
            return None

        video_divs = soup.find_all('div', class_='video-title')
        for video_div in video_divs:
            strong_tag = video_div.find('strong')
            if strong_tag and strong_tag.text.strip() == video_num:
                cover_div = video_div.find_previous('div', class_='cover')
                if cover_div:
                    img_tag = cover_div.find('img', {'loading': 'lazy'})
                    if img_tag and 'src' in img_tag.attrs:
                        return img_tag['src']
        return None