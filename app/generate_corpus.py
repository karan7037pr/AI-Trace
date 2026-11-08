"""Generate the 20-page sourced learning corpus with Groq."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    """Turn source-backed topic briefs into JSONL pages for ingestion."""

    from groq import Groq

    input_path = Path("data/virat_kohli/topics.jsonl")
    output_path = Path("data/virat_kohli/pages.jsonl")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Export it before running this command.")

    client = Groq(api_key=api_key)
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    retrieved_at = datetime.now(timezone.utc).date().isoformat()
    pages = []

    with input_path.open(encoding="utf-8") as input_file:
        topics = [json.loads(line) for line in input_file if line.strip()]

    for topic in topics:
        source_text = "\n".join(
            f"- {source['title']}: {source['url']}" for source in topic["sources"]
        )
        prompt = f"""Write an educational page of approximately 300 words about Virat Kohli.

Title: {topic['title']}

Verified fact brief:
{topic['facts']}

Reference sources:
{source_text}

Rules:
- Use only the facts in the brief and cautious general cricket explanation.
- Do not invent exact statistics, quotes, match scores, or private-life details.
- Clearly distinguish facts from interpretation.
- Write original prose; do not copy source wording.
- Do not add a bibliography section; source metadata is stored separately.
"""
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        pages.append(
            {
                "id": f"virat-kohli-page-{topic['page_number']:02d}",
                "title": topic["title"],
                "page_number": topic["page_number"],
                "text": response.choices[0].message.content.strip(),
                "source_url": topic["sources"][0]["url"],
                "source_title": "; ".join(source["title"] for source in topic["sources"]),
                "retrieved_at": retrieved_at,
            }
        )

    output_path.write_text(
        "".join(json.dumps(page, ensure_ascii=False) + "\n" for page in pages),
        encoding="utf-8",
    )
    print(f"Generated {len(pages)} pages at {output_path}.")


if __name__ == "__main__":
    main()
