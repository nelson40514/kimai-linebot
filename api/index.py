from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os
import time
from dotenv import load_dotenv

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ConfirmTemplate,
    TextMessage,
    TemplateMessage,
    ReplyMessageRequest,
    ApiException,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)

# 設置環境變數
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None or channel_access_token is None:
    print('Specify LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN as environment variables.')
    # sys.exit(1)

# 初始化 LineBot
handler = WebhookHandler(channel_secret)
line_bot_api = LineBotApi(channel_access_token)
# configuration = Configuration(
#     access_token=channel_access_token
# )

app = Flask(__name__)

# domain root
@app.route('/')
def home():
    # Return request info
    res = "From Kimai Assistant<br>"
    res += "Request Info:<br>"
    res += "Host: " + request.host + "<br>"
    res += "URL: " + request.url + "<br>"
    res += "Base URL: " + request.base_url + "<br>"
    res += "Remote Addr: " + request.remote_addr + "<br>"
    res += "Method: " + request.method + "<br>"
    res += "Path: " + request.path + "<br>"
    res += "Full Path: " + request.full_path + "<br>"
    res += "Query String: " + request.query_string.decode("utf-8") + "<br>"
    res += "Headers: <br>"
    for key, value in request.headers:
        res += key + ": " + value + "<br>"
    res += "Data: " + request.data.decode("utf-8") + "<br>"
    
    return res

@app.route("/webhook", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    time.sleep(1)
    # with ApiClient(configuration) as api_client:
    #     line_bot_api = MessagingApi(api_client)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0")