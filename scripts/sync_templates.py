from __future__ import annotations

import argparse
from uuid import uuid4

from course_mail.infrai_email import InfraiEmail

TEMPLATES = {
    "learner-deadline": {
        "subject": "Your {{course_title}} deadline is coming up",
        "html": "<h1>{{course_title}}</h1><p>Deadline: {{deadline_at}}</p><p>Progress: {{lesson_progress}}</p>",
    },
    "educator-report": {
        "subject": "Course delivery report: {{course_title}}",
        "html": "<h1>{{course_title}}</h1><p>Deadline: {{deadline_at}}</p><p>Learner progress: {{lesson_progress}}</p>",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", default="academy")
    args = parser.parse_args()
    release = uuid4().hex[:10]
    email = InfraiEmail()
    for role, template in TEMPLATES.items():
        name = f"{args.namespace}-{role}-{release}"
        template_id = email.create_template(
            name=name,
            subject=template["subject"],
            html=template["html"],
            request_key=f"template:{name}",
        )
        print(f"{role}: {template_id}")


if __name__ == "__main__":
    main()

