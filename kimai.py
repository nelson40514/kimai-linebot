import os
import pytz
import requests

from datetime import datetime

KIMAI_BASE_URL = os.getenv('KIMAI_BASE_URL')


# 設置時區
TZ = pytz.timezone('Asia/Taipei')

# 呼叫 Kimai API
def kimai_api_call(method, endpoint, user, param=None, json=None):
    headers = {
        "Authorization": f"Bearer {user['kimai_api_token']}",
        "Content-Type": "application/json"
    }
    url = f"{KIMAI_BASE_URL}/api/{endpoint}"
    response = requests.request(method, url, headers=headers, params=param, json=json)
    response.raise_for_status()
    return response.json()

# 獲取所有專案
def kimai_get_projects(user):
    response = kimai_api_call("GET", "projects", user)
    return response

# 獲取所有活動
def kimai_get_activities(user, project_id):
    response = kimai_api_call("GET", "activities", user, param={"project": project_id})
    return response

# 獲取進行中的時間追蹤
def kimai_get_current_timesheet(user):
    response = kimai_api_call("GET", "timesheets/active", user)
    if response:
        return response[0]
    return None

# 獲取最近n筆時間追蹤
def kimai_get_recent_timesheet(user, n):
    response = kimai_api_call("GET", "timesheets/recent", user, param={"size": n})
    return response

# 獲取user資訊
def get_user_info(user):
    response = kimai_api_call("GET", "users/me", user)
    return response

# 開始時間追蹤
def kimai_start_timesheet(user, project_id, activity_id, description):
    params = {
        "begin": datetime.now(TZ).isoformat(),
        "project": project_id,
        "activity": activity_id,
        # "end": "<dateTime>",
        "description": description,
        # "fixedRate": "<number>",
        # "hourlyRate": 280,
        "user": get_user_info(user)["id"],
        "tags": [],
        "exported": False,
        "billable": True,
    }
    # response = kimai_api_call("POST", "timesheets", user, param=params)
    response = params
    return response

# 停止時間追蹤
def kimai_stop_timesheet(user, timesheet_id):
    current_activity = user.get("current_activity")
    if not current_activity:
        return None
    
    data = {"end": datetime.now(TZ).isoformat()}
    # response = kimai_api_call("timesheets/{timesheet_id}", user, json=data)
    response = data
    return response
