import json
import os
import time
from argparse import ArgumentParser

import pandas as pd

cookies_csv_path = "raw/cookies.csv"


def dump_cookies(cookies_path):
    with open(cookies_path) as f:
        raw_cookies = json.load(f)
    cookies = pd.DataFrame(raw_cookies['cookies'])
    cookies.to_csv(cookies_csv_path, index=False)


def load_cookies():
    if not os.path.isfile(cookies_csv_path):
        raise Exception("Cookies file doesn't exist.")
    cookies = pd.read_csv(cookies_csv_path)
    expiry_datetime = cookies['expirationDate'].min() + 86400
    if time.time() > expiry_datetime:
        raise Exception("Cookies expired. ")
    cookies = {row['name']: row['value'] for _, row in cookies.iterrows()}
    return cookies


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--input_path", required=True)
    cmd, _ = parser.parse_known_args()

    try:
        dump_cookies(cmd.input_path)
    except FileNotFoundError:
        raise Exception(
            f"Cookies file not found at {cmd.input_path}")
    except json.JSONDecodeError:
        raise Exception("The provided cookies file cannot be parsed. Please set the file "
                        "path in environment variables of MCP server config page and restart "
                        "MCP server again.")
