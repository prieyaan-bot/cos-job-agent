import os
import base64
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from database import get_jobs_for_report

PRIYA_EMAIL = "prieyaan@gmail.com"


def generate_html_report(date_str: str, data: dict) -> str:
    """Generate a beautiful HTML daily digest email."""
    applied = data["applied"]
    skipped = data["skipped"]
    failed = data["failed"]

    total_scanned = len(applied) + len(skipped) + len(failed)

    grade_colors = {
        "A": "#22c55e",
        "B": "#84cc16",
        "C": "#f59e0b",
        "D": "#ef4444",
        "F": "#6b7280"
    }

    def grade_badge(grade: str) -> str:
        color = grade_colors.get(grade, "#6b7280")
        return (
            f'<span style="background:{color};color:white;padding:2px 8px;'
            f'border-radius:12px;font-size:12px;font-weight:bold;">{grade}</span>'
        )

    def job_row(job: dict) -> str:
        score = job.get("fit_score", 0)
        grade = job.get("fit_grade", "?")
        return f"""
        <tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:12px 8px;">
                <strong style="color:#1e293b;">{job.get('title','')}</strong><br>
                <span style="color:#64748b;font-size:13px;">
                    {job.get('company','')} · {job.get('location','')}
                </span>
            </td>
            <td style="padding:12px 8px;text-align:center;">{grade_badge(grade)}</td>
            <td style="padding:12px 8px;text-align:center;font-weight:bold;
                color:#3b82f6;">{score}%</td>
            <td style="padding:12px 8px;font-size:12px;color:#64748b;">
                {job.get('source','')}
            </td>
            <td style="padding:12px 8px;">
                <a href="{job.get('url','#')}"
                   style="color:#3b82f6;font-size:12px;text-decoration:none;">
                   View →
                </a>
            </td>
        </tr>"""

    def build_table(jobs: list) -> str:
        if not jobs:
            return '<p style="color:#64748b;">None today.</p>'
        rows = "".join(job_row(j) for j in jobs)
        return f"""
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr style="background:#f8fafc;">
              <th style="padding:10px 8px;text-align:left;color:#64748b;
                  font-size:12px;text-transform:uppercase;">Job</th>
              <th style="padding:10px 8px;text-align:center;color:#64748b;
                  font-size:12px;text-transform:uppercase;">Grade</th>
              <th style="padding:10px 8px;text-align:center;color:#64748b;
                  font-size:12px;text-transform:uppercase;">Fit</th>
              <th style="padding:10px 8px;color:#64748b;
                  font-size:12px;text-transform:uppercase;">Source</th>
              <th style="padding:10px 8px;color:#64748b;
                  font-size:12px;text-transform:uppercase;">Link</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    failed_section = ""
    if failed:
        failed_section = f"""
        <div style="background:white;border-radius:12px;padding:20px;
             margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
          <h2 style="color:#ef4444;font-size:18px;margin:0 0 16px;">
            ⚠️ Failed — Apply Manually ({len(failed)})
          </h2>
          {build_table(failed)}
        </div>"""

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f8fafc;
     font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:700px;margin:0 auto;padding:24px;">

    <!-- HEADER -->
    <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);
         border-radius:12px;padding:28px;margin-bottom:20px;">
      <h1 style="color:white;margin:0;font-size:22px;font-weight:700;">
        📋 Chief of Staff Job Agent
      </h1>
      <p style="color:#bfdbfe;margin:6px 0 0;font-size:14px;">
        Daily Report for Priya Narula · {date_str}
      </p>
    </div>

    <!-- SUMMARY CARDS -->
    <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
      <div style="flex:1;min-width:130px;background:white;border-radius:10px;
           padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08);">
        <div style="font-size:28px;font-weight:700;color:#2563eb;">{total_scanned}</div>
        <div style="color:#64748b;font-size:13px;margin-top:4px;">Jobs Scanned</div>
      </div>
      <div style="flex:1;min-width:130px;background:white;border-radius:10px;
           padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08);">
        <div style="font-size:28px;font-weight:700;color:#22c55e;">{len(applied)}</div>
        <div style="color:#64748b;font-size:13px;margin-top:4px;">Applied ✅</div>
      </div>
      <div style="flex:1;min-width:130px;background:white;border-radius:10px;
           padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08);">
        <div style="font-size:28px;font-weight:700;color:#f59e0b;">{len(skipped)}</div>
        <div style="color:#64748b;font-size:13px;margin-top:4px;">Skipped ⏭️</div>
      </div>
      <div style="flex:1;min-width:130px;background:white;border-radius:10px;
           padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.08);">
        <div style="font-size:28px;font-weight:700;color:#ef4444;">{len(failed)}</div>
        <div style="color:#64748b;font-size:13px;margin-top:4px;">Need Attention ⚠️</div>
      </div>
    </div>

    <!-- APPLIED TODAY -->
    <div style="background:white;border-radius:12px;padding:20px;
         margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
      <h2 style="color:#1e293b;font-size:18px;margin:0 0 16px;">
        ✅ Applied Today ({len(applied)})
      </h2>
      {build_table(applied)}
    </div>

    <!-- SKIPPED -->
    <div style="background:white;border-radius:12px;padding:20px;
         margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
      <h2 style="color:#64748b;font-size:18px;margin:0 0 16px;">
        ⏭️ Skipped — Low Fit Score ({len(skipped)})
      </h2>
      {build_table(skipped)}
    </div>

    <!-- FAILED -->
    {failed_section}

    <!-- FOOTER -->
    <div style="margin-top:24px;padding:16px;background:#f1f5f9;
         border-radius:10px;text-align:center;">
      <p style="color:#64748b;font-size:12px;margin:0;">
        Generated automatically by your Chief of Staff Job Agent.<br>
        Next scan runs tomorrow at 8:00 AM PT.
      </p>
    </div>

  </div>
</body>
</html>"""
    return html


def send_daily_report(date_str: str):
    """Fetch data, generate HTML report, send via Gmail."""
    print(f"📧 Generating daily report for {date_str}...")

    data = get_jobs_for_report(date_str)
    html_body = generate_html_report(date_str, data)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"📋 CoS Job Agent Report — {date_str} · "
        f"{len(data['applied'])} Applied"
    )
    msg["From"] = PRIYA_EMAIL
    msg["To"] = PRIYA_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    try:
        token_path = os.environ.get("GMAIL_TOKEN_PATH", "/app/assets/gmail_token.json")
        creds = Credentials.from_authorized_user_file(
            token_path,
            scopes=["https://www.googleapis.com/auth/gmail.send"]
        )
        service = build("gmail", "v1", credentials=creds)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()
        print(f"✅ Report sent to {PRIYA_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        fallback_path = f"/tmp/report_{date_str}.html"
        with open(fallback_path, "w") as f:
            f.write(html_body)
        print(f"   Saved to {fallback_path} as fallback")


if __name__ == "__main__":
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    send_daily_report(today)
