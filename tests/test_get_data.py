import json
import os

import pandas as pd

import auth
from get_data import Feed, Search, Detail

# %% Get cookies.
os.makedirs("raw", exist_ok=True)
cookies_path = "raw/cookies.csv"
if auth.check_cookies(cookies_path) is False:
    auth.dump_cookies(cookies_path, cookies_path)
cookies = auth.load_cookies(cookies_path)

# %% Test feed
feed = Feed(cookies)
post_1 = feed.get()
post_2 = feed.get()
posts = pd.concat([post_1, post_2], axis=0, ignore_index=True)
posts.to_csv('raw/posts.csv', index=False)


# %% Test search
s = Search(cookies, "ollama")
post_1 = s.get()
post_2 = s.get()
posts = pd.concat([post_1, post_2], axis=0, ignore_index=True)
posts.to_csv('raw/posts_search.csv', index=False)


# %% Test details
d = Detail(cookies)
posts = pd.read_csv('raw/posts_search.csv')
details = d.get(posts['id'], posts['xsec_token'])
with open("raw/details.json", "w") as f:
    json.dump(details, f, indent=4, ensure_ascii=False)


# %% Test single detail
id_ = "685e6c57000000001203f4e2"
xsec_token = "ABKuMnH4DxdplJ6W1uuNFNHfMdhBMKLIKwUE45Z4aSTr0="
d = Detail(cookies)
detail = d.get([id_], [xsec_token])
print(detail)
