import os
import sys
import json

from datetime import datetime
from argparse import ArgumentParser
from flask import Flask, request, abort
# from werkzeug.middleware.proxy_fix import ProxyFix

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
    CarouselTemplate,
    CarouselColumn,
    TextMessage,
    TemplateMessage,
    ReplyMessageRequest,
    ApiException,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)


from db import users_collection
from kimai import (
    kimai_get_projects,
    kimai_get_activities,
    kimai_get_current_timesheet,
    kimai_get_recent_timesheet,
    kimai_start_timesheet,
    kimai_stop_timesheet
)

app = Flask(__name__)
# app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# app.logger.setLevel(logging.INFO)

# 設置環境變數
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None or channel_access_token is None:
    print('Specify LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN as environment variables.')
    sys.exit(1)


# 初始化 LineBot
lineHandler = WebhookHandler(channel_secret)

configuration = Configuration(
    access_token=channel_access_token
)


@app.route("/")
def index():
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


def get_or_create_user(line_user_id):
    user = users_collection.find_one({"line_user_id": line_user_id})
    if not user:
        user = {
            "line_user_id": line_user_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "kimai_api_token": None,
            "current_activity": None
        }
        users_collection.insert_one(user)
    return user

def update_user(line_user_id, update_data):
    update_data["updated_at"] = datetime.now()
    res = users_collection.update_one({"line_user_id": line_user_id}, {"$set": update_data})


def get_quick_reply_menu():
    quick_reply = QuickReply(
        items=[
            QuickReplyItem(
                action=MessageAction(label="查看狀態", text="/status")
            ),
            QuickReplyItem(
                action=MessageAction(label="開始時間追蹤", text="/start")
            ),
            QuickReplyItem(
                action=MessageAction(label="停止時間追蹤", text="/stop")
            ),
            QuickReplyItem(
                action=MessageAction(label="查看最近時間追蹤", text="/recent 5")
            ),
            QuickReplyItem(
                action=MessageAction(label="設置Kimai API Token 用法", text="/set_token")
            )
        ]
    )
    return quick_reply

