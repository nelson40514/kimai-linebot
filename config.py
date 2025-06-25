import os
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
KIMAI_BASE_URL = os.getenv("KIMAI_BASE_URL")