import logging
import os
import sys

import pandas as pd

from get_data import get_cookies, set_cookies, Feed

# %% Login "xiaohongshu" account.
logging.basicConfig(level=logging.INFO, format='%(levelname).1s %(message)s',
                    stream=sys.stdout)
cookies_path = "raw/cookies.csv"
if not os.path.isfile(cookies_path):
    set_cookies(cookies_path)
cookies = get_cookies(cookies_path)

# %%
feed = Feed(cookies)
posts_1 = feed.init()
posts_2 = feed.more(15)
posts = pd.concat([posts_1, posts_2], axis=0, ignore_index=True)
posts.to_csv('raw/posts.csv', index=False)
