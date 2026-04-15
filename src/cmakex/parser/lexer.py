"""Lexer for CMake files — handles comments, strings, and command extraction."""

from __future__ import annotations

import re
from typing import Iterator, List, Tuple


class CMakeLexer:
    """Lexical analyzer for CMake files."""

    def __init__(self, text: str):
        """Initialize lexer with CMake source text."""
        self.text = text

    def strip_comments(self) -> str:
        """Remove CMake line and bracket comments, preserving quoted/bracket strings."""
        out: List[str] = []
        i = 0
        n = len(self.text)

        while i < n:
            ch = self.text[i]

            # Double-quoted string — pass through verbatim
            if ch == '"':
                j = i + 1
                while j < n:
                    if self.text[j] == "\\":
                        j += 2
                        continue
                    if self.text[j] == '"':
                        j += 1
                        break
                    j += 1
                out.append(self.text[i:j])
                i = j
                continue

            # Bracket string [[...]] or [=[...]=] — pass through verbatim
            if ch == "[":
                m = re.match(r"\[=*\[", self.text[i:])
                if m:
                    open_b = m.group()
                    level = len(open_b) - 2
                    close_b = "]" + "=" * level + "]"
                    j = self.text.find(close_b, i + len(open_b))
                    end = (j + len(close_b)) if j != -1 else n
                    out.append(self.text[i:end])
                    i = end
                    continue

            # Comment (line or bracket)
            if ch == "#":
                m = re.match(r"#(\[=*\[)", self.text[i:])
                if m:
                    # Bracket comment — preserve newlines for line-number accuracy
                    open_b = m.group(1)
                    level = len(open_b) - 2
                    close_b = "]" + "=" * level + "]"
                    j = self.text.find(close_b, i + len(m.group()))
                    end = (j + len(close_b)) if j != -1 else n
                    out.append("\n" * self.text[i:end].count("\n"))
                    i = end
                else:
                    # Line comment — skip to end of line
                    while i < n and self.text[i] != "\n":
                        i += 1
                continue

            out.append(ch)
            i += 1

        return "".join(out)

    @staticmethod
    def find_close_paren(text: str, start: int) -> int:
        """Return index of char immediately after the matching ')'.

        *start* is the index of the first character inside the opening '('.
        """
        depth = 1
        i = start
        n = len(text)
        while i < n and depth > 0:
            ch = text[i]
            if ch == '"':
                i += 1
                while i < n and text[i] != '"':
                    if text[i] == "\\":
                        i += 1
                    i += 1
                i += 1  # skip closing "
            elif ch == "(":
                depth += 1
                i += 1
            elif ch == ")":
                depth -= 1
                i += 1
            else:
                i += 1
        return i

    def extract_commands(self) -> Iterator[Tuple[str, str]]:
        """Yield (command_name, raw_args_text) pairs from cmake source text."""
        text = self.strip_comments()
        cmd_re = re.compile(r"\b([A-Za-z_]\w*)\s*\(", re.MULTILINE)
        pos = 0
        while True:
            m = cmd_re.search(text, pos)
            if not m:
                break
            cmd_name = m.group(1)
            args_start = m.end()  # index after '('
            args_end = self.find_close_paren(text, args_start)  # index after ')'
            raw_args = text[args_start : args_end - 1]
            yield cmd_name, raw_args
            pos = args_end

    @staticmethod
    def parse_args(raw: str) -> List[str]:
        """Split raw argument text (between parentheses) into individual tokens."""
        tokens: List[str] = []
        cur: List[str] = []
        i = 0
        n = len(raw)
        in_quote = False

        while i < n:
            ch = raw[i]
            if ch == '"' and not in_quote:
                in_quote = True
                i += 1
            elif ch == '"' and in_quote:
                in_quote = False
                i += 1
            elif in_quote:
                if ch == "\\" and i + 1 < n:
                    nc = raw[i + 1]
                    cur.append({"n": "\n", "t": "\t", "r": "\r"}.get(nc, nc))
                    i += 2
                else:
                    cur.append(ch)
                    i += 1
            elif ch in " \t\n\r":
                if cur:
                    tokens.append("".join(cur))
                    cur = []
                i += 1
            elif ch == ";":  # CMake list separator
                if cur:
                    tokens.append("".join(cur))
                    cur = []
                i += 1
            else:
                cur.append(ch)
                i += 1

        if cur:
            tokens.append("".join(cur))
        return [t for t in tokens if t]
