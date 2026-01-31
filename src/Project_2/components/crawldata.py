import requests
import time
import random
import pandas as pd
from Project_2.entity.config_entity import CrawlDataConfigure

class CrawlData:
    def __init__(self, config: CrawlDataConfigure):
        self.config = config
        self.headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Referer': config.url
                        }

    def get_product_ids_from_cat(self, cat_id, max_products):
        product_list = []
        page = 1
        seen_ids = set()
        print(f"--- Bắt đầu lấy danh sách sản phẩm từ Category: {cat_id} ---")

        while len(product_list) < max_products:
            url = f"https://tiki.vn/api/personalish/v1/blocks/listings?limit=48&category={cat_id}&page={page}"
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('data', [])
                    if not items:break
                    for item in items:
                        if len(product_list) > max_products:break
                        raw_id = item.get('id')
                        p_id = str(raw_id)

                        # KIỂM TRA TRÙNG LẶP DỰA TRÊN ID
                        # (ID là số nên hash được, không bị lỗi)
                        if p_id in seen_ids:
                            continue

                        seen_ids.add(p_id)
                        product_list.append({
                            'id': raw_id,
                            'name': item.get('name', 'No Name')
                        })
                    print(f"Đã tìm thấy {len(product_list)} sản phẩm (Page {page})")
                    page += 1
                    time.sleep(1)
                else:
                    print(f"Lỗi tải danh mục: {response.status_code}")
                    break
            except Exception as e:
                print(f"Lỗi: {e}")
                break
        return product_list

    def get_comment_from_product_ids(self, product_id, max_comments):
        comment_datas = []
        page = 1

        while len(comment_datas) < max_comments:
            url = f"https://tiki.vn/api/v2/reviews?product_id={product_id}&limit=20&page={page}"
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    reviews = data.get('data', [])
                    if not reviews: break

                    for rev in reviews:
                        if len(comment_datas) > max_comments: break

                        comment_datas.append({
                            "product_id" : product_id,
                            "user_name": rev.get("created_by", {}).get('full_name'),
                            'rating': rev.get('rating'),
                            'content': rev.get('content'),
                            'created_at': rev.get('created_at')
                        })

                    page += 1
                    time.sleep(random.uniform(0.5, 1.5))
                else:
                    break
            except:
                break

        return comment_datas

    def crawldata(self):
        if self.config.use_crawl_data:
            ALL_DATA = []

            for cat_id in self.config.ids_url:
                # Bước 1: Lấy danh sách sản phẩm (Hàm đã sửa)
                products = self.get_product_ids_from_cat(cat_id, self.config.max_products)

                # Bước 2: Lấy comment (Giữ nguyên code cũ)
                for idx, prod in enumerate(products):
                    print(f"[{idx+1}/{len(products)}] Đang cào comment cho ID {prod['id']}: {prod['name'][:30]}...")
                    comments = self.get_comment_from_product_ids(prod['id'], self.config.max_comments)

                    for c in comments:
                        c['product_name'] = prod['name']
                        ALL_DATA.append(c)

            if ALL_DATA:
                df = pd.DataFrame(ALL_DATA)
                df.to_csv(self.config.data_path, index=False)
                print("\nHoàn tất! Kiểm tra file tiki_reviews_8322.csv")
        else:
            print("Not crawl data")
            return
