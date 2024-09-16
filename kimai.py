import os
import sys
import json
import pytz
import requests

from datetime import datetime

# 獲取環境變數
KIMAI_BASE_URL = os.getenv('KIMAI_BASE_URL')
if KIMAI_BASE_URL is None:
    print('Specify KIMAI_BASE_URL as environment variables.')
    sys.exit(1)

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
def kimai_get_activities(user, project_id = None):
    if project_id is None:
        response = kimai_api_call("GET", "activities", user)
    else:
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
    response = kimai_api_call("GET", "timesheets", user, param={"size": n})
    return response

# 獲取user資訊
def get_user_info(user):
    response = kimai_api_call("GET", "users/me", user)
    return response

# 開始時間追蹤
def kimai_start_timesheet(user, project_id, activity_id, description):
    data = {
        "project": project_id,
        "activity": activity_id,
        "description": description,
        "tags": "",
    }
    response = kimai_api_call("POST", "timesheets", user, json=data)
    return response

# 停止時間追蹤
def kimai_stop_timesheet(user, current_timesheet_id):
    response = kimai_api_call("GET", f"timesheets/{current_timesheet_id}/stop", user)
    return response
