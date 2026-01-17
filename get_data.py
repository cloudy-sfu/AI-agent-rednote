import json
import logging
import random
import re
import time

import pandas as pd
from bs4 import BeautifulSoup
from xhshow import Xhshow, SessionManager, CryptoConfig

from xhshow_contrib import extract_initial_state, search_id

with open("headers/explore.json", "r") as f:
    header_explore = json.load(f)
with open("headers/homefeed.json", "r") as f:
    header_homefeed = json.load(f)
with open("headers/search.json", "r") as f:
    header_search = json.load(f)
# Humans use the same browser to visit any page of xiaohongshu.com forum, so user-agent
# should be the same.
assert header_explore['user-agent'] == header_homefeed['user-agent'] == header_search ['user-agent'], \
    ("Source code check fails, because user agent of explore & homefeed & search header are "
     "not unified.")
client_config = CryptoConfig().with_overrides(
    PUBLIC_USERAGENT=header_explore['user-agent']
)
client = Xhshow(config=client_config)
# Intermediate constant may be generated
xhs_session = SessionManager()


def feed_first_page(session, cookies):
    current_timestamp = int(time.time() * 1000)
    header = client.sign_headers_get(
        uri="https://www.xiaohongshu.com/explore",
        cookies=cookies,
        xsec_appid=cookies['xsecappid'],
        timestamp=current_timestamp,
        session=xhs_session,
    )
    header.update(header_explore)
    response = session.get(
        url="https://www.xiaohongshu.com/explore",
        headers=header,
        cookies=cookies,
    )
    assert response.status_code == 200, "Fail to fetch home page of xiaohongshu."
    initial_state = extract_initial_state(response.text)
    posts = []
    for feed in initial_state['feed']['feeds']:
        post = {
            "id": feed['id'],
            "xsec_token": feed['xsecToken'],
            # no title is possible
            "title": feed['noteCard'].get('displayTitle', ''),
            # resolution: blur, median, original (not available in feed)
            "cover_median_url": feed['noteCard']['cover']['urlDefault'],
            'user_id': feed['noteCard']['user']['userId'],
            'user_name': feed['noteCard']['user']['nickName'],
            'user_xsec_token': feed['noteCard']['user']['xsecToken'],
        }
        posts.append(post)
    time.sleep(random.uniform(0.7, 1.3))
    return posts


def feed_subsequent_page(session, cookies, note_index, page, cursor_score):
    if page == 1:  # second page
        refresh_type = 1
    else:
        refresh_type = 3
    current_timestamp = int(time.time() * 1000)
    payload = {
        "cursor_score": cursor_score,
        "num": 39,
        "refresh_type": refresh_type,
        "note_index": note_index + 39 * (page - 1),  # page number starts from 0
        "unread_begin_note_id": "",
        "unread_end_note_id": "",
        "unread_note_count": 0,
        "category": "homefeed_recommend",
        "search_key": "",
        "need_num": 14,
        "image_formats": ["jpg", "webp", "avif"],
        "need_filter_image": False,
    }

    header = client.sign_headers_post(
        uri="https://edith.xiaohongshu.com/api/sns/web/v1/homefeed",
        cookies=cookies,
        xsec_appid=cookies['xsecappid'],
        payload=payload,
        timestamp=current_timestamp,
        session=xhs_session,
    )
    header.update(header_homefeed)
    logging.info(f"POST --URL /api/sns/web/v1/homefeed --Payload {payload}")
    payload_str = client.build_json_body(payload)

    response = session.post(
        url="https://edith.xiaohongshu.com/api/sns/web/v1/homefeed",
        data=payload_str,
        cookies=cookies,
        headers=header,
    )
    assert response.status_code == 200, \
        (f"Fail to fetch xiaohongshu thread. Page: {page} (starts from 0). "
         f"Status code: {response.status_code}. Text: {response.text}")
    response_json = response.json()
    assert response_json['success'] == True, \
        f"Fail to fetch, website's message: {response_json['msg']}."
    cursor_score = response_json['data']['cursor_score']
    posts = []
    for item in response_json['data']['items']:
        post = {
            'id': item['id'],
            'xsec_token': item['xsec_token'],
            'title': item['note_card'].get('display_title', ''),
            'cover_median_url': item['note_card']['cover']['url_default'],
            'user_id': item['note_card']['user']['user_id'],
            'user_name': item['note_card']['user']['nick_name'],
            'user_xsec_token': item['note_card']['user']['xsec_token'],
        }
        posts.append(post)
    time.sleep(random.uniform(0.7, 1.3))
    return posts, cursor_score


