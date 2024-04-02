import aiohttp
import asyncio
import csv
import json
import time
import ssl
import os
from dotenv import load_dotenv

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Загрузка переменных окружения из файла .env
load_dotenv()

async def send_request_and_get_id(session, url, endpoint, headers, semaphore):
    worker_web_scrap_key = os.getenv("WORKER_API_KEY")
    async with semaphore:
        payload = json.dumps({
            "source": "universal",
            "url": url,
            "user_agent_type": "desktop",
            "geo_location": "Germany",
            "context": [
                {"key": "follow_redirects", "value": True},
                {"key": "http_method", "value": "get"},
                {"key": "content", "value": "YmFzZTY0RW5jb2RlZFBPU1RCb2R5"},
                {"key": "successful_status_codes", "value": [808, 909]}
            ]
        })
        async with session.post(endpoint, headers=headers, data=payload) as response:
            if response.status in [200, 202]:
                response_data = await response.json()
                return response_data['id']
            else:
                print(f"Ошибка при отправке запроса: {response.status}")
                return None

async def get_query_status(session, query_id, endpoint, headers, semaphore, timeout=40):
    async with semaphore:
        start_time = time.time()
        while True:
            async with session.get(f'{endpoint}/{query_id}', headers=headers) as response:
                if response.status == 200:
                    response_data = await response.json()
                    status = response_data.get("status", "unknown")
                    if status == "done":
                        return status
                    elif time.time() - start_time > timeout:
                        print(f"Время ожидания истекло для запроса: {query_id}")
                        return "timeout"
                else:
                    print(f"Ошибка при получении статуса: {response.status} для запроса: {query_id}")
                    return "error"
            await asyncio.sleep(5)

async def get_query_result_content(session, query_id, endpoint, headers, semaphore):
    async with semaphore:
        async with session.get(f'{endpoint}/{query_id}/results?type=raw', headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data['results']:
                    return data['results'][0]['content']
                else:
                    print("Результаты отсутствуют")
                    return None
            else:
                print(f"Ошибка при получении результатов: {response.status}")
                return None





async def main():
    web_scrap_key = os.getenv("WEB_SCRAPER_KEY")
    endpoint = "https://data.oxylabs.io/v1/queries"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Basic {web_scrap_key}'}
    urls = []

    # Чтение URL из файла
    with open('filtered_output.csv', 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            urls.append(row[0])

    semaphore = asyncio.Semaphore(99)
    total_urls = len(urls)
    processed_count = 0

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:

        tasks = [send_request_and_get_id(session, url, endpoint, headers, semaphore) for url in urls]
        ids = await asyncio.gather(*tasks)
        url_id_map = {url: _id for url, _id in zip(urls, ids) if _id}

        results = {}

        for url, _id in url_id_map.items():
            processed_count += 1
            print(f"Обрабатывается {processed_count}/{total_urls}: URL: {url}")
            status = await get_query_status(session, _id, endpoint, headers, semaphore)
            if status == 'done':
                content = await get_query_result_content(session, _id, endpoint, headers, semaphore)
                if content:
                    results[url] = content
                    print(f"Для URL: {url} данные успешно получены.")
                else:
                    print(f"Для URL: {url} данные не найдены.")

        print("Все запросы обработаны.")

        if results:
            with open('results.json', 'w') as jsonfile:
                json.dump(results, jsonfile)
            print("Результаты сохранены в results.json")
        else:
            print("Результаты отсутствуют, файл не создан")


if __name__ == "__main__":
    asyncio.run(main())
