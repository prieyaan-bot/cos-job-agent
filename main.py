import asyncio
from datetime import datetime, timezone

from scraper import scrape_all_boards
from ai_layer import score_job_fit, generate_cover_letter
from database import save_job, update_job_status, get_all_seen_ids
from apply_engine import apply_to_job
from reporter import send_daily_report

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

MIN_FIT_SCORE = 70           # Only apply to jobs scoring 70+
MAX_APPLICATIONS_PER_RUN = 10  # Safety cap per run


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

async def run_agent():
    log("=" * 55)
    log("🚀 Chief of Staff Job Agent Starting")
    log(f"   Candidate: Priya Narula")
    log(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log("=" * 55)

    # ── STEP 1: SCRAPE ──────────────────────────────────
    log("\n📡 STEP 1: Scraping job boards...")
    all_jobs = scrape_all_boards()
    log(f"   Raw jobs found: {len(all_jobs)}")

    # ── STEP 2: DEDUPLICATE ─────────────────────────────
    log("\n🔍 STEP 2: Deduplicating...")
    seen_ids = get_all_seen_ids()
    new_jobs = [j for j in all_jobs if j["job_id"] not in seen_ids]
    log(f"   New jobs (not seen before): {len(new_jobs)}")

    if not new_jobs:
        log("   No new jobs found today.")
        log("\n📧 Sending report anyway...")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        send_daily_report(today)
        return

    # ── STEP 3: SCORE + COVER LETTERS ───────────────────
    log(f"\n🤖 STEP 3: Scoring {len(new_jobs)} jobs with AI...")
    scored_jobs = []

    for i, job in enumerate(new_jobs):
        log(f"   [{i+1}/{len(new_jobs)}] {job['title']} @ {job['company']}")
        fit = score_job_fit(job)
        score = fit.get("score", 0)
        grade = fit.get("grade", "?")
        summary = fit.get("one_line_summary", "")
        log(f"      → Score: {score} ({grade}) — {summary}")

        if score >= MIN_FIT_SCORE:
            log(f"      → Generating cover letter...")
            cover_letter = generate_cover_letter(job, fit)
            status = "queued"
        else:
            cover_letter = ""
            status = "skipped"

        save_job(job, fit, cover_letter, status=status)

        if score >= MIN_FIT_SCORE:
            scored_jobs.append((job, fit, cover_letter))

    log(f"\n   ✅ Qualified jobs (score ≥ {MIN_FIT_SCORE}): {len(scored_jobs)}")

    # ── STEP 4: APPLY ────────────────────────────────────
    if not scored_jobs:
        log("\n   No qualifying jobs to apply to today.")
    else:
        log(f"\n📨 STEP 4: Applying to jobs...")
        scored_jobs.sort(key=lambda x: x[1].get("score", 0), reverse=True)
        apply_queue = scored_jobs[:MAX_APPLICATIONS_PER_RUN]

        applied_count = 0
        failed_count = 0

        for job, fit, cover_letter in apply_queue:
            log(f"\n   → {job['title']} at {job['company']} (Score: {fit.get('score')})")
            try:
                success, result_msg = await apply_to_job(job, cover_letter)
                if success:
                    update_job_status(job["job_id"], "applied", result_msg)
                    log(f"      ✅ Applied! {result_msg}")
                    applied_count += 1
                else:
                    update_job_status(job["job_id"], "failed", result_msg)
                    log(f"      ❌ Failed: {result_msg}")
                    failed_count += 1
                await asyncio.sleep(3)

            except Exception as e:
                err = str(e)[:150]
                update_job_status(job["job_id"], "failed", f"Exception: {err}")
                log(f"      ❌ Exception: {err}")
                failed_count += 1

        log(f"\n   Summary: {applied_count} applied, {failed_count} failed")

    # ── STEP 5: DAILY REPORT ─────────────────────────────
    log("\n📧 STEP 5: Sending daily report...")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    send_daily_report(today)

    log("\n" + "=" * 55)
    log("✅ Agent run complete!")
    log("=" * 55)


if __name__ == "__main__":
    asyncio.run(run_agent())
```

---

## How to add it on GitHub:

1. Click **"Add file" → "Create new file"**
2. Type `main.py` in the filename box
3. Paste the code above
4. Click the green **"Commit new file"** button ✅

---

## 🎉 That's all 7 Python files done!

Your repo should now look like this:
```
cos-job-agent/
├── main.py
├── scraper.py
├── ai_layer.py
├── apply_engine.py
├── database.py
├── reporter.py
└── requirements.txt
