import json
import os
import time
import pandas as pd
from winapi import select_file


def dump_cookies(output_path):
    cookies_path = select_file()
    assert cookies_path, "Cookies file not chosen."
    with open(cookies_path) as f:
        cookies_dict = json.load(f)
    cookies = pd.DataFrame(cookies_dict['cookies'])
    cookies.to_csv(output_path, index=False)


def load_cookies(cookies_path):
    cookies = pd.read_csv(cookies_path)
    cookies = {row['name']: row['value'] for _, row in cookies.iterrows()}
    return cookies


def check_cookies_expiry(cookies_path):
    if not os.path.isfile(cookies_path):
        return False
    cookies = pd.read_csv(cookies_path)
    if time.time() > cookies['expirationDate'].min():  # np.False_ is not False
        return False
    return True
