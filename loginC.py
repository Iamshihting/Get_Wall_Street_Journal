from playwright.sync_api import sync_playwright
import requests, json, time, random, re
from random import choice
from io import BytesIO
from PIL import Image
import ddddocr
from tqdm import tqdm
from dotenv import load_dotenv
import os

class LoginCookies:
    DOMAIN = 'https://idm.nycu.ust.edu.tw'
    HDS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    }

    def __init__(self, username, password, cookies=None, cookies_num=1):
        self.username = username
        self.password = password
        self.cookies_num = cookies_num
        self.all_cookies_list = []
        if cookies:
            self.all_cookies_list.append(cookies)
        self.check_cookies_num()
        
    def update_cookies(self, invalid_cookie):
        if invalid_cookie in self.all_cookies_list:
            self.all_cookies_list.remove(invalid_cookie)
            self.check_cookies_num()
        
    def get_cookies(self):
        if self.all_cookies_list == 0:
            self.__login_and_save_cookies(1)
        return choice(self.all_cookies_list)

    def check_cookies_num(self):
        num = self.cookies_num - len(self.all_cookies_list)
        if num > 0:
            self.__login_and_save_cookies(num)

    def __get_security_code(self, src):
        security_code_url = self.DOMAIN + src
        resp = requests.get(security_code_url, headers=self.HDS, stream=True)
        image = Image.open(BytesIO(resp.content))

        ocr = ddddocr.DdddOcr(show_ad=False)
        security_code = ocr.classification(image)
        return security_code

    def __login_and_save_cookies(self, numbers):

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            for n in tqdm(range(numbers)):
                context = browser.new_context()
                context.clear_cookies()
                page = context.new_page()
                page.goto("https://www.proquest.com/wallstreetjournal?accountid=10074")

                page.fill("input#id_username", self.username)
                page.fill("input#id_password", self.password)

                captcha_element = page.query_selector("img#captcha_img") 
                captcha_src = captcha_element.get_attribute("src")
                security_code = self.__get_security_code(captcha_src)
                page.fill("input#checkNum", security_code) 
                page.click("input[type='submit']")
                
                page.wait_for_load_state("networkidle",timeout=60000) 

                cookies = context.cookies() 
                requests_cookies = {cookie['name']: cookie['value'] for cookie in cookies}
                self.all_cookies_list.append(requests_cookies)

                context.close()

            browser.close()
    
    def manual_verification(self, url, cookies, timeout=None):
        """
        使用指定的 cookies 載入網頁(手動驗證用)
        當超出指定的時間未驗證，會直接更新 cookies
        
        param url: str
            網頁網址
        param cookies: dict
            帶有登入資訊的 cookies
        param timeout: int(optional)
            手動驗證的時限(秒)
        """
        playwright_cookies = [
            {
                "name": key,
                "value": value,
                "domain": "www.proquest.com	",
                "path": "/", 
                "secure": False, 
                "httpOnly": False, 
            }
            for key, value in cookies.items()
        ]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
        }
        verified = False
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False) 
            context = browser.new_context()
            context.add_cookies(playwright_cookies)
            context.set_extra_http_headers(headers)
            page = context.new_page()

            page.goto(url) 

            try:
                if timeout:
                    page.wait_for_selector("#documentTitle", timeout=timeout * 1000)
                else:
                    page.wait_for_selector("#documentTitle")
                verified = True
            except Exception as e:
                verified = False

            browser.close()

        if verified:
            pass
        else:
            self.update_cookies(cookies)
    
    def search(self,year,month,day,head):
        search_url = 'https://www.proquest.com/wallstreetjournal/advanced?accountid=10074'
        cookies = self.get_cookies()
        playwright_cookies = [
            {
                "name": key,
                "value": value,
                "domain": "www.proquest.com	",
                "path": "/", 
                "secure": False, 
                "httpOnly": False, 
            }
            for key, value in cookies.items()
        ]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
        }

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=head) 
            context = browser.new_context()
            context.add_cookies(playwright_cookies)
            context.set_extra_http_headers(headers)
            page = context.new_page()
            page.goto(search_url) 

            try:
                page.wait_for_selector('#onetrust-accept-btn-handler', timeout=30000)
                page.click('#onetrust-accept-btn-handler')
            except Exception:
                raise ValueError("未出現 Cookie 同意通知")
            page.select_option('#select_multiDateRange', 'RANGE')
            page.select_option('#month2', str(month))
            page.select_option('#month2_0', str(month))
            page.fill('#year2', str(year))
            page.fill('#year2_0', str(year))
            if year == 1997 and day == 15:
                page.select_option('#day2', '1')
                page.select_option('#day2_0', str(day))
            elif year == 1997 and day != 15:
                page.select_option('#day2', '16')
                page.select_option('#day2_0', str(day))
            else:
                page.select_option('#day2', '1')
                page.select_option('#day2_0', str(day))


            checkbox_selector = 'input[type="checkbox"][id="SourceType_Newspapers"]'

            if page.is_checked(checkbox_selector):
                pass
            else:
                page.click(checkbox_selector)

            page.click('#searchToResultPage')
                
            while True:
                try:
                    current_url = page.evaluate('() => window.location.href')
                    if 'results' in current_url:
                        page.wait_for_load_state("networkidle")
                        break
                except Exception as e:
                    continue
            search_id = re.search('results/(.+?)/', current_url).group(1)

            browser.close()

            data = {
                'itemsPerPage': '100',
            }

            response = requests.post(
                f'https://www.proquest.com/results.selectperpageresults:itemperpageoptionclick/$25PLACEHOLDER$25?site=wallstreetjournal&t:ac={search_id}/1',
                cookies=cookies,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            
        return search_id

if __name__ == "__main__":
    load_dotenv()
    USERNAME = os.getenv("NYCU_USERNAME")
    PASSWORD = os.getenv("NYCU_PASSWORD")
    login_automation = LoginCookies(USERNAME, PASSWORD)

    all_cookies_list = login_automation.all_cookies_list
    with open('cookies.json', 'w', encoding='utf8') as file:
        json.dump(all_cookies_list, file, ensure_ascii=False, indent=4)
