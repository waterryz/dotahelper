import requests

def search_internet(query):
    """
    Простая функция, которая делает запрос в DuckDuckGo API
    и возвращает краткий текст.
    """
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1"
    response = requests.get(url)
    data = response.json()
    if data.get("AbstractText"):
        return data["AbstractText"]
    elif data.get("RelatedTopics"):
        for topic in data["RelatedTopics"]:
            if isinstance(topic, dict) and topic.get("Text"):
                return topic["Text"]
    return "Ничего не найдено."
