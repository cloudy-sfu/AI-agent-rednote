import json
import logging
import random
import re
import time

import pandas as pd
from bs4 import BeautifulSoup

from xhshow.config import replacements
from xhshow.encrypt.misc_encrypt import x_b3_traceid, x_xray_traceid, search_id
from xhshow.encrypt.xs_encrypt import encrypt_xs
from xhshow.encrypt.xsc_encrypt import encrypt_xsc
from xhshow.extractor.extract_initial_state import extract_initial_state

with open("headers/explore.json", "r") as f:
    header_explore = json.load(f)
with open("headers/homefeed.json", "r") as f:
    header_homefeed = json.load(f)


def feed_first_page(session, cookies):
    response = session.get(
        url="https://www.xiaohongshu.com/explore",
        headers=header_explore,
        cookies=cookies,
    )
    assert response.status_code == 200, "Fail to fetch home page of xiaohongshu."
    initial_timestamp = round(time.time() * 1000)
    initial_state = extract_initial_state(response.text, replacements)
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
    return posts, initial_timestamp


def feed_subsequent_page(
        session, cookies, initial_timestamp, note_index, n, page, cursor_score):
    if page == 1:  # second page
        refresh_type = 1
    else:
        refresh_type = 3
    payload = {
        "category": "homefeed_recommend",
        "cursor_score": cursor_score,
        "image_formats": ["jpg", "webp", "avif"],
        "need_num": n - 25,
        "note_index": note_index + n * (page - 1),  # page number starts from 0
        "num": n,
        "refresh_type": refresh_type,
        "search_key": "",
        "unread_begin_note_id": "",
        "unread_end_note_id": "",
        "unread_note_count": 0,
        "need_filter_image": False,
    }
    header_ = header_homefeed.copy()
    payload_str = json.dumps(payload, separators=(',', ':'))
    logging.info(f"POST --URL /api/sns/web/v1/homefeed --Payload {payload_str}")
    current_timestamp = round(time.time() * 1000)
    sc = round((current_timestamp - initial_timestamp) / 30000)
    x_t = str(current_timestamp)
    x_b3_trace_id = x_b3_traceid()
    x_s = encrypt_xs(
        url="/api/sns/web/v1/homefeed" + payload_str,
        a1=cookies['a1'],
        ts=x_t,
        platform=cookies['xsecappid'],
    )
    x_s_common = encrypt_xsc(
        xs=x_s,
        xt=x_t,
        platform=cookies['xsecappid'],
        a1=cookies['a1'],
        x4=cookies['webBuild'],
        sc=sc,
    )
    header_['content-length'] = str(len(payload_str))
    header_['x-b3-traceid'] = x_b3_trace_id
    header_['x-s'] = x_s
    header_['x-s-common'] = x_s_common
    header_['x-t'] = x_t
    header_['x-xray-traceid'] = x_xray_traceid(x_b3_trace_id)
    response = session.post(
        url="https://edith.xiaohongshu.com/api/sns/web/v1/homefeed",
        data=payload_str,
        cookies=cookies,
        headers=header_,
    )
    assert response.status_code == 200, "Fail to fetch subsequent xiaohongshu thread."
    response_json = response.json()
    assert response_json['success'] == True, (f"Fail to fetch, website's message: "
                                              f"{response_json['msg']}.")
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


def search_page(
        session, cookies, query, page, initial_timestamp=None):
    if initial_timestamp is None:
        initial_timestamp = round(time.time() * 1000)
    header_ = header_homefeed.copy()
    current_timestamp = round(time.time() * 1000)
    payload = {
        "ext_flags": [],
        "image_formats": ["jpg", "webp", "avif"],
        "keyword": query,
        "note_type": 0,
        "page": page + 1,
        "page_size": 20,
        "search_id": search_id(current_timestamp),
        "sort": "general",
    }
    payload_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    logging.info(f"POST --URL /api/sns/web/v1/search/notes --Payload {payload_str}")

    # Build the header
    sc = round((current_timestamp - initial_timestamp) / 30000)
    x_t = str(current_timestamp)
    x_b3_trace_id = x_b3_traceid()
    x_s = encrypt_xs(
        url="/api/sns/web/v1/search/notes" + payload_str,
        a1=cookies['a1'],
        ts=x_t,
        platform=cookies['xsecappid'],
    )
    x_s_common = encrypt_xsc(
        xs=x_s,
        xt=x_t,
        platform=cookies['xsecappid'],
        a1=cookies['a1'],
        x4=cookies['webBuild'],
        sc=sc,
    )
    header_['content-length'] = str(len(payload_str))
    header_['x-b3-traceid'] = x_b3_trace_id
    header_['x-s'] = x_s
    header_['x-s-common'] = x_s_common
    header_['x-t'] = x_t
    header_['x-xray-traceid'] = x_xray_traceid(x_b3_trace_id)
    response = session.post(
        url="https://edith.xiaohongshu.com/api/sns/web/v1/search/notes",
        data=payload_str,
        cookies=cookies,
        headers=header_,
    )
    assert response.status_code == 200, \
        f"Fail to fetch searching results of page {page+1}."
    response_json = response.json()
    assert response_json['success'] == True, (f"Fail to fetch, website's message: "
                                              f"{response_json['msg']}.")
    posts = []
    if 'items' not in response_json['data'].keys():
        logging.info(f"The current page is {page+1} and no more searching results.")
        has_more = False
        return posts, has_more, initial_timestamp

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
    return posts, has_more, initial_timestamp


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
