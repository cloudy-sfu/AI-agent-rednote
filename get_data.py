import json
import logging
import time

import pandas as pd
from requests import Session
from selenium.webdriver import Chrome

from xhshow.config import replacements
from xhshow.encrypt.misc_encrypt import x_b3_traceid, x_xray_traceid
from xhshow.encrypt.xs_encrypt import encrypt_xs
from xhshow.encrypt.xsc_encrypt import encrypt_xsc
from xhshow.extractor.extract_initial_state import extract_initial_state

with open("headers/explore.json", "r") as f:
    header_explore = json.load(f)
with open("headers/homefeed.json", "r") as f:
    header_homefeed = json.load(f)


def set_cookies(output_path):
    chrome = Chrome()
    chrome.get("https://www.xiaohongshu.com/")
    logging.info('Please login https://www.xiaohongshu.com/ in the prompted Google '
                 'Chrome session. Do not close the session. Then, press Enter in this '
                 'terminal to continue.')
    _ = input()
    cookies = pd.DataFrame(chrome.get_cookies())
    cookies.to_csv(output_path, index=False)


def get_cookies(path):
    cookies = pd.read_csv(path)
    return {row['name']: row['value'] for _, row in cookies.iterrows()}


class Feed:
    def __init__(self, cookies):
        self.session = Session()
        self.cookies = cookies
        self.header = header_homefeed.copy()
        self.refresh_type = 1
        self.note_index = None
        self.initial_timestamp = None
        self.cursor_score = ""

    def init(self):
        """
        Initialize a "xiaohongshu" thread and get first page of posts.
        :return: pd.DataFrame table of posts' meta.
        """
        response = self.session.get(
            url="https://www.xiaohongshu.com/explore",
            headers=header_explore,
            cookies=self.cookies,
        )
        assert response.status_code == 200, "Fail to fetch home page of xiaohongshu."
        self.initial_timestamp = round(time.time() * 1000)
        initial_state = extract_initial_state(response.text, replacements)
        posts = []
        for feed in initial_state['feed']['feeds']:
            post = {
                "id": feed['id'],
                "xsec_token": feed['xsecToken'],
                "title": feed['noteCard']['displayTitle'],
                # resolution: blur, median, original (not available in feed)
                "cover_median_url": feed['noteCard']['cover']['urlDefault'],
                'user_id': feed['noteCard']['user']['userId'],
                'user_name': feed['noteCard']['user']['nickName'],
                'user_xsec_token': feed['noteCard']['user']['xsecToken'],
            }
            posts.append(post)
        posts = pd.DataFrame(posts)
        self.note_index = posts.shape[0]
        return posts

    def more(self, n):
        """
        After initialized the information thread, get more posts.
        :param n: The number of more posts to get.
        :return: pd.DataFrame table of posts' meta.
        """
        if not (self.initial_timestamp and self.note_index):
            logging.error("Run Feed.init function first.")
            return
        payload = {
            "category": "homefeed_recommend",
            "cursor_score": self.cursor_score,
            "image_formats": ["jpg", "webp", "avif"],
            "need_num": n - 25,
            "note_index": self.note_index,
            "num": n,
            "refresh_type": self.refresh_type,
            "search_key": "",
            "unread_begin_note_id": "",
            "unread_end_note_id": "",
            "unread_note_count": 0,
            "need_filter_image": False,
        }
        payload_str = json.dumps(payload, separators=(',', ':'))
        logging.info(f"POST payload {payload_str}")
        current_timestamp = round(time.time() * 1000)
        sc = round((current_timestamp - self.initial_timestamp) / 30000)
        x_t = str(current_timestamp)
        x_b3_trace_id = x_b3_traceid()
        x_s = encrypt_xs(
            url="/api/sns/web/v1/homefeed" + payload_str,
            a1=self.cookies['a1'],
            ts=x_t,
            platform=self.cookies['xsecappid'],
        )
        x_s_common = encrypt_xsc(
            xs=x_s,
            xt=x_t,
            platform=self.cookies['xsecappid'],
            a1=self.cookies['a1'],
            x4=self.cookies['webBuild'],
            sc=sc,
        )
        self.header['content-length'] = str(len(payload_str))
        self.header['x-b3-traceid'] = x_b3_trace_id
        self.header['x-s'] = x_s
        self.header['x-s-common'] = x_s_common
        self.header['x-t'] = x_t
        self.header['x-xray-traceid'] = x_xray_traceid(x_b3_trace_id)
        response = self.session.post(
            url="https://edith.xiaohongshu.com/api/sns/web/v1/homefeed",
            data=payload_str,
            cookies=self.cookies,
            headers=self.header,
        )
        assert response.status_code == 200, "Fail to fetch subsequent xiaohongshu thread."
        self.refresh_type = 3
        self.note_index += n
        response_json = response.json()
        assert response_json['success'] == True, "Fail to fetch subsequent xiaohongshu thread."
        self.cursor_score = response_json['data']['cursor_score']
        posts = []
        for item in response_json['data']['items']:
            post = {
                'id': item['id'],
                'xsec_token': item['xsec_token'],
                'title': item['note_card']['display_title'],
                'cover_median_url': item['note_card']['cover']['url_default'],
                'user_id': item['note_card']['user']['user_id'],
                'user_name': item['note_card']['user']['nick_name'],
                'user_xsec_token': item['note_card']['user']['xsec_token'],
            }
            posts.append(post)
        posts = pd.DataFrame(posts)
        return posts
