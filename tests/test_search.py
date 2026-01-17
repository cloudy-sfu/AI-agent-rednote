from requests import Session

from cookies import load_cookies
from get_data import search_page

cookies = load_cookies()
print(cookies.keys())

session = Session()
search_page(session, cookies, "cherry studio", 0)
