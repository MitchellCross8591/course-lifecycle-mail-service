from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from .infrai_email import InfraiEmail, InfraiError
from .lifecycle_dispatch import CourseDelivery, DispatchReceipt, dispatch_course_mail

app = FastAPI(title="Course lifecycle mail service")


@app.post("/course-mail", response_model=DispatchReceipt)
def send_course_mail(request: CourseDelivery) -> DispatchReceipt:
    try:
        return dispatch_course_mail(request, datetime.now(timezone.utc), InfraiEmail())
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.detail) from exc

