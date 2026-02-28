import os
from datetime import datetime, timezone
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def is_duplicate(job_id: str) -> bool:
    """Check if we've already seen this job."""
    try:
        result = (
            supabase.table("jobs")
            .select("id")
            .eq("job_id", job_id)
            .execute()
        )
        return len(result.data) > 0
    except Exception as e:
        print(f"[DB] Dedup check error: {e}")
        return False


def save_job(job: dict, fit_result: dict, cover_letter: str, status: str = "queued") -> bool:
    """Insert a new job record into the database."""
    try:
        record = {
            "job_id": job["job_id"],
            "source": job.get("source"),
            "company": job.get("company"),
            "title": job.get("title"),
            "location": job.get("location"),
            "url": job.get("url"),
            "ats": job.get("ats"),
            "description": job.get("description", "")[:5000],
            "posted_at": job.get("posted_at"),
            "fit_score": fit_result.get("score", 0),
            "fit_grade": fit_result.get("grade", ""),
            "key_matches": fit_result.get("key_matches", []),
            "concerns": fit_result.get("concerns", []),
            "fit_summary": fit_result.get("one_line_summary", ""),
            "cover_letter": cover_letter,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("jobs").insert(record).execute()
        return True
    except Exception as e:
        print(f"[DB] Save error for {job.get('title')}: {e}")
        return False


def update_job_status(job_id: str, status: str, apply_result: str = "") -> bool:
    """Update job status after an application attempt."""
    try:
        supabase.table("jobs").update({
            "status": status,
            "apply_attempted_at": datetime.now(timezone.utc).isoformat(),
            "apply_result": apply_result,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("job_id", job_id).execute()
        return True
    except Exception as e:
        print(f"[DB] Update error for {job_id}: {e}")
        return False


def get_jobs_for_report(date_str: str) -> dict:
    """Fetch today's job data for the daily report."""
    try:
        applied = (
            supabase.table("jobs")
            .select("*")
            .eq("status", "applied")
            .gte("apply_attempted_at", f"{date_str}T00:00:00+00:00")
            .lt("apply_attempted_at", f"{date_str}T23:59:59+00:00")
            .order("fit_score", desc=True)
            .execute()
        )
        skipped = (
            supabase.table("jobs")
            .select("*")
            .eq("status", "skipped")
            .gte("created_at", f"{date_str}T00:00:00+00:00")
            .order("fit_score", desc=True)
            .execute()
        )
        failed = (
            supabase.table("jobs")
            .select("*")
            .eq("status", "failed")
            .gte("created_at", f"{date_str}T00:00:00+00:00")
            .execute()
        )
        return {
            "applied": applied.data,
            "skipped": skipped.data,
            "failed": failed.data,
        }
    except Exception as e:
        print(f"[DB] Report query error: {e}")
        return {"applied": [], "skipped": [], "failed": []}


def get_all_seen_ids() -> set:
    """Get all job IDs we've ever seen (for dedup)."""
    try:
        result = supabase.table("jobs").select("job_id").execute()
        return {row["job_id"] for row in result.data}
    except Exception as e:
        print(f"[DB] Error fetching seen IDs: {e}")
        return set()
