import os
import json
import re
import time

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


class Chain:

    def __init__(self):

        # ---------------------------------------------------------
        # SMALLER MODEL FOR TESTING
        # ---------------------------------------------------------
        self.model_name = "openai/gpt-oss-20b"

        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name=self.model_name,
            max_tokens=1800
        )

    # =============================================================
    # HELPER: CLEAN JSON RESPONSE
    # =============================================================

    def _clean_json_response(self, raw_response):

        if raw_response is None:
            raise ValueError("LLM returned None.")

        raw_response = str(raw_response).strip()

        if not raw_response:
            raise ValueError("LLM returned an empty response.")

        # Remove markdown code fences
        raw_response = re.sub(
            r"^```(?:json)?",
            "",
            raw_response,
            flags=re.IGNORECASE
        )

        raw_response = re.sub(
            r"```$",
            "",
            raw_response
        )

        raw_response = raw_response.strip()

        # ---------------------------------------------------------
        # First attempt: direct JSON
        # ---------------------------------------------------------

        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass

        # ---------------------------------------------------------
        # Second attempt:
        # Find JSON object
        # ---------------------------------------------------------

        object_start = raw_response.find("{")
        object_end = raw_response.rfind("}")

        if object_start != -1 and object_end != -1:

            possible_json = raw_response[
                object_start:object_end + 1
            ]

            try:
                return json.loads(possible_json)
            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------
        # Third attempt:
        # Find JSON array
        # ---------------------------------------------------------

        array_start = raw_response.find("[")
        array_end = raw_response.rfind("]")

        if array_start != -1 and array_end != -1:

            possible_json = raw_response[
                array_start:array_end + 1
            ]

            try:
                return json.loads(possible_json)
            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------
        # Nothing worked
        # ---------------------------------------------------------

        print("\n========== RAW LLM RESPONSE ==========")
        print(raw_response)
        print("======================================\n")

        raise ValueError(
            "LLM returned invalid JSON."
        )

    # =============================================================
    # NORMALIZE JOB
    # =============================================================

    def _normalize_job(self, job):

        if not isinstance(job, dict):
            job = {}

        role = job.get("role", "")
        experience = job.get("experience", "")
        skills = job.get("skills", [])
        description = job.get("description", "")

        if role is None:
            role = ""

        if experience is None:
            experience = ""

        if description is None:
            description = ""

        if not isinstance(skills, list):
            skills = []

        skills = [
            str(skill).strip()
            for skill in skills
            if str(skill).strip()
        ]

        return {
            "role": str(role).strip(),
            "experience": str(experience).strip(),
            "skills": skills[:8],
            "description": str(description).strip()
        }

    # =============================================================
    # EXTRACT JOBS
    # =============================================================

    def extract_jobs(self, cleaned_text, source_url=""):

        # ---------------------------------------------------------
        # IMPORTANT:
        #
        # /jobs/123456 = SINGLE JOB
        #
        # Otherwise = JOB LISTING
        # ---------------------------------------------------------

        single_job = bool(
            re.search(
                r"/jobs/\d+",
                source_url.lower()
            )
        )

        # ---------------------------------------------------------
        # Limit webpage size
        #
        # This prevents sending enormous job-board pages
        # to Groq.
        # ---------------------------------------------------------

        cleaned_text = cleaned_text[:18000]

        if single_job:

            # =====================================================
            # SINGLE JOB PROMPT
            # =====================================================

            prompt = f"""
You are a job information extraction system.

The webpage below is ONE SINGLE JOB POSTING.

Extract ONLY that job.

Do NOT create additional jobs.
Do NOT use related jobs.
Do NOT use recommended jobs.
Do NOT invent information.

Return ONLY valid JSON.

The JSON must have exactly these fields:

role
experience
skills
description

Important:
- role must be the actual job title.
- experience should contain required experience if available.
- skills must be a list of skills.
- description must be a short summary.
- If information is unavailable, use an empty string or empty list.

JOB PAGE:

{cleaned_text}

Return JSON now.
"""

            max_attempts = 2

        else:

            # =====================================================
            # MULTIPLE JOB PROMPT
            # =====================================================

            prompt = f"""
You are a job information extraction system.

The webpage below is a JOB LISTING PAGE.

Find the individual job postings visible on this page.

IMPORTANT RULES:

1. Return a maximum of 3 jobs.
2. If only 1 job exists, return exactly 1 job.
3. If 2 jobs exist, return exactly 2 jobs.
4. If 3 or more jobs exist, return only the first 3 jobs.
5. Do NOT invent jobs.
6. Do NOT include recommended jobs unless they are actual listings.
7. Do NOT duplicate jobs.
8. Keep descriptions short.
9. Keep skills short.
10. Return ONLY valid JSON.

Use this exact structure:

{{
    "jobs": [
        {{
            "role": "job title",
            "experience": "required experience",
            "skills": ["skill1", "skill2"],
            "description": "short description"
        }}
    ]
}}

JOB LISTING PAGE:

{cleaned_text}

Return JSON now.
"""

            max_attempts = 2

        # =========================================================
        # CALL LLM
        # =========================================================

        last_error = None

        for attempt in range(max_attempts):

            try:

                print(
                    f"\nJob extraction attempt "
                    f"{attempt + 1}/{max_attempts}"
                )

                response = self.llm.invoke(prompt)

                raw_response = response.content

                parsed = self._clean_json_response(
                    raw_response
                )

                # =================================================
                # SINGLE JOB
                # =================================================

                if single_job:

                    # Sometimes model may still return:
                    #
                    # {"jobs": [...]}
                    #
                    if isinstance(parsed, dict) and "jobs" in parsed:

                        jobs = parsed.get("jobs", [])

                        if not jobs:
                            raise ValueError(
                                "No job was extracted."
                            )

                        job = self._normalize_job(
                            jobs[0]
                        )

                    else:

                        job = self._normalize_job(
                            parsed
                        )

                    if not job["role"]:

                        raise ValueError(
                            "Could not extract job title."
                        )

                    # VERY IMPORTANT:
                    # Single URL = exactly one job

                    print(
                        f"Successfully extracted single job: "
                        f"{job['role']}"
                    )

                    return [job]

                # =================================================
                # MULTIPLE JOBS
                # =================================================

                if isinstance(parsed, dict):

                    jobs = parsed.get(
                        "jobs",
                        []
                    )

                elif isinstance(parsed, list):

                    # fallback if LLM returned array directly

                    jobs = parsed

                else:

                    jobs = []

                if not isinstance(jobs, list):
                    jobs = []

                normalized_jobs = []

                for job in jobs:

                    normalized_job = self._normalize_job(
                        job
                    )

                    if not normalized_job["role"]:
                        continue

                    normalized_jobs.append(
                        normalized_job
                    )

                # Remove duplicate titles

                unique_jobs = []

                seen_roles = set()

                for job in normalized_jobs:

                    role_key = job["role"].lower().strip()

                    if role_key in seen_roles:
                        continue

                    seen_roles.add(role_key)

                    unique_jobs.append(job)

                # HARD LIMIT = 3

                unique_jobs = unique_jobs[:3]

                if not unique_jobs:

                    raise ValueError(
                        "No jobs were extracted."
                    )

                print(
                    f"Successfully extracted "
                    f"{len(unique_jobs)} job(s)."
                )

                return unique_jobs

            except Exception as e:

                last_error = e

                print(
                    f"Job extraction failed: {e}"
                )

                # Small delay before retry

                if attempt < max_attempts - 1:
                    time.sleep(2)

        # =========================================================
        # FINAL FAILURE
        # =========================================================

        raise ValueError(
            f"Unable to extract jobs after "
            f"{max_attempts} attempts. "
            f"Last error: {last_error}"
        )

    # =============================================================
    # GENERATE EMAIL
    # =============================================================

    def write_mail(self, job, links):

        role = job.get("role", "")

        experience = job.get(
            "experience",
            ""
        )

        skills = job.get(
            "skills",
            []
        )

        description = job.get(
            "description",
            ""
        )

        # Convert portfolio links safely

        if links is None:
            links = []

        if not isinstance(links, list):
            links = [links]

        links = [
            str(link)
            for link in links
            if link
        ]

        link_text = "\n".join(links[:5])

        # =========================================================
        # EMAIL PROMPT
        # =========================================================

        prompt = f"""
You are a Business Development Executive at TechNova Solutions.

TechNova Solutions provides:

- AI/ML development
- Generative AI solutions
- Software development
- Data engineering
- Cloud solutions
- Automation
- Dedicated engineering teams

This is a B2B sales email.

The company has posted a job.

TechNova Solutions wants to offer engineering/development
support instead of asking the company to hire internally.

IMPORTANT:

- Do NOT write as a job applicant.
- Do NOT say "I am applying".
- Do NOT invent clients.
- Do NOT invent achievements.
- Do NOT claim TechNova worked with the target company.
- Do NOT invent statistics.
- Do NOT use [Company Name].
- Keep it professional.
- Keep it around 120-160 words.
- Mention the actual job title.
- Explain how TechNova can provide relevant engineering support.
- Mention benefits such as faster delivery, flexible capacity,
  and reduced hiring/onboarding effort.
- Use portfolio links only if they are relevant.

JOB TITLE:
{role}

EXPERIENCE:
{experience}

SKILLS:
{", ".join(skills)}

DESCRIPTION:
{description}

RELEVANT PORTFOLIO LINKS:
{link_text}

Write ONE cold email.

Start with:

Subject:

Then write the email.

Return ONLY the email.
"""

        response = self.llm.invoke(prompt)

        email = response.content

        if email is None:
            raise ValueError(
                "LLM returned an empty email."
            )

        email = str(email).strip()

        if not email:
            raise ValueError(
                "LLM returned an empty email."
            )

        return email