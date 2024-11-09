import re
import requests
from bs4 import BeautifulSoup
import pymongo
from transformers import pipeline
from datetime import datetime

# Set up the sentiment analysis pipeline from Hugging Face
sentiment_analyzer = pipeline("sentiment-analysis")

# Global variable to hold the current unique id counter
unique_id_counter = 0

def extract_news(url, keywords, max_articles=100, article_elements=None, class_name=None, title_tag=None, description_tag=None, date_tag=None, date_class=None):
    """
    Extracts news articles with specified keywords from a given URL.

    Args:
        url (str): The URL of the news website.
        keywords (dict): A dictionary mapping category names to lists of keywords.
        max_articles (int, optional): The maximum number of articles to extract. Defaults to 100.
        article_elements (str, optional): The HTML tag(s) for article elements. Defaults to None.
        class_name (str, optional): The class name of article elements. Defaults to None.
        title_tag (str, optional): The HTML tag for title elements. Defaults to None.
        description_tag (str, optional): The HTML tag for description elements. Defaults to None.
        date_tag (str, optional): The HTML tag for date elements. Defaults to None.
        date_class (str, optional): The class name of date elements. Defaults to None.

    Returns:
        list: A list of dictionaries containing extracted news data.
    """
    global unique_id_counter
    articles = []
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    if article_elements is None or class_name is None or date_tag is None:
        raise ValueError("Article elements, class name, and date tag must be provided.")

    article_elements = soup.find_all(article_elements)[:max_articles]

    for article in article_elements:
        title_element = article.find(title_tag, class_=class_name)
        if not title_element:
            continue

        title_text = title_element.text.strip()
        for category, category_keywords in keywords.items():
            if any(keyword.lower() in title_text.lower() for keyword in category_keywords):
                description_element = article.find(description_tag)
                description = description_element.text.strip() if description_element else ''

                # Use system date as the article's date
                date_time = get_system_date()

                source_url = url
                source_name = url.split('/')[2]

                # Sentiment analysis: Combine Title and Description for sentiment calculation
                combined_text = title_text + " " + description
                sentiment = get_sentiment(combined_text)

                unique_id_counter += 1

                articles.append({
                    'id': unique_id_counter,
                    'Title': title_text,
                    'Description': description,
                    'Date': date_time,
                    'Source': source_name,
                    'Source URL': source_url,
                    'Category': category,
                    'Sentiment': sentiment
                })
                break

    return articles

def get_sentiment(text):
    """
    Get sentiment of a given text using Hugging Face's sentiment analysis pipeline.
    Sentiment can be positive, negative, or neutral.

    Args:
        text (str): The text to analyze.

    Returns:
        str: The sentiment of the text.
    """
    result = sentiment_analyzer(text)
    label = result[0]['label']
    if label == 'POSITIVE':
        return 'positive'
    elif label == 'NEGATIVE':
        return 'negative'
    else:
        return 'neutral'

def get_system_date():
    """
    Get the current system date in the format 'Month Day, Year'.
    
    Returns:
        str: The current system date in the format 'Month Day, Year'.
    """
    return datetime.now().strftime("%B %d, %Y")

def save_to_mongo(data, db_url="mongodb+srv://saifurrehman17092002:LM2LIyZIE8fRWlkS@cryptocluster.teapybj.mongodb.net/?retryWrites=true&w=majority&appName=CryptoCluster"):
    """
    Saves the extracted news data into MongoDB, avoiding duplicate IDs.
    """
    global unique_id_counter

    client = pymongo.MongoClient(db_url)
    db = client.get_database('test')  # Use 'test' database
    collection = db.get_collection('news')  # Get 'news' collection

    # Check if the collection already exists, if not, MongoDB will create it automatically
    # We will now insert data only if the article ID doesn't exist in the collection
    existing_ids = {doc['id'] for doc in collection.find({'id': {'$in': [article['id'] for article in data]}})}

    # Filter out the articles with existing IDs
    new_articles = [article for article in data if article['id'] not in existing_ids]

    if new_articles:
        collection.insert_many(new_articles)  # Insert only the new articles
        print(f"Inserted {len(new_articles)} new articles into MongoDB.")
    else:
        print("No new articles to insert. All articles were already present.")

    # Update the unique_id_counter in MongoDB (this could be in a separate collection or document)
    max_id_doc = collection.find_one({}, sort=[("id", pymongo.DESCENDING)])
    if max_id_doc:
        unique_id_counter = max_id_doc['id']
    else:
        unique_id_counter = 0  # Initialize if the collection is empty

if __name__ == '__main__':
    keywords = {
        'BTC': ['BTC', 'Bitcoin', 'Bitcoin Core', 'Digital Gold', 'Cryptocurrency'],
        'ETH': ['ETH', 'Ethereum', 'Smart Contracts', 'Decentralized Finance'],
        'SOL': ['SOL', 'Solana', 'Web3', 'Scalability'],
        'BNB': ['BNB', 'Binance Coin', 'Binance Smart Chain', 'DeFi'],
        'DOGE': ['DOGE', 'Dogecoin', 'Meme Coin', 'Shiba Inu']
    }

    urls = [
        {"url": "https://www.newsbtc.com/news/", "article_elements": "article", "class_name": "block-article__title", "title_tag": "h4", "description_tag": "p", "date_tag": "span", "date_class": "block-article__author"},
        {"url": "https://cryptopotato.com/crypto-news/", "article_elements": "article", "class_name": "rpwe-title", "title_tag": "h3", "description_tag": "p", "date_tag": "time", "date_class": "entry-date"},
        {"url": "https://cryptobriefing.com/news/", "article_elements": "section", "class_name": "main-news-title", "title_tag": "h2", "description_tag": "p", "date_tag": "time", "date_class": "entry-date"},
    ]

    all_articles = []
    for entry in urls:
        extracted_articles = extract_news(
            entry["url"], keywords, article_elements=entry["article_elements"], class_name=entry["class_name"],
            title_tag=entry["title_tag"], description_tag=entry["description_tag"], date_tag=entry["date_tag"], date_class=entry["date_class"]
        )
        all_articles.extend(extracted_articles)
        print(f"Extracted {len(extracted_articles)} articles from {entry['url']}.")

    # Save all articles to MongoDB
    save_to_mongo(all_articles)
    print(f"Saved {len(all_articles)} articles to MongoDB.")
