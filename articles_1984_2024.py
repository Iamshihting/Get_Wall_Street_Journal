import requests,json,re,datetime
import cloudscraper
import os, time, random
import openpyxl
from bs4 import BeautifulSoup
from tqdm import tqdm
from dotenv import load_dotenv
from loginC import LoginCookies
from pymongo import MongoClient

start_time = time.time()
client = MongoClient("mongodb://localhost:27017/")
db = client["url_article"]
url_collection = db["get_url"]
article_collection = db["get_articles"]
err_collection = db["Output_Error"]

def main():
    years = url_collection.distinct("year")
    years = [y for y in years if 1984 <= y <= 2024]
    for year in sorted(years): 
        total = url_collection.count_documents({"status": "pending", "year": year})
        filtered_sourse = url_collection.find(
            {"status":"pending", "year": year}, 
            {"_id": 1, "year": 1, "month": 1, "title": 1, "article_url": 1}
        )
        for a in tqdm(filtered_sourse,total=total):
            try:
                content = getArticle(a)
                data ={
                    "year" : a["year"],
                    "month" : a["month"],
                    "title" : a["title"],
                    "content" : content
                }
                article_collection.insert_one(data)
                url_collection.update_one({"_id": a['_id']},{"$set": {"status" : "success"} })
            except Exception as e:
                url_collection.update_one({"_id": a['_id']},{"$set": {"status" : "error", "err_detail" : str(e)} })
                print(f'Error getArticle - {e}')
        crawled_count = url_collection.count_documents({"year": year, "status": "success"})
        print(f"📊 {year} 年共有 {crawled_count} 篇文章爬取成功！")


def retry_requests(url):
    t = 0
    while t <= 1:
        cookies = loginCookies.get_cookies()
        response = scraper.get(
            url,
            cookies=cookies,
            headers=headers,
        )
        if 'prompt_captcha_form' not in response.text:
            return response
        else:
            loginCookies.manual_verification(url, cookies, 60)
        t += 1
        
    raise Exception(f'reCAPTCHA 驗證')
        
def getArticle(article):
    try:
        response = retry_requests(article['article_url'])
        soup = BeautifulSoup(response.text, 'lxml')
        content = '\n'.join([x.text.strip() for x in soup.select('#fullTextZone text p,#readableContent text p')])
        
        if not content:
            raise Exception('無法取得內容')

        return content
        
    except Exception as e:
        raise Exception(f'Error getArticle - {e}')
    
if __name__ == '__main__':    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    }

    load_dotenv()
    USERNAME = os.getenv("NYCU_USERNAME")
    PASSWORD = os.getenv("NYCU_PASSWORD")

    loginCookies = LoginCookies(USERNAME, PASSWORD)

    scraper = cloudscraper.create_scraper()
    main()
    end_time = time.time()
    execution_time = end_time - start_time
    print("程式執行時間：", execution_time, "秒")
