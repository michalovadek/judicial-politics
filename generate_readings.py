#!/usr/bin/env python3
"""Generate per-week reading lists for the Judicial Politics site from a single
source of truth (references.bib + readings.yml).

Run automatically as a Quarto pre-render step, or manually: `python generate_readings.py`.

Output: _readings/weekNN.md, the partial included by each weekNN.qmd.

Dependency-free (standard library only) so it runs anywhere Quarto does.
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
BIB = os.path.join(ROOT, "references.bib")
READINGS = os.path.join(ROOT, "readings.yml")
PARTIALS_DIR = os.path.join(ROOT, "_readings")


# --------------------------------------------------------------------------- #
# BibTeX parsing
# --------------------------------------------------------------------------- #
def _match_brace(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def _read_delimited(body, i):
    """Read a {braced} or "quoted" value starting at body[i]; return (value, next_i)."""
    if body[i] == "{":
        end = _match_brace(body, i)
        return body[i + 1:end], end + 1
    if body[i] == '"':
        j = i + 1
        while j < len(body):
            if body[j] == '"' and body[j - 1] != "\\":
                break
            j += 1
        return body[i + 1:j], j + 1
    j = i
    while j < len(body) and body[j] not in ",\n":
        j += 1
    return body[i:j].strip(), j


def _clean(value):
    value = value.replace("{", "").replace("}", "")
    repl = {
        "\\textquotedblleft": "“", "\\textquotedblright": "”",
        "\\textquoteleft": "‘", "\\textquoteright": "’",
        "\\textemdash": "—", "\\textendash": "–",
        "\\&": "&", "\\%": "%", "\\$": "$", "\\_": "_", "\\#": "#",
    }
    for k, v in repl.items():
        value = value.replace(k, v)
    value = value.replace("~", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _parse_fields(body):
    fields = {}
    i, n = 0, len(body)
    while i < n:
        while i < n and body[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        eq = body.find("=", i)
        if eq == -1:
            break
        name = body[i:eq].strip().lower()
        i = eq + 1
        while i < n and body[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        raw, i = _read_delimited(body, i)
        fields[name] = _clean(raw)
    return fields


def parse_bib(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    entries = {}
    i = 0
    while True:
        at = text.find("@", i)
        if at == -1:
            break
        brace = text.find("{", at)
        if brace == -1:
            break
        entrytype = text[at + 1:brace].strip().lower()
        end = _match_brace(text, brace)
        if entrytype in ("comment", "preamble", "string"):
            i = end + 1
            continue
        comma = text.find(",", brace)
        key = text[brace + 1:comma].strip()
        fields = _parse_fields(text[comma + 1:end])
        fields["entrytype"] = entrytype
        entries[key] = fields
        i = end + 1
    return entries


# --------------------------------------------------------------------------- #
# readings.yml parsing (minimal: our known flat schema, inline [key, key] lists)
# --------------------------------------------------------------------------- #
def parse_readings(path):
    weeks = []
    cur = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#") or s == "weeks:":
                continue
            m = re.match(r"-\s*num:\s*[\"']?([^\"']+)[\"']?", s)
            if m:
                if cur:
                    weeks.append(cur)
                cur = {"num": m.group(1).strip(), "title": "", "mandatory": [], "optional": []}
                continue
            if cur is None:
                continue
            m = re.match(r"title:\s*[\"']?(.*?)[\"']?\s*$", s)
            if m:
                cur["title"] = m.group(1).strip()
                continue
            m = re.match(r"(mandatory|optional):\s*\[(.*)\]", s)
            if m:
                keys = [k.strip().strip("\"'") for k in m.group(2).split(",") if k.strip()]
                cur[m.group(1)] = keys
                continue
    if cur:
        weeks.append(cur)
    return weeks


# --------------------------------------------------------------------------- #
# Chicago-ish formatting
# --------------------------------------------------------------------------- #
def _format_names(field):
    """BibTeX 'Last, First and Last2, First2' -> Chicago author string (no trailing period)."""
    names = [n.strip() for n in re.split(r"\s+and\s+", field) if n.strip()]
    formatted = []
    for idx, name in enumerate(names):
        if name.lower() in ("others", "et al", "et al."):
            formatted.append("et al.")
            continue
        if "," in name:
            last, first = [p.strip() for p in name.split(",", 1)]
        else:
            parts = name.split()
            last, first = (parts[-1], " ".join(parts[:-1])) if len(parts) > 1 else (name, "")
        formatted.append(f"{last}, {first}".strip().rstrip(",") if idx == 0 else f"{first} {last}".strip())
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, and {formatted[1]}"
    return ", ".join(formatted[:-1]) + ", and " + formatted[-1]


def _authors(entry):
    if entry.get("author"):
        return _format_names(entry["author"])
    if entry.get("editor"):
        return _format_names(entry["editor"]) + ", eds."
    return ""


def _doi_url(entry):
    if entry.get("doi"):
        return "https://doi.org/" + entry["doi"]
    if entry.get("url"):
        return entry["url"]
    return ""


def format_citation(entry):
    """Full Chicago-style citation for a week page (with trailing DOI link if present)."""
    who = _authors(entry)
    year = entry.get("year", "n.d.")
    title = entry.get("title", "").rstrip(".")
    etype = entry.get("entrytype", "article")
    lead = "" if not who else (f"{who} " if who.rstrip().endswith(".") else f"{who}. ")
    tp = "" if title and title[-1] in "?!" else "."
    if etype in ("book", "collection") or (etype == "misc" and entry.get("publisher")):
        pub = entry.get("publisher", "")
        out = f"{lead}*{title}*{tp} {pub}, {year}."
    elif etype in ("incollection", "inbook", "inproceedings"):
        book = entry.get("booktitle", "")
        pub = entry.get("publisher", "")
        pages = entry.get("pages", "").replace("--", "-")
        tail = f", {pages}" if pages else ""
        out = f"{lead}\"{title}{tp}\" In *{book}*{tail}. {pub}, {year}."
    else:  # article
        journal = entry.get("journal", "")
        vol = entry.get("volume", "")
        num = entry.get("number", "")
        pages = entry.get("pages", "").replace("--", "-")
        loc = f"*{journal}*"
        if vol:
            loc += f" {vol}"
        if num:
            loc += f", no. {num}"
        loc += f" ({year})"
        if pages:
            loc += f": {pages}"
        out = f"{lead}\"{title}{tp}\" {loc}."
    url = _doi_url(entry)
    if url:
        out += f" {url}"
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    bib = parse_bib(BIB)
    weeks = parse_readings(READINGS)
    os.makedirs(PARTIALS_DIR, exist_ok=True)

    missing = []

    def lookup(key):
        if key not in bib:
            missing.append(key)
            return None
        return bib[key]

    for wk in weeks:
        num = wk["num"]
        # week partial
        lines = ["## Mandatory readings", ""]
        for key in wk["mandatory"]:
            e = lookup(key)
            if e:
                lines.append(format_citation(e))
                lines.append("")
        lines += ["## Optional readings", ""]
        for key in wk["optional"]:
            e = lookup(key)
            if e:
                lines.append(format_citation(e))
                lines.append("")
        with open(os.path.join(PARTIALS_DIR, f"week{num}.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines).rstrip() + "\n")

    if missing:
        print("WARNING: keys not found in references.bib:", ", ".join(sorted(set(missing))))
    print(f"Generated {len(weeks)} week partials in _readings/.")


if __name__ == "__main__":
    main()
