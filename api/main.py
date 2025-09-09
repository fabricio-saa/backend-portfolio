import uuid, os
from celery.result import AsyncResult
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from starlette.templating import Jinja2Templates

from models import EnqueueResponse
from tasks import celery_app, generate_visitor_pack


ARTIFACTS = Path(os.environ.get('ARTIFACTS_DIR'), '/artifacts')
app = FastAPI(title='Backend Portfolio')
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    ctx = {
        'request': request,
        'email': 'fabricio.saavedra@outlook.com',
        'links': [
            {
                'label': 'github',
                'href': 'https://github.com/fabriccio27'
            },
            {
                'label': 'linkedin',
                'href': 'https://www.linkedin.com/in/fabricio-saavedra-n1271991/'
            }
        ]
    }
    return templates.TemplateResponse('index.html', context=ctx)


@app.post("/actions/generate-visitor-pack", response_model=EnqueueResponse, status_code=202)
async def generate_pack(request: Request):
    # Minimal “visitor” data—prove you can derive context server-side
    visitor = {
        "ip": request.client.host if request.client else "unknown",
        "ua": request.headers.get("user-agent", "unknown"),
        "accept_lang": request.headers.get("accept-language", "unknown"),
    }
    job = generate_visitor_pack.delay(visitor)  # enqueue
    job_id = job.id
    base = f"/jobs/{job_id}"
    return EnqueueResponse(
        job_id=job_id,
        status_url=base,
        downloads_url=f"{base}/downloads",
    )


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    # this polls by hitting redis
    res: AsyncResult = celery_app.AsyncResult(job_id)
    return {"job_id": job_id, "state": res.state}


# same job could output to different formats
@app.get("/jobs/{job_id}/downloads")
def list_downloads(job_id: str):
    folder = ARTIFACTS / job_id
    if not folder.exists():
        raise HTTPException(404, "Not ready")
    files = {p.name: f"/download/{job_id}/{p.name}" for p in folder.iterdir() if p.is_file()}
    if not files:
        raise HTTPException(404, "Not ready")
    return {"job_id": job_id, "files": files}


# download the file you want based on the file listed by endpoint above
@app.get("/download/{job_id}/{filename}")
def download(job_id: str, filename: str):
    path = ARTIFACTS / job_id / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path)