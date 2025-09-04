from pydantic import BaseModel

class EnqueueResponse(BaseModel):
    job_id: str
    status_url: str
    downloads_url: str
