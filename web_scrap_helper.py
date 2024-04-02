import requests
import json
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv

# loading environment variables from the .env file
load_dotenv()

def make_web_scraper_request(url):
    web_scrap_key = os.getenv("WEB_SCRAPER_KEY")
    endpoint = "https://realtime.oxylabs.io/v1/queries"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {web_scrap_key}'
    }
    payload = json.dumps({
        'source': 'universal',
        'url': url,
        'user_agent_type': 'desktop',
        'render': 'html',
        'geo_location': 'Germany',   
        'context': [{'key': 'follow_redirects', "value": True}],
    })
    
    try:
        response = requests.post(endpoint, headers=headers, data=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses
    # Convert response JSON into Python object
        data = response.json()
    # Access the 'content' from the first item in the 'results' list
        #content = data['results'][0]['content'] if data['results'] else None
        #return content
        return data
    except requests.exceptions.HTTPError as errh:
        print("HTTP Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        print("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        print("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        print("Oops: Something Else", err)

    return None

#def process_response(response_str):

    # Преобразование строки ответа в объект Python
    try:
        response = json.loads(response_str)
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
        return None

    if not response:
        print("Ответ от сервера не получен.")
        return None
        
    if response.status_code == 200:
        try:
            data = response.json()
        except ValueError:  # Includes simplejson.errors.JSONDecodeError
            print("Ошибка декодирования JSON")
            return None

        if 'results' not in data:
            print("Отсутствует ключ 'results' в ответе.")
            return None

        extracted_content = []
        for result in data['results']:
            content_html = result.get('content', '')
            if content_html:
                try:
                    soup = BeautifulSoup(content_html, 'html.parser')
                    clean_text = soup.get_text()
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    extracted_content.append(clean_text)
                except Exception as e:
                    print(f"Ошибка обработки HTML: {e}")
        if not extracted_content:
            print("Не удалось извлечь содержимое.")
            return None
        return extracted_content
    else:
        print(f"Ошибка при выполнении запроса: {response.status_code}")
        return None


def process_response(response):



    # Check if response is a string and attempt to parse it as JSON
    if isinstance(response, str):
        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            print("Ошибка при попытке декодировать строку JSON.")
            return None
    elif isinstance(response, dict):
        response_data = response
    else:
        print("Неподдерживаемый тип данных для ответа.")
        return None

    # Proceed with processing response_data as a dictionary
    if 'results' not in response_data:
        print("Отсутствует ключ 'results' в данных ответа.")
        return None
    
    extracted_content = []
    for result in response_data['results']:
        content_html = result.get('content', '')
        if content_html:
            try:
                soup = BeautifulSoup(content_html, 'html.parser')
                clean_text = soup.get_text()
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                extracted_content.append(clean_text)
            except Exception as e:
                print(f"Ошибка обработки HTML: {e}")
    
    if not extracted_content:
        print("Не удалось извлечь содержимое.")
        return None
    
    return extracted_content


def process_response_mistakes(response):
    # Ensure the response is in a usable format
    if isinstance(response, requests.models.Response):
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            print("Failed to decode JSON from response.")
            return None
    elif isinstance(response, str):
        try:
            response_data = json.loads(response)
        except json.JSONDecodeError:
            print("Failed to decode JSON from string.")
            return None
    elif isinstance(response, dict):
        response_data = response
    else:
        print("Unsupported response data type.")
        return None

    # Check if 'results' key exists
    if 'results' not in response_data:
        print("'results' key missing in response data.")
        return None

    extracted_content = []
    for result in response_data['results']:
        # Extract and clean text from HTML content
        content_html = result.get('content', '')
        if content_html:
            try:
                soup = BeautifulSoup(content_html, 'html.parser')
                clean_text = ' '.join(soup.stripped_strings)
                extracted_content.append(clean_text)
            except Exception as e:
                print(f"Error processing HTML content: {e}")
                # Optionally, append raw HTML on error to not lose data
                extracted_content.append(content_html)

    if not extracted_content:
        print("No content extracted.")
        return None

    return ' '.join(extracted_content)