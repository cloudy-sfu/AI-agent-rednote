import json
import os

from requests import Session

from cookies import dump_cookies, check_cookies, load_cookies
from get_data import feed_first_page

try:
    dump_cookies(os.environ["xiaohongshu_cookies_path"])
except FileNotFoundError:
    raise Exception(f"Cookies file not found at {os.environ["xiaohongshu_cookies_path"]}")
except json.JSONDecodeError:
    raise Exception("The provided cookies file cannot be parsed. Please set the file "
                    "path in environment variables of MCP server config page and restart "
                    "MCP server again.")
else:
    cookies_is_valid = check_cookies()
    if cookies_is_valid:
        cookies = load_cookies()
    else:
        raise Exception("Rednote cookies is invalid. Please set the file path in "
                        "environment variables of MCP server config page and restart "
                        "MCP server again.")

session = Session()
feed_first_page(session, cookies)
