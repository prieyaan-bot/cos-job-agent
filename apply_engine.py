import os
import asyncio
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout
from ai_layer import answer_application_question

APPLICANT = {
    "first_name": "Priya",
    "last_name": "Narula",
    "email": "prieyaan@gmail.com",
    "phone": "(832) 638-8175",
    "linkedin": "https://www.linkedin.com/in/priya-narula-cos/",
    "location": "San Francisco Bay Area, CA",
    "resume_path": os.environ.get("RESUME_PATH", "/app/assets/Priya_Narula_Resume_2026.pdf"),
}


async def apply_greenhouse(job: dict, cover_letter: str) -> tuple[bool, str]:
    """Apply to Greenhouse job via API first, browser fallback second."""
    job_id = job["job_id"]
    company = job["company"].lower()

    try:
        import aiohttp
        import aiofiles

        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}/applications"

        async with aiofiles.open(APPLICANT["resume_path"], "rb") as f:
            resume_bytes = await f.read()

        form_data = aiohttp.FormData()
        form_data.add_field("first_name", APPLICANT["first_name"])
        form_data.add_field("last_name", APPLICANT["last_name"])
        form_data.add_field("email", APPLICANT["email"])
        form_data.add_field("phone", APPLICANT["phone"])
        form_data.add_field("cover_letter_text", cover_letter)
        form_data.add_field(
            "resume",
            resume_bytes,
            filename="Priya_Narula_Resume_2026.pdf",
            content_type="application/pdf"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data) as resp:
                if resp.status in (200, 201):
                    return True, "Applied via Greenhouse API"
                else:
                    print(f"[Greenhouse API] Status {resp.status}, trying browser...")
    except Exception as e:
        print(f"[Greenhouse API] Error: {e}, trying browser...")

    return await apply_via_browser(job, cover_letter, ats="greenhouse")


async def apply_lever(job: dict, cover_letter: str) -> tuple[bool, str]:
    """Apply to Lever job via API first, browser fallback second."""
    posting_id = job["job_id"]
    company = job["company"].lower()

    try:
        import aiohttp
        import aiofiles

        url = f"https://api.lever.co/v0/postings/{company}/{posting_id}/apply"

        async with aiofiles.open(APPLICANT["resume_path"], "rb") as f:
            resume_bytes = await f.read()

        form_data = aiohttp.FormData()
        form_data.add_field("name", f"{APPLICANT['first_name']} {APPLICANT['last_name']}")
        form_data.add_field("email", APPLICANT["email"])
        form_data.add_field("phone", APPLICANT["phone"])
        form_data.add_field("org", "Walmart Global Tech")
        form_data.add_field("urls[LinkedIn]", APPLICANT["linkedin"])
        form_data.add_field("comments", cover_letter)
        form_data.add_field(
            "resume",
            resume_bytes,
            filename="Priya_Narula_Resume_2026.pdf",
            content_type="application/pdf"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form_data) as resp:
                if resp.status in (200, 201):
                    return True, "Applied via Lever API"
                else:
                    print(f"[Lever API] Status {resp.status}, trying browser...")
    except Exception as e:
        print(f"[Lever API] Error: {e}, trying browser...")

    return await apply_via_browser(job, cover_letter, ats="lever")


async def apply_via_browser(job: dict, cover_letter: str, ats: str) -> tuple[bool, str]:
    """Generic browser-based application using Playwright."""
    url = job.get("url")
    if not url:
        return False, "No URL available"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)

            # Click Apply button if present
            for apply_text in ["Apply", "Apply Now", "Apply for this job", "Apply for Position"]:
                try:
                    btn = page.get_by_role("button", name=apply_text)
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                except PlaywrightTimeout:
                    continue

            # Fill standard fields
            await _fill_field(page, ["first_name", "first-name", "firstName"], APPLICANT["first_name"])
            await _fill_field(page, ["last_name", "last-name", "lastName"], APPLICANT["last_name"])
            await _fill_field(page, ["email", "email_address"], APPLICANT["email"])
            await _fill_field(page, ["phone", "phone_number", "phoneNumber"], APPLICANT["phone"])
            await _fill_field(page, ["linkedin", "linkedin_profile", "linkedinUrl"], APPLICANT["linkedin"])

            # Upload resume
            await _upload_resume(page)

            # Fill cover letter
            await _fill_cover_letter(page, cover_letter)

            # Handle any custom questions
            await _handle_custom_questions(page, job)

            # Submit
            submitted = await _submit_form(page)
            if submitted:
                return True, f"Applied via browser ({ats})"
            else:
                return False, "Could not find submit button"

        except Exception as e:
            return False, f"Browser error: {str(e)[:200]}"
        finally:
            await browser.close()


