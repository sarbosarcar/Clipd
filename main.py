import uvicorn

from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os
from supabase import create_client, Client

import dotenv

import base64

dotenv.load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


@app.get("/{cliplink}", response_class=HTMLResponse)
async def read_item(cliplink: str, request: Request):
    response = supabase.table("clipboard").select("encoded").eq("link", cliplink).execute().data
    if response == []:
        return templates.TemplateResponse(
            request=request, name="index.html", context={"link": cliplink, "prefill": ""}
        )
    else:
        prefill = response[0]["encoded"]
        prefill = base64.b64decode(prefill.encode("utf-8")).decode("utf-8")
        return templates.TemplateResponse(
            request=request, name="index.html", context={"link": cliplink, "prefill": prefill}
        )

@app.post("/{cliplink}/save")
async def write_item(request: Request, cliplink: str, content: str = Form(...)):
    string = content.encode("utf-8")
    base64_enc = base64.b64encode(string)
    base64_string = base64_enc.decode("utf-8")
    response = supabase.table("clipboard").select("link").eq("link", cliplink).execute().data
    if response == []:
        if content != "":
            supabase.table("clipboard").insert({"link": cliplink, "encoded": base64_string}).execute()
    else:
        if content != "":
            supabase.table("clipboard").update({"encoded": base64_string}).eq("link", cliplink).execute()

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
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)