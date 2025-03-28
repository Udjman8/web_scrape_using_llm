
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import random
import google.generativeai as genai
from google.api_core.exceptions import TooManyRequests
import os
import dotenv
 
urls = [
    "https://www.ge.com", "https://about.facebook.com", "https://www.jnj.com",
    "https://us.pg.com", "https://www.chevron.com", "https://www.intel.com",
    "https://www.coca-colacompany.com", "https://corporate.walmart.com",
    "https://www.airbus.com", "https://www.pepsico.com"
]
 

options = Options()
options.add_argument("--headless")  
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("start-maximized")
options.add_argument("disable-infobars")
options.add_argument("--disable-dev-shm-usage")
options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(80, 100)}.0.3987.106 Safari/537.36")
 

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
 

def fetch_content(url):
    try:
        print(f"Scraping {url}...")
        driver.get(url)
 
      
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
 
       
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 4)) 
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
 
        try:
            load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'Load More')]")
            for button in load_more_buttons:
                driver.execute_script("arguments[0].click();", button)
                time.sleep(random.uniform(2, 4))
        except:
            pass  
 
        return driver.page_source
 
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
 

def clean_data(soup):
    for script in soup(['script', 'style']):
        script.decompose()
    return soup.get_text(separator=' ', strip=True)
 
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY")
dotenv.load_dotenv()
genai.configure(api_key=GEMINI_API_KEY, transport="rest")
 
def call_gemini_api(prompt):
    model = genai.GenerativeModel("gemini-2.0-flash")
 
    for attempt in range(5):  # Retry up to 5 times
        try:
            response = model.generate_content(prompt)
            return response.text if response else ""
        except TooManyRequests:
            print("Rate limit exceeded. Retrying in 60 seconds...")
            time.sleep(60)
 
    return "Error: API Rate Limit Exceeded"
 

def extract_information_with_gemini(cleaned_text):
    pre_prompt = """
    Extract the following company details from the given text. If any information is missing, explicitly state "Not Provided":
    1. Company mission statement or core values
    2. Products or services offered
    3. Founding date and founders
    4. Company headquarters location
    5. Key executives or leadership team
    6. Notable awards or recognitions
 
    Text: {cleaned_text}
    """
    prompt = pre_prompt.format(cleaned_text=cleaned_text)
    return call_gemini_api(prompt)
 
# ✅ Function to extract relevant links (like "About Us")
def extract_relevant_links(soup, base_url):
    keywords = [ "about", "company", "mission", "values", "ethics", "leadership", "management",
    "team", "founders", "history", "executive", "awards", "recognition", "vision",
    "principles", "board", "governance", "corporate", "innovation", "culture",
    "supplier", "location", "headquarters", "heritage", "about-us", "our-company","linkedin",
    "company-overview", "company-profile", "who-we-are", "mission-statement"]
    links = []
   
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(keyword in href for keyword in keywords):
            full_link = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
            links.append(full_link)
 
    return list(set(links))
 
# ✅ Function to get complete information, checking additional pages if needed
def get_complete_information(url):
    page_source = fetch_content(url)
    if not page_source:
        return "Error: Unable to fetch data"
 
    soup = BeautifulSoup(page_source, 'html.parser')
    cleaned_text = clean_data(soup)
    extracted_info = extract_information_with_gemini(cleaned_text)
 
    # If key details are missing, scrape additional "About Us" links
    if "not provided" in extracted_info.lower():
        additional_links = extract_relevant_links(soup, url)
        for link in additional_links:
            print(f"Scraping additional page: {link}")
            page_source = fetch_content(link)
            if not page_source:
                continue
 
            soup = BeautifulSoup(page_source, 'html.parser')
            cleaned_text += "\n" + clean_data(soup)
            extracted_info = extract_information_with_gemini(cleaned_text)
 
            if "not provided" not in extracted_info.lower():
                break  # Stop if sufficient info is found
 
    return extracted_info
 

def save_to_csv(data, filename="company_details.csv"):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Data saved to {filename}")
 

def process_urls(urls):
    all_extracted_data = []
 
    for url in urls:
        extracted_info = get_complete_information(url)
        all_extracted_data.append({"URL": url, "Extracted Info": extracted_info})
        time.sleep(random.uniform(5, 10))  # Add delay between requests
 
    save_to_csv(all_extracted_data)
 

process_urls(urls)
 

driver.quit()
 