async def _fill_field(page: Page, selectors: list, value: str):
    """Try multiple selector patterns to fill a form field."""
    for selector in selectors:
        for pattern in [
            f'[name="{selector}"]',
            f'[id="{selector}"]',
            f'[placeholder*="{selector}"]'
        ]:
            try:
                el = page.locator(pattern).first
                if await el.is_visible(timeout=1000):
                    await el.fill(value)
                    return
            except Exception:
                continue


async def _upload_resume(page: Page):
    """Find resume upload field and upload Priya's resume."""
    upload_selectors = [
        'input[type="file"][name*="resume"]',
        'input[type="file"][name*="cv"]',
        'input[type="file"]',
    ]
    for selector in upload_selectors:
        try:
            el = page.locator(selector).first
            if await el.count() > 0:
                await el.set_input_files(APPLICANT["resume_path"])
                await asyncio.sleep(1)
                return
        except Exception:
            continue


async def _fill_cover_letter(page: Page, cover_letter: str):
    """Fill cover letter text area."""
    cl_selectors = [
        'textarea[name*="cover"]',
        'textarea[name*="letter"]',
        'textarea[placeholder*="cover"]',
        'textarea[id*="cover"]',
        '[contenteditable="true"]',
    ]
    for selector in cl_selectors:
        try:
            el = page.locator(selector).first
            if await el.is_visible(timeout=1000):
                await el.fill(cover_letter)
                return
        except Exception:
            continue


async def _handle_custom_questions(page: Page, job: dict):
    """Find and answer custom application questions using AI."""
    try:
        text_inputs = page.locator('textarea:not([name*="cover"]):not([name*="letter"])')
        count = await text_inputs.count()
        for i in range(min(count, 5)):
            el = text_inputs.nth(i)
            if not await el.is_visible(timeout=500):
                continue
            label = await page.evaluate("""
                (el) => {
                    const id = el.id;
                    if (id) {
                        const label = document.querySelector(`label[for="${id}"]`);
                        if (label) return label.innerText;
                    }
                    const parent = el.closest('.form-group, .field, [class*="question"]');
                    if (parent) return parent.innerText.replace(el.value, '').trim();
                    return '';
                }
            """, await el.element_handle())
            if label and len(label) > 10:
                answer = answer_application_question(label, job)
                await el.fill(answer)
                await asyncio.sleep(0.5)
    except Exception as e:
        print(f"[Custom Questions] Error: {e}")


async def _submit_form(page: Page) -> bool:
    """Find and click the submit button."""
    submit_patterns = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Submit")',
        'button:has-text("Submit Application")',
        'button:has-text("Apply")',
    ]
    for pattern in submit_patterns:
        try:
            el = page.locator(pattern).last
            if await el.is_visible(timeout=2000):
                await el.click()
                await asyncio.sleep(3)
                return True
        except Exception:
            continue
    return False


async def apply_to_job(job: dict, cover_letter: str) -> tuple[bool, str]:
    """Route application to the right method based on ATS type."""
    ats = job.get("ats", "").lower()
    print(f"   Applying: {job['title']} at {job['company']} via {ats.capitalize()}")

    if ats == "greenhouse":
        return await apply_greenhouse(job, cover_letter)
    elif ats == "lever":
        return await apply_lever(job, cover_letter)
    else:
        return await apply_via_browser(job, cover_letter, ats=ats)
