from pymongo import MongoClient
from config import MONGODB_URI

if MONGODB_URI is None:
    raise ValueError("MONGODB_URI is not set in the environment variables.")


# 初始化 MongoDB
client = MongoClient(MONGODB_URI)
db = client.kimai_bot
users_collection = db.users