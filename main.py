from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, constr
import os
import asyncio
from typing import Optional
from fastapi.templating import Jinja2Templates
from openai_helper import process_any_text  # Импортируем вашу функцию
from serp_api_helper import make_api_requests, extract_urls_from_response  # Импортируем вашу функцию
from web_scrap_helper import make_web_scraper_request, process_response  # Импортируем вашу функцию
import json
from openai_helper import split_into_many, num_tokens_from_string
from openai import OpenAI
import asyncio
from worker_web_scrap_async import send_request_and_get_id, get_query_status, get_query_result_content
import aiohttp
import ssl
from bs4 import BeautifulSoup
import re
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

serp_api_key = os.getenv("SERP_API_KEY")

web_scrap_key = os.getenv("WEB_SCRAPER_KEY")

app = FastAPI()

templates = Jinja2Templates(directory="templates")

class Query(BaseModel):
    guiding_question: Optional[str] = None

class SearchQuery(BaseModel):
    query: str

class WebRequest(BaseModel):
    url: str

class TextData(BaseModel):
    text: str    

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Передаём request в шаблон, чтобы можно было использовать его в шаблонах Jinja2
    return templates.TemplateResponse("index.html", {"request": request})


def load_template_info(template_name: str):
    with open('prompt_template.json', 'r', encoding='utf-8') as file:
        all_templates = json.load(file)["templates"]
    
    template = all_templates.get(template_name)
    if not template:
        print(f"Шаблон '{template_name}' не найден.")
        return None
    else:
        return template


@app.post("/gd")
async def generate_search_keywords(query: Query):
    # Проверяем, что вопрос предоставлен
    if not query.guiding_question:
        raise HTTPException(status_code=400, detail="Guiding question is required")
    
    # Очищаем вопрос от символов переноса строки и заменяем их пробелами
    cleaned_question = ' '.join(query.guiding_question.splitlines())

    try:
        
        
        template_name = "generate_words_for_search_competitors"
        
        # Загружаем шаблон из файла
        template = load_template_info(template_name)
        
        # Передаём очищенный вопрос в функцию обработки
        response = process_any_text(cleaned_question, template)
        
        # Предполагаем, что ответ уже в формате списка ключевых слов
        # или адаптируйте следующий шаг в соответствии с вашей логикой обработки ответа
        response
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке запроса: {e}")
    

@app.post("/scrap")
async def scrap_for_urls(search_query: SearchQuery):
    if not search_query.query:
        raise HTTPException(status_code=400, detail="Search query is required.")

    try:
        response_text = make_api_requests(search_query.query)
        urls = extract_urls_from_response(response_text)
        return {"urls": urls}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# Адаптируем синхронные функции для использования в асинхронном контексте
async def async_make_web_scraper_request(url: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, make_web_scraper_request, url)

async def async_process_response(response):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, process_response, response)

async def async_process_any_text(any_text, template_name):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, process_any_text, any_text, template_name)

@app.post("/web")
async def web_scraper_endpoint(web_request: WebRequest):
    # Используй первую функцию для отправки запроса на скрапинг
    scraper_response = make_web_scraper_request(web_request.url)
    
    # Проверь, успешно ли выполнен запрос на скрапинг
    if scraper_response is None:
        raise HTTPException(status_code=500, detail="Ошибка при выполнении запроса на скрапинг")

    # Используй вторую функцию для обработки полученного ответа
    processed_response = process_response(scraper_response)

    # Проверь, успешно ли обработан ответ
    if processed_response is None:
        raise HTTPException(status_code=500, detail="Ошибка при обработке данных скрапинга")

    return {"processed_data": processed_response}




async def process_query_with_delay(query: str):
    await asyncio.sleep(0)  # Задержка на 5 секунд
    return await scrap_for_urls(SearchQuery(query=query))


def process_response(response):
    # Предполагается, что response это строка с HTML-содержимым
    if isinstance(response, str):
        try:
            soup = BeautifulSoup(response, 'html.parser')
            clean_text = soup.get_text()
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            return clean_text
        except Exception as e:
            print(f"Ошибка обработки HTML: {e}")
            return None
    else:
        print("Неподдерживаемый тип данных для ответа.")
        return None


