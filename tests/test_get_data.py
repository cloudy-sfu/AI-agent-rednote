import json

import pandas as pd
import pytest

import auth
from get_data import Feed, Search, Detail

# %% Get cookies.
cookies_path = "raw/cookies.csv"
if auth.check_cookies_expiry(cookies_path) is False:
    auth.dump_cookies(cookies_path)
cookies = auth.load_cookies(cookies_path)


# %% Unit tests.
def test_feed():
    feed = Feed(cookies)
    post_1 = feed.get()
    post_2 = feed.get()
    posts = pd.concat([post_1, post_2], axis=0, ignore_index=True)
    posts.to_csv('raw/posts.csv', index=False)


def test_search():
    s = Search(cookies, "ollama")
    post_1 = s.get()
    post_2 = s.get()
    posts = pd.concat([post_1, post_2], axis=0, ignore_index=True)
    posts.to_csv('raw/posts_search.csv', index=False)


def test_detail():
    d = Detail(cookies)
    posts = pd.read_csv('raw/posts_search.csv')
    details = []
    for _, row in posts.iterrows():
        detail = d.get(row['id'], row['xsec_token'])
        details.append(detail)
    with open("raw/details.json", "w") as f:
        json.dump(details, f, indent=4, ensure_ascii=False)


def test_single_detail():
    id_ = "67da0ff2000000001c03fb94"
    xsec_token = "AB0NebdvedMrwCOk0dy4cXntIWPMW3YuuGRJzgi_vMsas="
    d = Detail(cookies)
    detail = d.get(id_, xsec_token)
    print(detail)


if __name__ == '__main__':
    pytest.main()
