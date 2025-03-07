import requests,json,re,datetime
import cloudscraper
import os
from bs4 import BeautifulSoup
from tqdm import tqdm
from dotenv import load_dotenv
from loginC import LoginCookies
import calendar

def retry_requests(url):
    t = 0
    while t <= 1:
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

def parseList(search_id,year,month):
    url = f'https://www.proquest.com/wallstreetjournal/results/{search_id}/1?accountid=10074'
    response = retry_requests(url)
    soup = BeautifulSoup(response.text, 'lxml')
    nav = soup.select('ul.pagination li')
    end_page = nav[-1].a
    end_page = end_page.get('href')

    response = retry_requests(end_page)
    soup = BeautifulSoup(response.text, 'lxml')
    current_page_element = soup.select_one('span.currentPage')
    current_page = int(current_page_element.text.strip())
    print(current_page)
    articles = []
    for pg in tqdm(range(1, current_page + 1)):
        url = f'https://www.proquest.com/wallstreetjournal/results/{search_id}/{pg}?accountid=10074'
        response = retry_requests(url)
        soup = BeautifulSoup(response.text, 'lxml')
        
        for h in soup.select('.resultHeader'):
            links = h.select('li.badge a')
            articles.append({
                'year':year,
                'month':month,
                'title': h.select_one('div.truncatedResultsTitle').text.strip(),
                'article_url': links[1]['href'],
            })
            
    print(f"{year}年{month}月新增{len(articles)}筆資料")        
    output(articles)
    
    
def output(article_url):
    if os.path.exists('url_1984_2024.json'):
        with open('url_1984_2024.json', 'r', encoding='utf8') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    if isinstance(existing_data, list):
        existing_data.extend(article_url) 
    elif isinstance(existing_data, dict):
        existing_data.update(article_url)
    else:
        raise ValueError("❌ 原始 JSON 資料格式錯誤，請使用字典或列表")

    with open('url_1984_2024.json', 'w', encoding='utf8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

def search_parselist(year,month,day):
    search_id = loginCookies.search(year,months[month],day,True)
    print(day)
    parseList(search_id,year,month)


if __name__ == '__main__':
    load_dotenv()
    USERNAME = os.getenv("NYCU_USERNAME")
    PASSWORD = os.getenv("NYCU_PASSWORD")
    months = {
    1: "JANUARY",
    2: "FEBRUARY",
    3: "MARCH",
    4: "APRIL",
    5: "MAY",
    6: "JUNE",
    7: "JULY",
    8: "AUGUST",
    9: "SEPTEMBER",
    10: "OCTOBER",
    11: "NOVEMBER",
    12: "DECEMBER"
    }
    result_path='url_1984_2024.json'
    loginCookies = LoginCookies(USERNAME, PASSWORD)
    scraper = cloudscraper.create_scraper()
    cookies = loginCookies.get_cookies()
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    }

    start_year = 1984
    start_month = 1

    if os.path.exists(result_path):
        with open(result_path,encoding="utf-8") as file:
            data=json.load(file)
        last_entry = data[-1]
        start_year = last_entry.get("year")
        start_month = last_entry.get("month")
        filtered_data=[entry for entry in data if not (entry['year']==start_year and entry['month']==start_month)]
        with open(result_path,"w") as file:
            json.dump(filtered_data,file,indent=4)

    for year in range(start_year,2025):
        for month in range(start_month,13):
            final_day=calendar.monthrange(year, month)[1]
            if year == 1997:
                search_parselist(year,months[month],15,True)
                search_parselist(year,months[month],final_day,True)
            else:
                search_parselist(year,months[month],final_day,True)
            print(year,month)
        start_month=1