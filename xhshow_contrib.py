# Ref: https://github.com/Cloxl/xhshow/issues/49
import json
import random
import re
import string

from bs4 import BeautifulSoup


def extract_initial_state(html_content: str) -> dict | None:
    """
    Extract window.__INITIAL_STATE__ from HTML and convert to JSON.
    Args:
        html_content:

    Returns:

    """
    soup = BeautifulSoup(html_content, "html.parser")

    for script in soup.find_all("script"):
        if not script.string or "window.__INITIAL_STATE__" not in script.string:
            continue

        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*({.*})", script.string, re.S
        )
        if not match:
            continue

        # Extract raw Javascript object
        js_str = match.group(1)
        stack = []
        for i, char in enumerate(js_str):
            if char == "{":
                stack.append(char)
            elif char == "}":
                stack.pop()
                if not stack:
                    js_str = js_str[: i + 1]
                    break

        # Convert to valid JSON
        js_str = (
            js_str.replace("undefined", "null")
            .replace("True", "true")
            .replace("False", "false")
            .replace("None", "null")
        )

        # Handle single quote
        js_str = re.sub(r"'([^']*?)'(\s*:)", r'"\1"\2', js_str)
        js_str = re.sub(
            r":\s*'([^']*?)'",
            lambda m: ': "' + m.group(1).replace('"', '\\"') + '"',
            js_str,
        )
        return json.loads(js_str)
    return None


def base36encode(number) -> str:
    base36 = ''
    alphabet = ''.join(string.digits + string.ascii_lowercase)
    sign = '-' if number < 0 else ''
    number = abs(number)
    while number:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36
    return sign + (base36 or alphabet[0])


def search_id(timestamp: int) -> str:
    e = timestamp << 64
    t = int(random.uniform(0, 2 ** 31 - 1))
    return base36encode((e + t))
