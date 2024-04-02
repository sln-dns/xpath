
import json 
import openai
import tiktoken
import os
from openai import OpenAI
from dotenv import load_dotenv

#from web_scrap_helper import make_web_scraper_request, process_response


# Загрузка переменных окружения из файла .env
load_dotenv()

def load_template_info(template_name: str):
    with open('prompt_template.json', 'r', encoding='utf-8') as file:
        all_templates = json.load(file)["templates"]
    
    template = all_templates.get(template_name)
    if not template:
        print(f"Шаблон '{template_name}' не найден.")
        return None
    else:
        return template


def num_tokens_from_string(string, encoding_name: str = "cl100k_base") -> int:
    """Returns the number of tokens in a text string based on the specified encoding.
    If the input is not a string, attempts to convert it to a string."""
    # Проверка типа входных данных и преобразование в строку, если это не строка
    if not isinstance(string, str):
        string = str(string)

    try:
        encoding = tiktoken.get_encoding(encoding_name)  # Get encoding details
        num_tokens = len(encoding.encode(string))  # Encode string and count tokens
    except Exception as e:
        print(f"Ошибка при кодировании текста: {e}")
        num_tokens = 0  # Возвращаем 0 токенов в случае ошибки

    return num_tokens

max_tokens = 16000

def split_into_many(text, max_tokens=max_tokens, encoding_name="cl100k_base"):
    sentences = text.split('. ')
    chunks = []
    chunk = []
    tokens_so_far = 0

    for sentence in sentences:
        token_count = num_tokens_from_string(" " + sentence, encoding_name)
        
        if tokens_so_far + token_count > max_tokens:
            chunks.append('. '.join(chunk) + '.')
            chunk = [sentence]
            tokens_so_far = token_count
        elif token_count <= max_tokens:
            chunk.append(sentence)
            tokens_so_far += token_count
        else:
            continue  # Skip sentences that exceed the max_tokens on their own

        # Account for the space added at the beginning
        tokens_so_far += 1

    # Don't forget to add the last chunk
    if chunk:
        chunks.append('. '.join(chunk) + '.')

    return chunks


def make_openai_request(part_prompt, template_name):
    # Загрузка шаблона сообщений из файла
    template = load_template_info(template_name)
    if not template:
        print(f"Шаблон '{template_name}' не найден.")
        return None

    # Проверка, что part_prompt является строкой
    if not isinstance(part_prompt, str) or not part_prompt:
        print("Передан пустой или некорректный текст запроса.")
        return None

    # Создаем новый список сообщений с включением пользовательского ввода
    messages = []
    for message in template:
        # Добавляем все сообщения кроме плейсхолдера для пользователя
        if message["role"] != "user":
            messages.append(message)
        else:
            # Для пользовательского ввода используем part_prompt
            messages.append({"role": "user", "content": part_prompt})

    # Получение API ключа из переменной окружения
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        print("API ключ OpenAI не найден в файле .env")
        return None

    # Создание клиента OpenAI с использованием API ключа
    openai.api_key = api_key

    MODEL = "gpt-3.5-turbo"
    try:
        response = openai.Completion.create(
            engine=MODEL,
            prompt=[msg["content"] for msg in messages],
            max_tokens=50,
            temperature=0.5,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=None
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Ошибка при запросе к OpenAI: {e}")
        return None



def process_large_text(text, template_name):
    # Разбить текст на части с помощью split_into_many
    parts = split_into_many(text)
    
    # Результаты будут сохранены в этом списке
    results = []

    # Проход по каждой части текста
    for part in parts:
        # Создать запрос к OpenAI для каждой части текста
        result = make_openai_request(part, template_name)
        
        # Добавить результат в список
        results.append(result)
    
    # Объединить все элементы списка results обратно в одну строку
    combined_text = " ".join(results)

    # Проверить количество токенов в объединенном тексте
    total_tokens = num_tokens_from_string(combined_text)
    
    # Если количество токенов превышает максимальное
    if total_tokens > 16000:
        # Рекурсивно вызвать эту же функцию снова
        return process_large_text(combined_text, template_name)
    else:
        # Отправить объединенный текст в функцию make_openai_request
        final_result = make_openai_request(combined_text, template_name)
        
        # Вернуть окончательный результат
        return final_result

def process_any_text(any_text, template_name):
    max_tokens = 16000

    total_tokens = num_tokens_from_string(any_text)

    if total_tokens >= max_tokens:
        return process_large_text(any_text, template_name)
    else:
        return make_openai_request(any_text, template_name)
    

def make_openai_request_json(part_prompt, template_name):

    # Загрузка шаблонов сообщений из файла
    with open('prompt_template.json', 'r') as file:
        templates = json.load(file)
    
    # Получение конкретного шаблона сообщений
    messages = templates.get(template_name)
    if messages is None:
        print(f"Шаблон '{template_name}' не найден.")
        return
    
    # Проверьте, что part_prompt является строкой
    if not isinstance(part_prompt, str) or not part_prompt:
        print("Передан пустой или некорректный текст запроса.")
        return None

    # Замена заглушки для пользовательского ввода в последнем сообщении пользователя
    if messages[-1]["role"] == "user":
        messages[-1]["content"] = part_prompt

    # Получение API ключа из переменной окружения
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        print("API ключ OpenAI не найден в файле .env")
        return

    # Создание клиента OpenAI с использованием API ключа
    client = OpenAI(api_key=api_key)

    MODEL = "gpt-3.5-turbo-1106"
    response_format={ "type": "json_object" }
    response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    
    temperature=0,
)

    return response.choices[0].message.content