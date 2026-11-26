from __future__ import annotations

from pathlib import Path
import os
import re
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers.auth import owner_email

APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

router = APIRouter(tags=["Public Website"])


def swing_email():
    address = os.getenv('GOLF_INQUIRY_EMAIL', '').strip() or owner_email()
    if not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', address):
        return '', ''
    body = ('Hi William,\n\nI would like help with my swing.\n\n'
            'My name:\nWhat I would like help with:\nClub used (optional):\n\n'
            'I have attached a short swing video or a few pictures.\n')
    return address, 'mailto:' + quote(address, safe='@') + '?' + urlencode({
        'subject': 'My swing — online coaching inquiry', 'body': body}, quote_via=quote)


@router.get("/", response_class=HTMLResponse, name="public_home")
def public_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="public_home.html",
        context={"page_title": "WSBCO Golf | Reedsport Golf Course"},
    )


@router.get('/send-your-swing', response_class=HTMLResponse)
def send_your_swing(request: Request) -> HTMLResponse:
    address, email_url = swing_email()
    return templates.TemplateResponse(request=request, name='online_inquiry.html', context={
        'email_address': address, 'email_url': email_url,
    })
