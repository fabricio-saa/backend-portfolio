import os, subprocess
from pathlib import Path
from celery import Celery
from openpyxl import Workbook

BROKER = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
ARTIFACTS = Path(os.environ.get("ARTIFACTS_DIR", "/artifacts"))

celery_app = Celery("portfolio", broker=BROKER, backend=BACKEND)

# bind = True to have access to self
@celery_app.task(bind=True, name="generate_visitor_pack")
def generate_visitor_pack(self, visitor: dict) -> dict:
    job_id = self.request.id  # stable id to keep files together
    outdir = ARTIFACTS / job_id
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Build XLSX
    xlsx_path = outdir / "visitor.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Visitor"
    ws.append(["Field", "Value"])
    for k, v in visitor.items():
        ws.append([k, v])
    wb.save(xlsx_path)

    # 2) Convert to PDF via LibreOffice headless
    # LibreOffice writes alongside with the same basename
    subprocess.run(
        [
            "soffice", "--headless",
            "--convert-to", "pdf",
            "--outdir", str(outdir),
            str(xlsx_path),
        ],
        check=True,
    )
    pdf_path = outdir / "visitor.pdf"

    return {"xlsx": str(xlsx_path), "pdf": str(pdf_path)}
