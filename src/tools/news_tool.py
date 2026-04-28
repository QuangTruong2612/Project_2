from bs4 import BeautifulSoup
import requests
import urllib.parse
from langchain_core.tools import tool
from src.core import supabase
from pydantic import BaseModel, Field
from typing import Optional, Union, List
import dateparser
from datetime import datetime, time

SITE_CONFIGS = {
    'vnexpress.net': {
        'title': 'h1.title-detail',
        'category': 'ul.breadcrumb li:nth-child(2) a',
        'description': 'p.description',
        'content': 'p.Normal',
    },
    'thanhnien.vn': {
        'title': 'h1.detail-title',
        'category': 'div.detail-top div.detail-cate a',
        'description': 'h2.detail-sapo',
        'content': 'div.detail-content p',
    },

    'tuoitre.vn': {
        'title': 'h1.article-title',
        'category': 'nav.breadcrumb a:nth-of-type(2)',
        'description': 'h2.article-sapo',
        'content': 'div.article-content p',
    },

    'dantri.com.vn': {
        'title': 'h1.title-page',
        'category': 'div.breadcrumb a:last-child',
        'description': 'h2.singular-sapo',
        'content': 'div.singular-content p',
    },

    'vietnamnet.vn': {
        'title': 'h1.content-detail-title',
        'category': 'ul.breadcrumb a:last-of-type',
        'description': 'div.content-detail-sapo',
        'content': 'div.content-detail-body p',
    },
    'znews.vn': {
        'title': 'h1.article-title',
        'category': 'ul.breadcrumb li:last-child a',
        'description': 'p.article-summary',
        'content': 'div.article-content p',
    },

    'zingnews.vn': {
        'title': 'h1.article-title',
        'category': 'ul.breadcrumb li:last-child a',
        'description': 'p.article-summary',
        'content': 'div.article-content p',
    },
}



class NewsInput(BaseModel):
    url_news : str = Field(description="Đường dẫn tin tức muốn tóm tắt")



@tool(args_schema=NewsInput)
async def get_news_url(url_news: str)-> dict:
    """
    Lấy tin tức theo url mà người dùng gửi để phục vụ cho việc tóm tắt tin tức
    """
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/'
        }
    news_config = SITE_CONFIGS

    try:
        response = requests.get(url_news, headers=headers, timeout=10)
        response.encoding = 'utf-8' 
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        domain = urllib.parse.urlparse(url_news).netloc
        if domain not in news_config:
            print(f"Domain {domain} not supported.")
            return None
    
        config = news_config[domain]

        # ========== GET TITLE ==========
        title = soup.select_one(config['title']).get_text(strip=True) if soup.select_one(config['title']) else ''

        # ========== GET PUBLISHED DATE ==========
        published_date = soup.select_one(config['published-date']).get_text(strip=True) if soup.select_one(config['published-date']) else ''

        # ========== GET DESCRIPTION ==========
        description_tag = soup.select_one(config['description'])
        description = description_tag.get_text(strip=True) if description_tag else ''

        # ========== GET LOCATION ==========
        if 'location' in config:
            location_tag = soup.select_one(config['location'])
            location = location_tag.get_text(strip=True) if location_tag else ''
            description = description.replace(location, '').strip() if location else description
        else:
            location = ''

        # ========== GET CONTENT (Đã sửa để lấy nhiều thẻ p.Normal) ==========
        content_tags = soup.select(config['content']) # Sử dụng select() thay vì select_one()
        content_text = ""
        if content_tags:
            texts = []
            for tag in content_tags:
                # Xóa các tag rác bên trong mỗi đoạn
                for trash in tag.select('table, figure, div.z-news-mini, .more-news'):
                    trash.decompose()
                
                # Giữ lại text trong thẻ <a>
                for a in tag.find_all('a'):
                    a.unwrap()
                
                texts.append(tag.get_text(strip=True))
            
            # Nối các đoạn văn lại với nhau
            content_text = "\n".join(texts)
        return {
            'title': title,
            'location': location,
            'published_date': published_date,
            'description': description,
            'content': content_text
        }
    except Exception as e:
        print(f"Error crawling {url_news}: {e}")
        return None


