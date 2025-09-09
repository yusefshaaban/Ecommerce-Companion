#!/usr/bin/env python3

"""
normalize_text_indentation.py

Make a .txt (or code) file look consistent across editors (e.g., VS Code and Notepad)
by normalizing indentation and line endings.

Usage examples:
  # Convert tabs -> 4 spaces, set CRLF (Windows), strip trailing spaces, in-place
  python normalize_text_indentation.py input.txt --indent spaces --tabsize 4 --eol crlf --strip --in-place

  # Convert to real tabs (tab width 4 for indentation), keep LF, write to new file
  python normalize_text_indentation.py input.txt --indent tabs --tabsize 4 --eol lf -o output.txt

  # Just fix line endings and ensure a final newline
  python normalize_text_indentation.py input.txt --eol crlf --ensure-final-newline --in-place
"""
import argparse
import sys
from pathlib import Path

EOL_MAP = {
    "lf": "\n",
    "crlf": "\r\n",
    "cr": "\r",
}

def detect_line_ending(text: str) -> str:
    # Returns 'crlf', 'lf', or 'cr' based on what appears most
    crlf = text.count("\r\n")
    # count lone \r (not part of \r\n) by replacing crlf first
    cr_only = text.replace("\r\n", "").count("\r")
    lf_only = text.replace("\r\n", "").count("\n")
    if crlf >= lf_only and crlf >= cr_only:
        return "crlf"
    if lf_only >= cr_only:
        return "lf"
    return "cr"

def expand_leading_tabs_to_spaces(line: str, tabsize: int) -> str:
    # expand tabs only in the leading indentation run
    i = 0
    while i < len(line) and line[i] in ("\t", " "):
        i += 1
    return line[:i].expandtabs(tabsize) + line[i:]

def leading_spaces_to_tabs(line: str, tabsize: int) -> str:
    # Convert leading spaces to tabs (respect existing tabs)
    i = 0
    while i < len(line) and line[i] in (" ", "\t"):
        i += 1
    lead = line[:i]
    rest = line[i:]
    # First, normalize any tabs in the leading run to spaces for correct math,
    # then recompose using tabs + spaces.
    spaces_equiv = lead.expandtabs(tabsize)
    space_count = len(spaces_equiv)
    tabs = "\t" * (space_count // tabsize)
    spaces = " " * (space_count % tabsize)
    return tabs + spaces + rest

def normalize_text(
    text: str,
    indent: str,
    tabsize: int,
    eol: str | None,
    strip_trailing: bool,
    ensure_final_newline: bool,
    convert_all_tabs: bool,
) -> tuple[str, dict]:
    stats = {
        "original_eol": detect_line_ending(text) if text else "lf",
        "lines": 0,
        "tabs_to_spaces_lines": 0,
        "spaces_to_tabs_lines": 0,
        "trailing_ws_trimmed_lines": 0,
        "final_newline_added": False,
        "eol_changed": False,
    }

    # Normalize to \n for processing
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    stats["lines"] = len(lines)

    out_lines = []
    for line in lines:
        original = line

        if indent == "spaces":
            if convert_all_tabs:
                # Expand all tabs in the whole line
                line = line.expandtabs(tabsize)
            else:
                # Expand only leading tabs to spaces (indentation)
                new_line = expand_leading_tabs_to_spaces(line, tabsize)
                if new_line != line:
                    line = new_line
            if line != original:
                stats["tabs_to_spaces_lines"] += 1
        elif indent == "tabs":
            # Convert leading whitespace to tabs (indent width = tabsize)
            new_line = leading_spaces_to_tabs(line, tabsize)
            if new_line != line:
                stats["spaces_to_tabs_lines"] += 1
                line = new_line

        if strip_trailing:
            stripped = line.rstrip(" \t")
            if stripped != line:
                stats["trailing_ws_trimmed_lines"] += 1
            line = stripped

        out_lines.append(line)

    result = "\n".join(out_lines)

    # Ensure final newline
    if ensure_final_newline and (not result.endswith("\n")):
        result += "\n"
        stats["final_newline_added"] = True

    # Apply requested EOL
    if eol:
        target = EOL_MAP[eol]
        if target == "\n":
            # Already normalized above; do nothing
            pass
        else:
            # Convert current \n to target
            result = result.replace("\n", target)
        if stats["original_eol"] != eol:
            stats["eol_changed"] = True

    return result, stats

def main(argv=None):
    p = argparse.ArgumentParser(description="Normalize indentation and line endings for a text file.")
    p.add_argument("input", type=str, help="Path to the input text file")
    p.add_argument("-o", "--output", type=str, default=None, help="Path to write output (default: print or in-place)")
    p.add_argument("--in-place", action="store_true", help="Write changes back to the input file")
    p.add_argument("--indent", choices=["spaces", "tabs", "keep"], default="spaces",
                   help="Indentation policy: convert to spaces, tabs, or keep as-is (default: spaces)")
    p.add_argument("--tabsize", type=int, default=4, help="Tab width (default: 4)")
    p.add_argument("--eol", choices=["lf", "crlf", "cr"], default="crlf",
                   help="Line ending to enforce (default: crlf for Notepad)")
    p.add_argument("--strip", action="store_true", help="Strip trailing spaces/tabs from line ends")
    p.add_argument("--ensure-final-newline", action="store_true",
                   help="Ensure the file ends with a newline")
    p.add_argument("--convert-all-tabs", action="store_true",
                   help="When --indent spaces, expand ALL tabs (not just leading indent)")
    p.add_argument("--encoding", default="utf-8", help="File encoding (default: utf-8)")
    args = p.parse_args(argv)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: input file not found: {in_path}", file=sys.stderr)
        return 2

    data = in_path.read_bytes()
    try:
        text = data.decode(args.encoding, errors="replace")
    except LookupError:
        print(f"Error: unknown encoding {args.encoding}", file=sys.stderr)
        return 2

    result, stats = normalize_text(
        text=text,
        indent=args.indent,
        tabsize=args.tabsize,
        eol=args.eol,
        strip_trailing=args.strip,
        ensure_final_newline=args.ensure_final_newline,
        convert_all_tabs=args.convert_all_tabs,
    )

    # Decide output
    if args.in_place:
        out_path = in_path
    elif args.output:
        out_path = Path(args.output)
    else:
        out_path = None

    if out_path is None:
        # Print to stdout
        sys.stdout.write(result)
    else:
        out_path.write_bytes(result.encode(args.encoding, errors="replace"))
        print(f"Wrote: {out_path}")

    # Print a brief report to stderr
    report = (
        f"Lines: {stats['lines']}\n"
        f"Original EOL: {stats['original_eol']}\n"
        f"Tabs→Spaces lines: {stats['tabs_to_spaces_lines']}\n"
        f"Spaces→Tabs lines: {stats['spaces_to_tabs_lines']}\n"
        f"Trimmed trailing WS lines: {stats['trailing_ws_trimmed_lines']}\n"
        f"Final newline added: {stats['final_newline_added']}\n"
        f"EOL changed: {stats['eol_changed']}\n"
    )
    print(report, file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