@app.post("/full")
async def process_text(data: TextData):
    # Обработка текста: убираем символы переноса строки и гарантируем, что результат является строкой
    processed_text = ' '.join(data.text.splitlines())

    MAX_TOKENS = 14000

    # Создаем клиента OpenAI с API ключом из переменных окружения
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # Создаем запрос к OpenAI
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Objective: Generate a list of Google search keywords to identify major competitors and evaluate their strategies and channels in a specific market. Context: You're conducting market research in a defined market, aiming to understand competitors, their product features, strategies, and marketing channels. Your research focuses on a market defined by specific characteristics: its name, main advantage, geographical area, and your research aim. Steps to Generate Keywords: Define the Market: Name of the Market: Insert the specific market you're researching (e.g., Bi-Software market). Identify the Main Advantage: Main Advantage: Describe the primary benefit or unique selling proposition of the market (e.g., use AI tools). Specify the Geographical Market: Geographical Market: Mention the geographical scope of your research (e.g., English speaking segment of the internet). Clarify the Aim of the Research: Research Aim: Clearly state what you intend to achieve with the research (e.g., gain a competitive advantage and successfully enter the market with a breakthrough software). Example Research Request: Conduct market research using the benchmarking method in the Bi-Software market, that uses AI tools in the English-speaking segment of the internet to identify major competitors and their products' features and evaluate their strategies and channels, in order to gain a competitive advantage and successfully enter the market with a breakthrough software. Suggested Keywords for Google Search: Bi-Software market competitors AI tools in Bi-Software English speaking Bi-Software market analysis Bi-Software strategies and channels How to enter Bi-Software market Bi-Software market trends 2024 Use these keywords to conduct thorough market research. This will help you understand the market, identify competitors, analyze their products, strategies, and marketing channels, ultimately assisting you in achieving your research objectives. Provide only Keywords without introduction and conclusion, use comma to divide."
                },
                {
                    "role": "user",
                    "content": processed_text
                }
            ]
        )
        
        words_str = chat_completion.choices[0].message.content
        words_list = [word.strip() for word in words_str.split(',')]
        print(words_list)

        # Асинхронная обработка списка словосочетаний с задержкой
        urls_list = await asyncio.gather(*(process_query_with_delay(word) for word in words_list))
        
        # Преобразование списка словарей с URL в один общий список URL
        all_urls = [url for sublist in urls_list for url in sublist["urls"]]
        
        print({"words to search": words_list, "urls": all_urls})

        all_urls = all_urls[:30]                                    # Ограничение на 10 URL

        endpoint = "https://data.oxylabs.io/v1/queries"
        headers = {'Content-Type': 'application/json', 'Authorization': f'Basic {web_scrap_key}'}
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
            tasks = []
            semaphore = asyncio.Semaphore(10)  # Управление количеством одновременных запросов
            
            for url in all_urls:
                task = send_request_and_get_id(session, url, endpoint, headers, semaphore)
                tasks.append(task)

            ids = await asyncio.gather(*tasks)
            url_id_map = {url: id_ for url, id_ in zip(all_urls, ids) if id_}

            contents = []
            for url, id_ in url_id_map.items():
                try:
                    status = await get_query_status(session, id_, endpoint, headers, semaphore)
                    if status == 'done':
                        try:
                            content = await get_query_result_content(session, id_, endpoint, headers, semaphore)
                        except Exception as e:
                            print(f"Произошла ошибка при получении содержимого для ID {id_}: {e}")
                            content = None
                        if content: 
                            contents.append(content)
                    elif status == 'timeout':
                        print(f"Время ожидания истекло для запроса {id_}. Продолжаем с следующим.")
                    elif status == 'error':
                        print(f"Ошибка при обработке запроса {id_}. Продолжаем с следующим.")
                except Exception as e:
                    print(f"Необработанная ошибка при получении статуса для ID {id_}: {e}")

            # Преобразование каждого HTML-ответа в чистый текст
            extracted_texts = list(filter(None, [process_response(content) for content in contents]))

            extracted_texts = extracted_texts[:20]                                   # Ограничение на обработку первых трех элементов списка

            for text in extracted_texts:
                num_tokens = num_tokens_from_string(text)

                if num_tokens > MAX_TOKENS:
                    extracted_texts.remove(text)

            for text in extracted_texts:
                


               # Создаем клиента OpenAI с API ключом из переменных окружения
                client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

                # Создаем запрос к OpenAI
                
                chat_completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                    {
                    "role": "system",
                    "content": "Leverage Your Market Analysis Expertise: With your extensive background in market analysis and research, you are tasked with a critical component of our strategic planning. Dive into the provided dataset, meticulously sifting through to identify and list the names of our product's direct competitors. Your keen eye for detail and unparalleled analytical skills are crucial for accurately pinpointing these competitors. Please present your findings as a straightforward list, focusing solely on the names without any introductory comments or concluding remarks. Your precise extraction will fuel our next steps in navigating the competitive landscape. If you don't have any competitors, please type ' ' "
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )
            
                
                competitors_str = chat_completion.choices[0].message.content
                # Замена символа новой строки на запятую
                competitors_str = competitors_str.replace("\n", ", ")
                # Создание списка, разделяя строку по запятым и удаляя пробелы с обоих концов каждого элемента
                competitors_list = [competitor.strip() for competitor in competitors_str.split(',')]
                print(competitors_list)
                
                result = remove_duplicates(competitors_list)

                return {"competitors": result}
            
            
        
    except Exception as e:
        return {"error": str(e)}


def remove_duplicates(competitors):
    seen = set()
    seen_add = seen.add
    return [x for x in competitors if not (x in seen or seen_add(x))]



async def extract_competitors(data: TextData):
    processed_text = ' '.join(data.text.splitlines())

    total_tokens = num_tokens_from_string(processed_text)

    # Проверяем, превышает ли количество токенов максимально допустимое
    if total_tokens > 16000:
        parts = split_into_many(processed_text)
    else:
        parts = [processed_text]

    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    competitors_list = []

    for part in parts:
        try:
            chat_completion = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Leverage Your Market Analysis Expertise: With your extensive background in market analysis and research, you are tasked with a critical component of our strategic planning. Dive into the provided dataset, meticulously sifting through to identify and list the names of our product's direct competitors. Your keen eye for detail and unparalleled analytical skills are crucial for accurately pinpointing these competitors. Please present your findings as a straightforward list, focusing solely on the names without any introductory comments or concluding remarks. Your precise extraction will fuel our next steps in navigating the competitive landscape. If you don't have any competitors, please type ' ' ",
                    },
                    {
                        "role": "user",
                        "content": part,
                    },
                ],
                temperature=0.0,
            )
            
            # Обработка ответа и извлечение конкурентов из полученного текста
            competitors_str = chat_completion.choices[0].message.content
            
            competitors_list = [competitor.strip() for competitor in competitors_str.split(',') if competitor.strip()]
            return competitors_list
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка при выполнении запроса к OpenAI: {e}")


