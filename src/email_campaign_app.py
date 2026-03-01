from __future__ import annotations

import argparse
import os
import re
from collections import deque
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class CampaignRequirements:
    goal: str
    audience: str
    tone: str
    cta: str


class WebsiteCrawler:
    def __init__(self, include_subdomains: bool = False, timeout: int = 10) -> None:
        self.include_subdomains = include_subdomains
        self.timeout = timeout

    def crawl(self, start_url: str, max_pages: int = 20) -> dict[str, str]:
        """Return mapping of crawled URL -> extracted text."""
        start_url = self._normalize_url(start_url)
        base_host = urlparse(start_url).netloc
        queue: deque[str] = deque([start_url])
        seen: set[str] = set()
        pages: dict[str, str] = {}

        while queue and len(pages) < max_pages:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)

            try:
                response = requests.get(current, timeout=self.timeout)
                if "text/html" not in response.headers.get("Content-Type", ""):
                    continue
                html = response.text
            except requests.RequestException:
                continue

            text = self._extract_text(html)
            if text:
                pages[current] = text

            for link in self._extract_links(html, current):
                if link not in seen and self._is_allowed_host(link, base_host):
                    queue.append(link)

        return pages

    @staticmethod
    def _normalize_url(url: str) -> str:
        if not urlparse(url).scheme:
            return f"https://{url}"
        return url

    def _is_allowed_host(self, link: str, base_host: str) -> bool:
        host = urlparse(link).netloc
        if self.include_subdomains:
            return host == base_host or host.endswith(f".{base_host}")
        return host == base_host

    @staticmethod
    def _extract_links(html: str, base_url: str) -> Iterable[str]:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href:
                continue
            candidate = urljoin(base_url, href)
            parsed = urlparse(candidate)
            if parsed.scheme in {"http", "https"}:
                normalized = parsed._replace(fragment="", query="").geturl()
                yield normalized

    @staticmethod
    def _extract_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(soup.stripped_strings)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:12000]


def build_company_brief(pages: dict[str, str]) -> str:
    if not pages:
        return "No content could be extracted from the provided website."

    joined = "\n\n".join(f"URL: {url}\nCONTENT: {text}" for url, text in pages.items())
    return (
        "Company website intelligence summary:\n"
        f"- Pages crawled: {len(pages)}\n"
        "- Raw source excerpts (truncated):\n"
        f"{joined[:15000]}"
    )


def generate_email_with_openai(brief: str, req: CampaignRequirements) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        return generate_email_template(brief, req)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return generate_email_template(brief, req)

    client = OpenAI(api_key=api_key)
    prompt = f"""
You are an expert B2B email marketer.

Use the company intelligence below to produce:
1) Subject line options (3)
2) Preheader text options (2)
3) One complete outreach email body
4) A short follow-up email body

Company intelligence:
{brief}

Campaign requirements:
- Goal: {req.goal}
- Audience: {req.audience}
- Tone: {req.tone}
- CTA: {req.cta}
""".strip()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        temperature=0.6,
    )
    return response.output_text


def generate_email_template(brief: str, req: CampaignRequirements) -> str:
    snippet = brief[:400].replace("\n", " ")
    return f"""
Subject options:
1) Helping {req.audience} reach {req.goal}
2) A faster path to {req.goal}
3) Idea for your team this quarter

Preheaders:
- Built from your website positioning and campaign goal.
- Quick note with a practical next step.

Primary email:
Hi there,

I reviewed your website and noticed messaging around: {snippet}

Based on that, I wanted to share a campaign idea focused on {req.goal} for {req.audience}.

We can build a sequence in a {req.tone.lower()} tone that aligns with your positioning and drives action.

If this is a priority, let's {req.cta}.

Best,
Your Team

Follow-up email:
Hi again,

Wanted to bump this in case boosting {req.goal} is on your roadmap.
Happy to send a sample 3-email sequence tailored to your audience.

Open to a quick next step: {req.cta}.
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate campaign emails from company website content")
    parser.add_argument("--url", required=True, help="Company website URL")
    parser.add_argument("--campaign-goal", required=True, help="Campaign goal")
    parser.add_argument("--audience", required=True, help="Target audience")
    parser.add_argument("--tone", default="Professional", help="Email tone")
    parser.add_argument("--cta", required=True, help="Call to action")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum pages to crawl")
    parser.add_argument("--include-subdomains", action="store_true", help="Include subdomains")
    args = parser.parse_args()

    crawler = WebsiteCrawler(include_subdomains=args.include_subdomains)
    pages = crawler.crawl(args.url, max_pages=args.max_pages)
    brief = build_company_brief(pages)

    requirements = CampaignRequirements(
        goal=args.campaign_goal,
        audience=args.audience,
        tone=args.tone,
        cta=args.cta,
    )

    email_copy = generate_email_with_openai(brief, requirements)

    print("=" * 80)
    print("COMPANY BRIEF")
    print("=" * 80)
    print(brief)
    print("\n" + "=" * 80)
    print("EMAIL OUTPUT")
    print("=" * 80)
    print(email_copy)


if __name__ == "__main__":
    main()
