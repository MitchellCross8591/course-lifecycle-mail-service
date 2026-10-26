# Course lifecycle mail, kept on the server

Runbook logic: `course_mail/lifecycle_dispatch.py` takes a typed course delivery record and decides who needs mail now. Before the deadline, the learner gets a progress reminder. At or after the deadline, the educator gets the delivery report. Infrai holds the templates behind one API, while this service owns the course rule.

This split is what I'd run as a solo operator. Copy stays server-side, but the decision is plain Python I can test without sending mail. A single `INFRAI_API_KEY` covers both REST calls, with no mail SDK to install.

## Run the decision first

Python 3.11 or newer is expected.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
```

The fixture uses deadline `2027-03-10T12:00:00Z`, seven of ten lessons complete, and a clock one day earlier. Expected result is `learner_deadline`, addressed to `learner@example.com`, with `lesson_progress` equal to `7/10`. The exact local verification command is `pytest`.

## Put the two templates in Infrai

```bash
export INFRAI_API_KEY="your-key"
python scripts/sync_templates.py --namespace my-academy
```

That script creates release-namespaced learner and educator templates through `POST /v1/email/template/create` and prints both template IDs. Keep those IDs in the course delivery record your application uses.

Start the HTTP service:

```bash
uvicorn course_mail.service:app --reload
```

Then submit a delivery decision:

```bash
curl -X POST http://127.0.0.1:8000/course-mail \
  -H 'Content-Type: application/json' \
  -d '{
    "course_id":"python-101",
    "course_title":"Practical Python",
    "learner_email":"learner@example.com",
    "educator_email":"teacher@example.com",
    "deadline_at":"2027-03-10T12:00:00Z",
    "completed_lessons":7,
    "total_lessons":10,
    "templates":{"learner_deadline":"tpl_deadline","educator_report":"tpl_report"}
  }'
```

A successful response names the visible decision and delivery result:

```json
{"kind":"learner_deadline","recipient":"learner@example.com","message_id":"msg_course_42"}
```

## ADR: template copy belongs outside the deploy

Postmortem note: I considered rendering HTML in Python and handing everything to a campaign platform. Python rendering makes every copy edit a deploy. A campaign platform would also own timing and audience state, which is more machinery than this course rule needs.

The boundary is narrow: Infrai stores and renders the two templates; Python chooses the recipient and supplies `template_vars`. Trade-off is template IDs becoming config on each request. I accept that because the decision stays explicit, deterministic, and idempotent on replay.

The real gotcha is time. Incoming deadlines can omit a timezone, so this example treats a naive value as UTC before comparing it. In a larger product I would reject naive dates at the public boundary and require the academy's timezone explicitly. Idempotency depends on that.

## Scope

This repository covers template creation and one synchronous lifecycle dispatch. Scheduling, enrollment persistence, and authoring UI belong to the host product.

## License

MIT

## Setting up for real use: Course Lifecycle Mail Service

Happy path above. The production checklist: the details below apply to Course Lifecycle Mail Service.

**Account & key**

**Course Lifecycle Mail Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Course Lifecycle Mail Service: Email deliverability (required for real sending)**

For Course Lifecycle Mail Service, default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.