from typing import Union


class SizeError(Exception):
    pass


def split_with_limit(text: str, delimiters: str, limit: int) -> list[str]:
    sections = []

    cur = 0
    i = 0
    while True:
        if len(text) - cur <= limit:
            sections.append(text[cur:len(text)])
            return sections
        
        jump = limit - 1
        i += jump

        # backtrack
        while i >= cur and text[i] not in delimiters:
            i -= 1
        
        if i == cur - 1:
            raise SizeError("Text contains too large a section.")

        sections.append(text[cur:i + 1])

        i += 1
        cur = i
