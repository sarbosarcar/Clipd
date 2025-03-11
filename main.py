import uvicorn

from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from supabase import create_client, Client

import os
import dotenv
import base64
import hashlib
from datetime import datetime, timedelta

dotenv.load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
LOGIN_PASSWORD: str = os.environ.get("LOGIN_PASSWORD")
hashed_password = hashlib.sha256(LOGIN_PASSWORD.encode()).hexdigest()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")

def format_datetime(timestamp: str) -> str:
    dt_utc = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    # Manually add 5 hours 30 minutes for IST
    dt_ist = dt_utc + timedelta(hours=5, minutes=30)

    return dt_ist.strftime("%d %b %Y %H:%M")

@app.get("/~root")
async def fetch_details(request: Request):
    response = supabase.table("clipboard").select("created_at, link").order("created_at", desc=True).execute().data
    for r in response:
        r["created_at"] = format_datetime(r["created_at"])
    return templates.TemplateResponse(request=request, name="root.html", context={"links": response, "password": hashed_password})

@app.get("/{cliplink}", response_class=HTMLResponse)
async def read_item(cliplink: str, request: Request):
    response = supabase.table("clipboard").select("encoded").eq("link", cliplink).execute().data
    images = supabase.table("clipboard").select("images").eq("link", cliplink).execute().data
    if images:
        img = images[0]["images"]
    else:
        img = []
    if response == []:
        return templates.TemplateResponse(
            request=request, name="index.html", context={"link": cliplink, "prefill": "", "images": img, "password": hashed_password}
        )
    else:
        prefill = response[0]["encoded"]
        prefill = base64.b64decode(prefill.encode("utf-8")).decode("utf-8")
        return templates.TemplateResponse(
            request=request, name="index.html", context={"link": cliplink, "prefill": prefill, "images": img, "password": hashed_password}
        )

@app.post("/{cliplink}/save")
async def write_item(request: Request, cliplink: str, content: str = Form(...), img_content: str = Form(...)):
    string = content.encode("utf-8")
    base64_enc = base64.b64encode(string)
    base64_string = base64_enc.decode("utf-8")
    response = supabase.table("clipboard").select("link").eq("link", cliplink).execute().data
    imgs = img_content.split("\n")
    imgs_ret = []
    for img in imgs:
        if img.strip("\r"):
            imgs_ret.append(img.strip("\r"))
    
    if response == []:
        if content != "":
            supabase.table("clipboard").insert({"link": cliplink, "encoded": base64_string}).execute()
        if imgs_ret:
            supabase.table("clipboard").insert({"images": imgs_ret}).execute()
    else:
        if content != "":
            supabase.table("clipboard").update({"encoded": base64_string}).eq("link", cliplink).execute()
        if imgs_ret:
            supabase.table("clipboard").update({"images": imgs_ret}).eq("link", cliplink).execute()
        else:
            curr_images = supabase.table("clipboard").select("images").eq("link", cliplink).execute().data
            if curr_images:
                supabase.table("clipboard").update({"images": None}).eq("link", cliplink).execute()

    return RedirectResponse(f"/{cliplink}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/{cliplink}/delete")
async def delete_item(request: Request, cliplink: str):
    response = supabase.table("clipboard").select("link").eq("link", cliplink).execute().data
    if response != []:
        supabase.table("clipboard").delete().eq("link", cliplink).execute()

    return RedirectResponse(f"/{cliplink}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/")
async def fetch_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.post("/")
async def create_link(request: Request, link: str = Form(...)):
    return RedirectResponse(f"/{link}", status_code=status.HTTP_303_SEE_OTHER)

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=9999, reload=True)
