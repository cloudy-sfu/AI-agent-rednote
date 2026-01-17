import time

from requests import Session
from xhshow import Xhshow, SessionManager

from cookies import load_cookies

cookies = load_cookies()
print(cookies.keys())

session = Session()
client = Xhshow()
xhs_session = SessionManager()

payload = {
    'cursor_score': '',
    'num': 39,
    'refresh_type': 1,
    'note_index': 34,
    'unread_begin_note_id': '',
    'unread_end_note_id': '',
    'unread_note_count': 0,
    'category': 'homefeed_recommend',
    'search_key': '',
    'need_num': 14,
    'image_formats': ['jpg', 'webp', 'avif'],
    'need_filter_image': False
}
header_homefeed = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,ja;q=0.7,sw;q=0.6",
    "content-type": "application/json;charset=UTF-8",
    "dnt": "1",
    "origin": "https://www.xiaohongshu.com",
    "priority": "u=1, i",
    "referer": "https://www.xiaohongshu.com/",
    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "xy-direction": "46"
}

current_timestamp = int(time.time() * 1000)
header = client.sign_headers_post(
    uri="https://edith.xiaohongshu.com/api/sns/web/v1/homefeed",
    cookies=cookies,
    xsec_appid=cookies['xsecappid'],
    payload=payload,
    timestamp=current_timestamp,
    session=xhs_session,
)
header.update(header_homefeed)
payload_str = client.build_json_body(payload)
response = session.post(
    url="https://edith.xiaohongshu.com/api/sns/web/v1/homefeed",
    data=payload_str,
    cookies=cookies,
    headers=header,
)
print(response.status_code)
print(response.text)
