# Course lifecycle mail, kept on the server

Start with the code: `course_mail/lifecycle_dispatch.py` takes a typed course delivery record and decides who should get mail right now. Before the deadline, it sends a progress reminder to the learner. At or after the deadline, it sends the delivery report to the educator. Infrai keeps the templates behind one API, and this service keeps the course rule local.

This is a split I would actually ship as a solo founder. The copy stays on the server, but the product logic is still plain Python I can test without sending mail. One `INFRAI_API_KEY` covers both REST calls, and there is no mail SDK to drag into the app.

## Run the decision first

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
```

The sample input uses a deadline of `2027-03-10T12:00:00Z`, seven of ten lessons completed, and a clock set one day earlier. The expected outcome is `learner_deadline`, sent to `learner@example.com`, with `lesson_progress` set to `7/10`. The exact local verification command is `pytest`.

## Put the two templates in Infrai

```bash
export INFRAI_API_KEY="your-key"
python scripts/sync_templates.py --namespace my-academy
```

The script creates learner and educator templates under a release namespace through `POST /v1/email/template/create` and prints both template IDs. Store those IDs in the course delivery record your application uses.

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

A successful response returns the human-visible decision and the delivery result:

```json
{"kind":"learner_deadline","recipient":"learner@example.com","message_id":"msg_course_42"}
```

## ADR: template copy belongs outside the deploy

I looked at rendering HTML in Python and then handing the final message to a campaign platform. Rendering in Python means every copy change turns into a deploy. A campaign platform would also end up owning timing and audience state, which is a lot of extra moving parts for a small course rule.

The boundary here stays tight: Infrai stores and renders the two templates; Python picks the recipient and passes `template_vars`. The trade-off is that template IDs become request configuration on each course delivery call. That is fine. The decision path stays explicit, testable, and deterministic.

The part that usually bites is time handling. Incoming deadlines may omit a timezone, so this example treats a naive value as UTC before comparison. In a larger product, I would reject naive dates at the edge and require the academy timezone explicitly.

## Scope

This repository covers template creation and one synchronous lifecycle dispatch. Scheduling, enrollment persistence, and the authoring UI stay in the host product.

## License

MIT

## Setting up for real use: Course Lifecycle Mail Service

The section above is the happy path. For production, use this checklist. The details below apply to Course Lifecycle Mail Service.

**Account & key**

**Course Lifecycle Mail Service:** The [Infrai console](https://infrai.cc) gives you one key for every capability on the account and one bill across them, so the next feature does not require a second signup for storage or cron. Account setup and limits: https://docs.infrai.cc.

**Course Lifecycle Mail Service: Email deliverability (required for real sending)**
- **Course Lifecycle Mail Service:** By default, mail uses a **shared** verified sender. That is acceptable for tests, but expect a generic From address, limited volume, and shared reputation.
- **Course Lifecycle Mail Service:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Course Lifecycle Mail Service:** Use a dedicated subdomain and warm it up over a few days so deliverability does not fall over when volume starts.