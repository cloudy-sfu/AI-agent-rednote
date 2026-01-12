import json
import os
import time

import pandas as pd

cookies_csv_path = "raw/cookies.csv"


def dump_cookies(cookies_path):
    with open(cookies_path) as f:
        raw_cookies = json.load(f)
    cookies = pd.DataFrame(raw_cookies['cookies'])
    cookies.to_csv(cookies_csv_path, index=False)


def load_cookies():
    cookies = pd.read_csv(cookies_csv_path)
    cookies = {row['name']: row['value'] for _, row in cookies.iterrows()}
    # TODO: switch back to www.xiaohongshu.com cookies
    cookies['webBuild'] = '5.6.5'
    return cookies


def check_cookies():
    if not os.path.isfile(cookies_csv_path):
        return False
    cookies = pd.read_csv(cookies_csv_path)
    expiry_datetime = cookies['expirationDate'].min() + 86400
    if time.time() > expiry_datetime:  # np.False_ is not False
        return False
    return True
