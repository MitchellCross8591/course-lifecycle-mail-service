from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Protocol


class MailKind(str, Enum):
    LEARNER_DEADLINE = "learner_deadline"
    EDUCATOR_REPORT = "educator_report"


def _nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


@dataclass
class TemplateIds:
    learner_deadline: str
    educator_report: str

    def __post_init__(self) -> None:
        _nonempty(self.learner_deadline, "learner_deadline")
        _nonempty(self.educator_report, "educator_report")


@dataclass
class CourseDelivery:
    course_id: str
    course_title: str
    learner_email: str
    educator_email: str
    deadline_at: datetime
    completed_lessons: int
    total_lessons: int
    templates: TemplateIds

    def __post_init__(self) -> None:
        _nonempty(self.course_id, "course_id")
        _nonempty(self.course_title, "course_title")
        for field in ("learner_email", "educator_email"):
            value = getattr(self, field)
            if not isinstance(value, str) or not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+", value
            ):
                raise ValueError(f"{field} must be a valid email address")
        if not isinstance(self.deadline_at, datetime):
            raise TypeError("deadline_at must be a datetime")
        if isinstance(self.completed_lessons, bool) or not isinstance(
            self.completed_lessons, int
        ) or self.completed_lessons < 0:
            raise ValueError("completed_lessons must be a non-negative integer")
        if isinstance(self.total_lessons, bool) or not isinstance(
            self.total_lessons, int
        ) or self.total_lessons <= 0:
            raise ValueError("total_lessons must be a positive integer")
        if not isinstance(self.templates, TemplateIds):
            raise TypeError("templates must be TemplateIds")

    @classmethod
    def model_validate(cls, value: object) -> CourseDelivery:
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            raise TypeError("course delivery must be a mapping")
        data = dict(value)
        deadline = data.get("deadline_at")
        if isinstance(deadline, str):
            data["deadline_at"] = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        templates = data.get("templates")
        if isinstance(templates, dict):
            data["templates"] = TemplateIds(**templates)
        return cls(**data)


@dataclass
class DispatchReceipt:
    kind: MailKind
    recipient: str
    message_id: str


class EmailPort(Protocol):
    def send_template(
        self,
        *,
        to: str,
        template_id: str,
        template_vars: dict[str, str],
        request_key: str,
    ) -> str:
        raise AssertionError("EmailPort is a structural typing contract")


def choose_mail(course: CourseDelivery, now: datetime) -> MailKind:
    deadline = course.deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return (
        MailKind.EDUCATOR_REPORT
        if current >= deadline
        else MailKind.LEARNER_DEADLINE
    )


def dispatch_course_mail(
    course: CourseDelivery, now: datetime, email: EmailPort
) -> DispatchReceipt:
    kind = choose_mail(course, now)
    progress = f"{course.completed_lessons}/{course.total_lessons}"
    if kind is MailKind.LEARNER_DEADLINE:
        recipient = str(course.learner_email)
        template_id = course.templates.learner_deadline
    else:
        recipient = str(course.educator_email)
        template_id = course.templates.educator_report
    message_id = email.send_template(
        to=recipient,
        template_id=template_id,
        template_vars={
            "course_title": course.course_title,
            "deadline_at": course.deadline_at.isoformat(),
            "lesson_progress": progress,
        },
        request_key=f"{course.course_id}:{kind.value}:{course.deadline_at.isoformat()}",
    )
    return DispatchReceipt(kind=kind, recipient=recipient, message_id=message_id)
