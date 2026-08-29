"""
Parses a single corpus markdown file into (metadata, title, body_text).

Expected file shape:

    ---
    id: "..."
    ...yaml front matter...
    ---
    # Title Line
    <blank line>
    body paragraphs...
"""
from pathlib import Path

import yaml


class ParseError(RuntimeError):
    pass


def parse_markdown_file(path):
    """Parse one corpus .md file.

    Returns:
        (metadata: dict, title: str, body_text: str)
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    if not lines or lines[0].strip() != "---":
        raise ParseError(f"{path}: expected file to start with a '---' front-matter delimiter")

    # Find the closing '---' of the front matter block.
    closing_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_index = i
            break
    if closing_index is None:
        raise ParseError(f"{path}: front matter opened with '---' but never closed")

    front_matter_raw = "\n".join(lines[1:closing_index])
    try:
        metadata = yaml.safe_load(front_matter_raw) or {}
    except yaml.YAMLError as e:
        raise ParseError(f"{path}: invalid YAML front matter ({e})")

    # Everything after the closing '---'.
    remainder = lines[closing_index + 1:]

    # Find the "# Title" heading line.
    title_index = None
    for i, line in enumerate(remainder):
        stripped = line.strip()
        if stripped.startswith("# "):
            title_index = i
            break
    if title_index is None:
        raise ParseError(f"{path}: no '# Title' heading found after front matter")

    title = remainder[title_index].strip()[2:].strip()

    # Body is everything after the title line, with leading/trailing blank lines trimmed.
    body_lines = remainder[title_index + 1:]
    body_text = "\n".join(body_lines).strip()

    return metadata, title, body_text