def search_page(session, cookies, query, page):
    current_timestamp = int(time.time() * 1000)
    payload = {
        "keyword": query,
        "page": page + 1,
        "page_size": 20,
        "search_id": search_id(current_timestamp),
        "sort": "general",
        "note_type": 0,
        "ext_flags": [],
        "filters": [{"tags": ["general"], "type": "sort_type"},
                    {"tags": ["不限"], "type": "filter_note_type"},
                    {"tags": ["不限"], "type": "filter_note_time"},
                    {"tags": ["不限"], "type": "filter_note_range"},
                    {"tags": ["不限"], "type": "filter_pos_distance"}],
        "geo": "",
        "image_formats": ["jpg", "webp", "avif"],
    }

    header = client.sign_headers_post(
        uri="https://edith.xiaohongshu.com/api/sns/web/v1/search/notes",
        cookies=cookies,
        xsec_appid=cookies['xsecappid'],
        payload=payload,
        timestamp=current_timestamp,
        session=xhs_session,
    )
    header.update(header_search)
    logging.info(f"POST --URL /api/sns/web/v1/search/notes --Payload {payload}")
    payload_str = client.build_json_body(payload)

    response = session.post(
        url="https://edith.xiaohongshu.com/api/sns/web/v1/search/notes",
        data=payload_str,
        cookies=cookies,
        headers=header,
    )
    assert response.status_code == 200, \
        f"Fail to fetch searching results of page {page+1}."
    response_json = response.json()
    assert response_json['success'] == True, \
        f"Fail to fetch, website's message: {response_json['msg']}."
    posts = []
    if 'items' not in response_json['data'].keys():
        logging.info(f"The current page is {page+1} and no more searching results.")
        has_more = False
        return posts, has_more

    for item in response_json['data']['items']:
        if not item['model_type'] == 'note':
            continue
        post = {
            'id': item['id'],
            'xsec_token': item['xsec_token'],
            # no title is possible
            'title': item['note_card'].get('display_title', ''),
            'cover_median_url': item['note_card']['cover']['url_default'],
            'user_id': item['note_card']['user']['user_id'],
            'user_name': item['note_card']['user']['nick_name'],
            'user_xsec_token': item['note_card']['user']['xsec_token'],
        }
        posts.append(post)
    has_more = response_json['data']['has_more']
    time.sleep(random.uniform(0.7, 1.3))
    return posts, has_more


def get_details_(session, cookies, id_list: list[str], xsec_token_list: list[str]):
    results = []
    for id_, xsec_token in zip(id_list, xsec_token_list):
        url = f"https://www.xiaohongshu.com/explore/{id_}?xsec_token={xsec_token}"
        response = session.get(url, cookies=cookies, headers=header_explore)
        assert response.status_code == 200, \
            f"Fail to fetch the post's detail from xiaohongshu. URL: {url}"
        logging.info(f"GET --URL {url}")
        tree = BeautifulSoup(response.text, "html.parser")
        images = [
            image.get('content')
            for image in tree.find_all('meta', {'name': 'og:image'})
        ]

        initial_state_regex = re.compile("window.__INITIAL_STATE__")
        script_tag = tree.find("script", string=initial_state_regex)
        script_text = script_tag.text
        script_text = re.sub("window.__INITIAL_STATE__=", "", script_text)
        script_text = re.sub("undefined", "null", script_text)
        initial_state = json.loads(script_text)

        try:
            note = initial_state['note']['noteDetailMap'][id_]['note']
        except KeyError:
            logging.warning(f"Post {url} does not exist.")
            continue
        published_time_stamp = note.get('time')
        if published_time_stamp:
            published_time = pd.Timestamp(
                published_time_stamp, unit='ms', tz='Asia/Shanghai')
            published_time = published_time.strftime("%Y-%m-%d %H:%M:%S %z")
        else:
            published_time = ''
        results.append({
            "url": url,
            "title": note.get('title', ''),
            "description": note.get('desc', ''),
            "images": images,
            "labels": [a.get('name', '') for a in note.get('tagList')],
            "location": note.get('ipLocation', ''),
            "published_time": published_time
        })
    return results
