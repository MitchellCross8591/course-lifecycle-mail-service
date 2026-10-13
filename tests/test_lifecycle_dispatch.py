from datetime import datetime, timezone

from course_mail.lifecycle_dispatch import (
    CourseDelivery,
    MailKind,
    dispatch_course_mail,
)


class RecordingEmail:
    def __init__(self) -> None:
        self.sent: dict[str, object] = {}

    def send_template(self, **request: object) -> str:
        self.sent = request
        return "msg_course_42"


def course(deadline: str) -> CourseDelivery:
    return CourseDelivery.model_validate(
        {
            "course_id": "python-101",
            "course_title": "Practical Python",
            "learner_email": "learner@example.com",
            "educator_email": "teacher@example.com",
            "deadline_at": deadline,
            "completed_lessons": 7,
            "total_lessons": 10,
            "templates": {
                "learner_deadline": "tpl_deadline",
                "educator_report": "tpl_report",
            },
        }
    )


def test_before_deadline_sends_learner_reminder_with_course_context() -> None:
    email = RecordingEmail()
    receipt = dispatch_course_mail(
        course("2027-03-10T12:00:00Z"),
        datetime(2027, 3, 9, 12, tzinfo=timezone.utc),
        email,
    )

    assert receipt.kind is MailKind.LEARNER_DEADLINE
    assert email.sent["to"] == "learner@example.com"
    assert email.sent["template_id"] == "tpl_deadline"
    assert email.sent["template_vars"] == {
        "course_title": "Practical Python",
        "deadline_at": "2027-03-10T12:00:00+00:00",
        "lesson_progress": "7/10",
    }


def test_at_deadline_sends_educator_delivery_report() -> None:
    email = RecordingEmail()
    receipt = dispatch_course_mail(
        course("2027-03-10T12:00:00Z"),
        datetime(2027, 3, 10, 12, tzinfo=timezone.utc),
        email,
    )

    assert receipt.kind is MailKind.EDUCATOR_REPORT
    assert receipt.message_id == "msg_course_42"
    assert email.sent["to"] == "teacher@example.com"
    assert email.sent["template_id"] == "tpl_report"

