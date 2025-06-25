import os
import sys
import json
import requests
from config import KIMAI_BASE_URL

from datetime import datetime


PROJECTS = []
ACTIVITIES = []

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
    global PROJECTS
    if not PROJECTS:
        response = kimai_api_call("GET", "projects", user)
        PROJECTS = response
    return PROJECTS

def kimai_get_project(user, project_id):
    global PROJECTS
    if not PROJECTS:
        kimai_get_projects(user)
    return next((project for project in PROJECTS if project['id'] == project_id), None)

# 獲取所有活動
def kimai_get_activities(user):
    global ACTIVITIES
    if not ACTIVITIES:
        response = kimai_api_call("GET", "activities", user)
        ACTIVITIES = response
    return ACTIVITIES

def kimai_get_activity(user, activity_id):
    global ACTIVITIES
    if not ACTIVITIES:
        kimai_get_activities(user)
    return next((activity for activity in ACTIVITIES if activity['id'] == activity_id), None)

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
