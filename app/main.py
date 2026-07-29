from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(
    title="WSBCO Golf Coach",
    version="0.1.0",
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": "WSBCO Golf Coach",
            "version": "0.1.0",
        },
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "application": "WSBCO Golf Coach",
    }