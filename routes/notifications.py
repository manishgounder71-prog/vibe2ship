"""FutureShield AI — PWA / Notification endpoints."""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import json
from datetime import datetime, timedelta

import database
from routes import _PROJECT_ROOT

router = APIRouter(tags=["Notifications"])


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: dict = {}


@router.get("/api/notifications/check")
def check_notifications() -> dict:
    threats = database.query_db("SELECT id, name, urgency, probability FROM threats WHERE resolved = 0")

    goals = database.query_db(
        """SELECT id, title, deadline, progress FROM goals
           WHERE status != 'COMPLETED'
           AND deadline != ''
           AND deadline IS NOT NULL
           ORDER BY deadline ASC"""
    )

    now = datetime.now()
    upcoming_deadlines = []
    for g in goals:
        try:
            deadline_date = datetime.strptime(g["deadline"], "%Y-%m-%d")
            days_until = (deadline_date - now).days
            if 0 <= days_until <= 3:
                upcoming_deadlines.append({
                    "id": g["id"],
                    "title": g["title"],
                    "deadline": g["deadline"],
                    "days_remaining": days_until,
                    "progress": g["progress"],
                })
        except (ValueError, TypeError):
            pass

    return {
        "threats": threats,
        "deadlines": upcoming_deadlines,
        "notification_count": len(threats) + len(upcoming_deadlines),
        "checked_at": now.isoformat(),
    }


@router.post("/api/push/subscribe")
def subscribe_push(request: PushSubscriptionRequest) -> dict:
    subs_path = os.path.join(_PROJECT_ROOT, "push_subscriptions.json")

    subscriptions = []
    if os.path.exists(subs_path):
        try:
            with open(subs_path, "r") as f:
                subscriptions = json.load(f)
        except (json.JSONDecodeError, OSError):
            subscriptions = []

    existing = [s for s in subscriptions if s.get("endpoint") == request.endpoint]
    if not existing:
        subscriptions.append({
            "endpoint": request.endpoint,
            "keys": request.keys,
            "subscribed_at": datetime.now().isoformat(),
        })
        with open(subs_path, "w") as f:
            json.dump(subscriptions, f, indent=2)

    return {"status": "subscribed"}


@router.post("/api/notifications/test")
def test_notification() -> dict:
    threats = database.query_db("SELECT COUNT(*) as count FROM threats WHERE resolved = 0", one=True)
    active_threats = threats["count"] if threats else 0

    return {
        "status": "ok",
        "notification": {
            "title": "FutureShield AI System Update",
            "body": f"{active_threats} active threat(s) detected. System integrity at optimal levels.",
            "tag": "system-update",
            "url": "/dashboard.html",
            "requireInteraction": active_threats > 0,
        },
    }
