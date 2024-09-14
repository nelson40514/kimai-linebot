import os
import sys

from pymongo import MongoClient

# 獲取環境變數
MONGODB_URI = os.getenv('MONGODB_URI', None)
if MONGODB_URI is None:
    print('Specify MONGODB_URI as environment variables.')
    sys.exit(1)


# 初始化 MongoDB
client = MongoClient(MONGODB_URI)
db = client.kimai_bot
users_collection = db.users