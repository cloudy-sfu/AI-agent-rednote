from requests import Session

from cookies import load_cookies
from get_data import feed_subsequent_page, feed_first_page
import time

cookies = load_cookies()
current_timestamp = int(time.time() * 1000)
session = Session()
feed_first_page(session, cookies)
feed_subsequent_page(
    session=session,
    cookies=cookies,
    note_index=34,
    page=1,
    cursor_score=""
)
