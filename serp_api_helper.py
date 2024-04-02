import csv
import requests
import os
import json
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()



def make_api_requests(query, domain="com", pages=2, locale="en-EN", **kwargs):
    end_point = 'https://realtime.oxylabs.io/v1/queries'

    serp_api_key = os.getenv("SERP_API_KEY")
    
    
    payload = json.dumps({
            "source": "google_search",
            "domain": domain,
            "query": query,
            "start_page": 1,
            "pages": pages,
            "parse": True,
            "locale": locale,
            "context": [{"key": "results_language", "value": "en"}]
        })
        
    headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {serp_api_key}'
        }

    response = requests.post(end_point, headers=headers, data=payload)

    if response.status_code == 200:
        return response.text
    else:
        print(f"Не удалось получить данные для запроса '{query}'. Код состояния: {response.status_code}")


def extract_urls_from_response(response):
    if response is None:
        return None
    data = json.loads(response)
    
    urls = []
    for result in data['results']:
        if 'organic' in result['content']['results']:
            for organic_result in result['content']['results']['organic']:
                urls.append(organic_result['url'])
    return urls