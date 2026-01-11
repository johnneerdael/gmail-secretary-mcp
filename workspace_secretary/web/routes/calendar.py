from fastapi import APIRouter, Request, Query, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import json

from workspace_secretary.web import engine_client as engine
from workspace_secretary.web.auth import require_auth, Session

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    view: str = Query("week"),
    week_offset: int = Query(0),
    day_offset: int = Query(0),
    month_offset: int = Query(0),
    session: Session = Depends(require_auth),
):
    now = datetime.now()

    week_start = None
    week_end = None

    if view == "day":
        target_day = now + timedelta(days=day_offset)
        time_min = target_day.strftime("%Y-%m-%dT00:00:00Z")
        time_max = target_day.strftime("%Y-%m-%dT23:59:59Z")
    elif view == "month":
        target_month = now.replace(day=1) + timedelta(days=32 * month_offset)
        target_month = target_month.replace(day=1)
        month_start = target_month
        next_month = (target_month.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = next_month - timedelta(seconds=1)
        time_min = month_start.strftime("%Y-%m-%dT00:00:00Z")
        time_max = month_end.strftime("%Y-%m-%dT23:59:59Z")
    elif view == "agenda":
        time_min = now.strftime("%Y-%m-%dT00:00:00Z")
        time_max = (now + timedelta(days=30)).strftime("%Y-%m-%dT23:59:59Z")
    else:
        week_start = now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=7)
        time_min = week_start.strftime("%Y-%m-%dT00:00:00Z")
        time_max = week_end.strftime("%Y-%m-%dT23:59:59Z")

    try:
        events_response = await engine.get_calendar_events(time_min, time_max)
        events = events_response.get("events", [])
    except Exception:
        events = []

    try:
        freebusy_response = await engine.freebusy_query(time_min, time_max)
        busy_slots = (
            freebusy_response.get("calendars", {}).get("primary", {}).get("busy", [])
        )
    except Exception:
        busy_slots = []

    context = {
        "request": request,
        "view": view,
        "events": events,
        "busy_slots": busy_slots,
        "now": now,
    }

    if view == "day":
        target_day = now + timedelta(days=day_offset)
        day_events = [
            e
            for e in events
            if e.get("start", {})
            .get("dateTime", "")
            .startswith(target_day.strftime("%Y-%m-%d"))
        ]
        context.update(
            {
                "target_day": target_day,
                "day_offset": day_offset,
                "day_events": day_events,
            }
        )
    elif view == "month":
        target_month = now.replace(day=1) + timedelta(days=32 * month_offset)
        target_month = target_month.replace(day=1)
        month_start = target_month
        month_name = target_month.strftime("%B %Y")

        first_weekday = month_start.weekday()
        calendar_start = month_start - timedelta(days=first_weekday)

        weeks = []
        current = calendar_start
        for week in range(6):
            week_days = []
            for day in range(7):
                day_date = current + timedelta(days=week * 7 + day)
                day_events = [
                    e
                    for e in events
                    if e.get("start", {})
                    .get("dateTime", "")
                    .startswith(day_date.strftime("%Y-%m-%d"))
                ]
                week_days.append(
                    {
                        "date": day_date,
                        "day_num": day_date.day,
                        "is_current_month": day_date.month == target_month.month,
                        "is_today": day_date.date() == now.date(),
                        "events": day_events,
                    }
                )
            weeks.append(week_days)

        context.update(
            {
                "month_offset": month_offset,
                "month_name": month_name,
                "weeks": weeks,
            }
        )
    elif view == "agenda":
        sorted_events = sorted(
            events, key=lambda e: e.get("start", {}).get("dateTime", "")
        )
        grouped_events = {}
        for event in sorted_events:
            event_date = event.get("start", {}).get("dateTime", "")[:10]
            if event_date not in grouped_events:
                grouped_events[event_date] = []
            grouped_events[event_date].append(event)

        context.update(
            {
                "grouped_events": grouped_events,
            }
        )
    else:
        week_start = now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=7)
        days = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_events = [
                e
                for e in events
                if e.get("start", {})
                .get("dateTime", "")
                .startswith(day.strftime("%Y-%m-%d"))
            ]
            days.append(
                {
                    "date": day,
                    "name": day.strftime("%A"),
                    "short": day.strftime("%b %d"),
                    "events": day_events,
                    "is_today": day.date() == now.date(),
                }
            )

        context.update(
            {
                "days": days,
                "week_start": week_start,
                "week_end": week_end,
                "week_offset": week_offset,
            }
        )

    return templates.TemplateResponse("calendar.html", context)


@router.get("/calendar/availability", response_class=HTMLResponse)
async def availability_widget(
    request: Request,
    days: int = Query(7),
    session: Session = Depends(require_auth),
):
    now = datetime.now()
    time_min = now.strftime("%Y-%m-%dT00:00:00Z")
    time_max = (now + timedelta(days=days)).strftime("%Y-%m-%dT23:59:59Z")

    try:
        freebusy_response = await engine.freebusy_query(time_min, time_max)
        busy_slots = (
            freebusy_response.get("calendars", {}).get("primary", {}).get("busy", [])
        )
    except Exception:
        busy_slots = []

    return templates.TemplateResponse(
        "partials/availability_widget.html",
        {
            "request": request,
            "busy_slots": busy_slots,
            "days": days,
        },
    )


@router.post("/api/calendar/event")
async def create_event(
    summary: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    description: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    attendees: Optional[str] = Form(None),
    add_meet: bool = Form(False),
    session: Session = Depends(require_auth),
):
    try:
        attendee_list = [a.strip() for a in attendees.split(",")] if attendees else None
        result = await engine.create_calendar_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description or None,
            location=location or None,
            attendees=attendee_list,
            add_meet=add_meet,
        )
        return JSONResponse(
            {"success": True, "message": "Event created", "event": result}
        )
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/api/calendar/respond/{event_id}")
async def respond_to_event(
    event_id: str,
    response: str = Query(...),
    session: Session = Depends(require_auth),
):
    if response not in ("accepted", "declined", "tentative"):
        return JSONResponse(
            {"success": False, "error": "Invalid response"}, status_code=400
        )

    try:
        result = await engine.respond_to_invite(event_id, response)
        return JSONResponse({"success": True, "message": f"Response: {response}"})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
