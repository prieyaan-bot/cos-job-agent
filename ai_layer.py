import anthropic
import json
import re

client = anthropic.Anthropic()

PRIYA_PROFILE = """
NAME: Priya Narula, MS
ROLE TARGET: Chief of Staff / Business Operations Leader
EMAIL: prieyaan@gmail.com
LINKEDIN: https://www.linkedin.com/in/priya-narula-cos/
PHONE: (832) 638-8175

CURRENT ROLE: Principal Technology Operations Manager & Chief of Staff, Walmart Global Tech (2022–Present)
- Strategic partner to VP of Engineering and senior leadership
- Led OKR cycles, MBRs/TBRs, QBRs, governance initiatives
- Implemented SaaS and AI/Copilot automation reducing manual effort by 35%
- Accelerated decision-making by 30%, achieved 90% executive alignment on high-impact initiatives
- Drove 12–15% operational efficiency improvement and 25% increase in cross-functional collaboration

PREVIOUS: Project Manager – Hiring, Walmart Global Tech (2021–2022)
- Led strategic hiring for Walmart Marketplace; analytics, DEI, employer branding

PREVIOUS: HR Manager, Kunai (May–Sept 2021)
- Built HR function from scratch; HRIS migration from TriNet to ADP

PREVIOUS: Manager IT Staffing & Talent Solutions, SGIC Cloud Technologies (2012–2020)
- 8-year career in end-to-end talent acquisition and team leadership

EDUCATION:
- MS, Human Resource Management — Golden Gate University
- Employee Relations Law Certificate — Institute of Applied Management and Law
- BA in Law (LLB, Honors) — National Law School of India University, Bangalore

KEY ACHIEVEMENTS:
- 30% faster decision-making for senior leadership
- 35% reduction in manual effort via SaaS/AI automation
- 15% YoY performance improvement via OKR governance
- 25% increase in cross-functional collaboration
- 10% annual cost savings via strategic resource planning
- 40% faster response to organizational priorities

CORE COMPETENCIES: Strategic planning, operational excellence, cross-functional alignment,
change management, OKR/MBR/QBR cycles, executive communication, stakeholder management,
AI proficiency (Microsoft Copilot), SaaS tools, program management, process improvement,
performance management, DEI, resource optimization

TECH STACK: MS Office Suite, Copilot, SharePoint, Confluence, Jira, Zoom, Slack

INDUSTRIES: Enterprise tech, eCommerce, retail, HR/talent, cloud/SaaS
LOCATION: San Francisco Bay Area
"""

COVER_LETTER_BASE = """
Priya Narula, MS
prieyaan@gmail.com | (832) 638-8175 | linkedin.com/in/priya-narula-cos
San Francisco Bay Area
"""


def score_job_fit(job: dict) -> dict:
    """Score how well a job matches Priya's profile (0-100)."""
    prompt = f"""You are an expert career coach specializing in Chief of Staff roles.

Here is the candidate profile:
{PRIYA_PROFILE}

Here is the job posting:
COMPANY: {job.get('company')}
TITLE: {job.get('title')}
LOCATION: {job.get('location')}
DESCRIPTION:
{job.get('description', 'No description available')[:2500]}

Score this job's fit for Priya on a scale of 0-100. Consider:
- Title and seniority alignment (CoS, Sr. CoS, VP-level CoS)
- Industry fit (tech, eCommerce, SaaS preferred)
- Skills overlap (OKR, operations, executive partnership, AI/SaaS)
- Location (Bay Area or remote preferred)

Respond ONLY with valid JSON in this exact format:
{{
  "score": <integer 0-100>,
  "grade": "<A/B/C/D>",
  "key_matches": ["<match1>", "<match2>", "<match3>"],
  "concerns": ["<concern1>"],
  "one_line_summary": "<why this is or isn't a great fit in one sentence>"
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[Scorer] Error: {e}")
        return {
            "score": 0,
            "grade": "F",
            "key_matches": [],
            "concerns": ["Scoring failed"],
            "one_line_summary": "Could not score this job."
        }


def generate_cover_letter(job: dict, fit_result: dict) -> str:
    """Generate a tailored cover letter for Priya."""
    prompt = f"""You are writing a cover letter on behalf of Priya Narula for a Chief of Staff role.

CANDIDATE PROFILE:
{PRIYA_PROFILE}

JOB DETAILS:
Company: {job.get('company')}
Title: {job.get('title')}
Location: {job.get('location')}
Description: {job.get('description', '')[:2500]}

KEY FIT POINTS TO EMPHASIZE: {', '.join(fit_result.get('key_matches', []))}

Write a compelling, concise cover letter (3-4 paragraphs, ~300 words) that:
1. Opens with a strong hook connecting Priya's background to this specific company/role
2. Highlights 2-3 quantified achievements most relevant to this job
3. Demonstrates knowledge of the company's space and challenges
4. Closes confidently with a clear call to action

Tone: Confident, strategic, warm. Avoid clichés like "I am excited to apply."
Format: Plain text, no markdown. Include the header with Priya's contact info at the top.
Start directly with the header — no commentary before or after the letter."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"[Cover Letter] Error: {e}")
        return _fallback_cover_letter(job)


def _fallback_cover_letter(job: dict) -> str:
    return f"""{COVER_LETTER_BASE}

Dear Hiring Team at {job.get('company', 'your organization')},

I am writing to express my strong interest in the {job.get('title')} role. As a Chief of Staff
and Principal Technology Operations Manager at Walmart Global Tech, I bring deep expertise in
strategic planning, cross-functional alignment, and AI-powered operational transformation.

Over the past several years, I have served as a trusted advisor to senior engineering and
business leadership, driving 12-15% operational efficiency improvements, reducing manual effort
by 35% through SaaS and AI automation, and establishing governance frameworks that improved
cross-functional collaboration by 25%.

I would welcome the opportunity to discuss how my background can support your leadership team.

Warm regards,
Priya Narula
prieyaan@gmail.com | (832) 638-8175
"""


def answer_application_question(question: str, job: dict) -> str:
    """Answer a free-text application question on Priya's behalf."""
    prompt = f"""You are answering a job application question on behalf of Priya Narula.

CANDIDATE PROFILE:
{PRIYA_PROFILE}

JOB: {job.get('title')} at {job.get('company')}

APPLICATION QUESTION:
{question}

Write a concise, authentic answer (2-4 sentences) in first person as Priya.
Be specific and quantified where possible. No fluff."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"[Q&A] Error: {e}")
        return (
            "I bring over a decade of strategic operations and Chief of Staff experience, "
            "with proven results driving executive alignment and organizational performance at scale."
        )