@lineHandler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    user_id = event.source.user_id
    user = get_or_create_user(user_id)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        # 設置 Kimai API Token
        if text.startswith("/set_token"):
            # 檢查是否有輸入 Token
            if len(text.split(" ")) < 2:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="請先設置您的Kimai API Token，格式為 /set_token <token>"
                            )
                        ]
                    )
                )
                return
            token = text.split(" ")[1]
            update_user(user_id, {"kimai_api_token": token})
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="設置成功", quick_reply=get_quick_reply_menu())
                    ]
                )
            )
            return
        
        # 檢查是否有設置 Kimai API Token
        if not user or not user.get("kimai_api_token"):
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="請先設置您的Kimai API Token，格式為 /set_token <token>",
                            quick_reply=QuickReply(
                                items=[
                                    QuickReplyItem(
                                        action=MessageAction(label="設置Kimai API Token", text="/set_token")
                                    )
                                ]
                            )
                        )
                    ]
                )
            )
            return

        # 開始時間追蹤(選擇專案)
        if text == "/start":
            projects = kimai_get_projects(user)
            if not projects:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="您尚未設置任何專案", quick_reply=get_quick_reply_menu())
                        ]
                    )
                )
                return
            quick_reply = QuickReply(
                items=[
                    QuickReplyItem(
                        action=MessageAction(label=project["name"], text=f"/start_project {project['id']} {project['name']}")
                    ) for project in projects[:13]
                ]
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="請選擇專案", quick_reply=quick_reply)
                    ]
                )
            )
            return

        # 選完專案，選擇活動
        if text.startswith("/start_project"):
            # 檢查是否有選擇專案
            if len(text.split(" ")) < 3:
                # 沒有選擇專案，重新顯示專案列表
                projects = kimai_get_projects(user)
                if not projects:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[
                                TextMessage(text="您尚未設置任何專案", quick_reply=get_quick_reply_menu())
                            ]
                        )
                    )
                    return
                quick_reply = QuickReply(
                    items=[
                        QuickReplyItem(
                            action=MessageAction(label=project["name"], text=f"/start_project {project['id']} {project['name']}")
                        ) for project in projects[:13]
                    ]
                )
                return
            project_id = int(text.split(" ")[1])
            project_name = text.split(" ")[2] + " " + text.split(" ")[3] if len(text.split(" ")) > 3 else text.split(" ")[2]
            activities = kimai_get_activities(user, project_id)
            if not activities:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="此專案下無任何活動", quick_reply=get_quick_reply_menu())
                        ]
                    )
                )
                return
            quick_reply = QuickReply(
                items=[
                    QuickReplyItem(
                        action=MessageAction(label=activity["name"], text=f"/start_activity {project_id} {project_name} {activity['id']} {activity['name']}")
                    ) for activity in activities[:13]
                ]
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="請選擇活動", quick_reply=quick_reply)
                    ]
                )
            )
            return

        # 選完活動，輸入描述
        if text.startswith("/start_activity"):
            # 檢查是否有選擇活動
            if len(text.split(" ")) < 5:
                # 沒有選擇活動，重新顯示活動列表
                project_id = int(text.split(" ")[1])
                project_name = text.split(" ")[2] + " " + text.split(" ")[3] if len(text.split(" ")) > 3 else text.split(" ")[2]
                activities = kimai_get_activities(user, project_id)
                if not activities:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[
                                TextMessage(text="此專案下無任何活動", quick_reply=get_quick_reply_menu())
                            ]
                        )
                    )
                    return
                quick_reply = QuickReply(
                    items=[
                        QuickReplyItem(
                            action=MessageAction(label=activity["name"], text=f"/start_activity {project_id} {project_name} {activity['id']} {activity['name']}")
                        ) for activity in activities[:13]
                    ]
                )
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="請選擇活動", quick_reply=quick_reply)
                        ]
                    )
                )
                return
            project_id = int(text.split(" ")[1])
            if type(text.split(" ")[3]) == int:
                project_name = text.split(" ")[2] 
                activity_id = int(text.split(" ")[3])
                activity_name = text.split(" ")[4]
            else:
                project_name = text.split(" ")[2] + " " + text.split(" ")[3]
                activity_id = int(text.split(" ")[4])
                activity_name = text.split(" ")[5]
            update_user(user_id, {
                "current_activity": {
                    "project": {
                        "id": project_id,
                        "name": project_name
                    },
                    "activity": {
                        "id": activity_id,
                        "name": activity_name
                    }
                }
            })
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="請輸入描述")
                    ]
                )
            )
            return

        # 確認開始時間追蹤
        if text == "/confirm":
            if user.get("current_activity") is None:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="您尚未選擇任何專案或活動", quick_reply=get_quick_reply_menu())
                        ]
                    )
                )
                return
            project = user["current_activity"]["project"]
            activity = user["current_activity"]["activity"]
            description = user["current_activity"]["description"]
            try:
                res = kimai_start_timesheet(user, project["id"], activity["id"], description)
                startTime = datetime.strptime(res["begin"], "%Y-%m-%dT%H:%M:%S%z")
                confirm_message = f"開始成功\n專案:{project['name']}\n活動:{activity['name']}\n描述:{description}\n從{startTime.strftime('%m/%d %H:%M')}開始"
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text=confirm_message, quick_reply=get_quick_reply_menu())
                        ]
                    )
                )
                update_user(user_id, {"current_activity": None})
            except Exception as e:
                app.logger.error(e)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text=f"開始失敗\n{str(e)}", quick_reply=get_quick_reply_menu())
                        ]
                    )
                )
            return

        # 取消開始時間追蹤
        if text == "/cancel":
            update_user(user_id, {"current_activity": None})
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text="取消成功", quick_reply=get_quick_reply_menu())
                    ]
                )
            )
            return

        # 停止時間追蹤
        if text == "/stop":
            current_timesheet = kimai_get_current_timesheet(user)
            if not current_timesheet:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="您尚未開始任何活動", quick_reply=get_quick_reply_menu())
                        ]
                    )
                )
                return
            res = kimai_stop_timesheet(user, current_timesheet["id"])
            project_name = current_timesheet["project"]["name"]
            activity_name = current_timesheet["activity"]["name"]
            description = current_timesheet["description"]
            startTime = datetime.strptime(current_timesheet["begin"], "%Y-%m-%dT%H:%M:%S%z")
            endTime = datetime.strptime(res["end"], "%Y-%m-%dT%H:%M:%S%z")
            duration = res["duration"]
            stop_message = f"停止成功\n專案:{project_name}\n活動:{activity_name}\n描述:{description}\n從{startTime.strftime('%m/%d %H:%M')}到{endTime.strftime('%m/%d %H:%M')}\n總共{duration // 60}分鐘"

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text=stop_message, quick_reply=get_quick_reply_menu())
                    ]
                )
            )
            return

        # 查看狀態
        if text == "/status":
            current_timesheet = kimai_get_current_timesheet(user)
            if not current_timesheet:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="您尚未開始任何活動", quick_reply=get_quick_reply_menu())
                        ]
                    )
                )
                return
            project_name = current_timesheet["project"]["name"]
            activity_name = current_timesheet["activity"]["name"]
            description = current_timesheet["description"]

            # 使用現在時間和開始時間計算已經累積的時間
            startTime = datetime.strptime(current_timesheet["begin"], "%Y-%m-%dT%H:%M:%S%z")
            current_time = datetime.now()
            duration = datetime.timestamp(current_time) - datetime.timestamp(startTime)

            # 專案:xxx
            # 活動:xxx
            # 說明:xxx
            # 從xxx開始(mm/dd HH:MM)
            # 已累積xxxmins
            status_message = f"專案:{project_name}\n活動:{activity_name}\n說明:{description}\n自 {startTime.strftime('%m/%d %H:%M')} 開始\n已累積 {duration // 60} mins"
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text=status_message, quick_reply=get_quick_reply_menu())
                    ]
                )
            )
            return

        # 查看最近時間追蹤
        if text.startswith("/recent"):
            n = int(text.split(" ")[1]) if len(text.split(" ")) > 1 else 5
            recent_timesheet = kimai_get_recent_timesheet(user, n)
            if not recent_timesheet:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="您尚未有任何時間追蹤記錄", quick_reply=get_quick_reply_menu())
                        ]
                    )
                )
                return
            recent_timesheet_list = []
            for tracking in recent_timesheet:
                project_id = tracking.get("project", "")
                project_name = "".join([project["name"] for project in kimai_get_projects(user) if project["id"] == project_id])
                activity_id = tracking.get("activity", "")
                activity_name = "".join([activity["name"] for activity in kimai_get_activities(user, project_id) if activity["id"] == activity_id])
                description = tracking.get("description", "無描述") if tracking.get("description") else "無描述"
                duration = tracking.get("duration", 0)
                begin = tracking.get("begin", "")
                end = tracking.get("end", "")
                startDate = datetime.strptime(begin, "%Y-%m-%dT%H:%M:%S%z")
                endDate = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S%z")
                timesheet = {
                    "project":{
                        "id": project_id,
                        "name": project_name
                    },
                    "activity":{
                        "id": activity_id,
                        "name": activity_name
                    },
                    "description": description,
                    "duration": duration,
                    "startDate": startDate.strftime("%m/%d %H:%M"),
                    "endDate": endDate.strftime("%H:%M")
                }
                recent_timesheet_list.append(timesheet)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        # TextMessage(text="最近時間追蹤記錄:\n" + recent_timesheet_list, quick_reply=get_quick_reply_menu())
                        # Change to Carousel
                        TemplateMessage(
                            altText="最近時間追蹤記錄",
                            template=CarouselTemplate(
                                columns=[
                                    CarouselColumn(
                                        title=f"{timesheet['project']['name']} \n{timesheet['activity']['name']}",
                                        text=f"{timesheet['description'][:59]}",
                                        actions=[
                                            MessageAction(label=f"{timesheet['startDate']} ~ {timesheet['endDate']}", text="/status"),
                                            MessageAction(label=f"紀錄時間:{timesheet['duration'] // 60}分鐘", text="/status"),
                                            MessageAction(label="複製專案與活動", text=f"/start_activity {timesheet['project']['id']} {timesheet['project']['name']} {timesheet['activity']['id']} {timesheet['activity']['name']}"),
                                        ]
                                    ) for timesheet in recent_timesheet_list
                                ]
                            )
                        )
                    ]
                )
            )
            return

        # 提示使用者確認描述及資訊，使用TemplateMessage讓使用者確認
        if user.get("current_activity"):
            project = user["current_activity"]["project"]
            activity = user["current_activity"]["activity"]
            description = text
            update_user(user_id, {
                "current_activity": {
                    "project": project,
                    "activity": activity,
                    "description": description
                }
            })
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TemplateMessage(
                            alt_text="確認開始時間追蹤",
                            template=ConfirmTemplate(
                                text=f"確認開始時間追蹤\n專案:{project['name']}\n活動:{activity['name']}\n描述:{description}",
                                actions=[
                                    MessageAction(label="確認", text="/confirm"),
                                    MessageAction(label="取消", text="/cancel")
                                ]
                            )
                        )
                    ]
                )
            )
            return


        # 預設快速回覆選單
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text="請選擇操作", quick_reply=get_quick_reply_menu())
                ]
            )
        )


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        lineHandler.handle(body, signature)
    except ApiException as e:
        app.logger.warn("Got exception from LINE Messaging API: %s\n" % e.body)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', type=int, default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=True, help='debug')
    options = arg_parser.parse_args()

    app.run(
        debug=options.debug, 
        port=os.getenv('PORT', options.port),
        host='0.0.0.0'
    )