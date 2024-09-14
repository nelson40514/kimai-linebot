import os

from pymongo import MongoClient

MONGODB_URI = os.getenv('MONGODB_URI')

# 連接到MongoDB
client = MongoClient(MONGODB_URI)
db = client.kimai_bot
users_collection = db.users