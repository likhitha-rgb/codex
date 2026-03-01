# AI Email Campaign Generator

This project is a starter app for generating email-marketing copy from a company's website.

## What it does

1. Accepts a company website URL.
2. Crawls pages in the same domain (optionally subdomains).
3. Extracts readable text and metadata.
4. Builds a compact company brief.
5. Generates campaign emails from requirements (goal, audience, tone, CTA, etc.).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/email_campaign_app.py \
  --url https://example.com \
  --campaign-goal "Book product demos" \
  --audience "SMB founders" \
  --tone "Professional and friendly" \
  --cta "Schedule a 20-minute call" \
  --max-pages 15
```

If `OPENAI_API_KEY` is set, the app will use an LLM for richer email output. Without it, it falls back to deterministic template generation.

## Roadmap suggestions

- Add robots.txt and crawl-delay awareness.
- Add sitemap parsing and queue prioritization.
- Add vector search over crawled content.
- Add user auth and campaign history in a database.
- Add A/B testing and delivery integrations.

## Notes

- Crawl responsibly and respect website terms.
- For production use, add retries, rate limits, and content quality checks.
