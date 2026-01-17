from requests import Session

from cookies import load_cookies
from get_data import get_details_

cookies = load_cookies()
print(cookies.keys())

session = Session()
get_details_(session, cookies, ["67a187b4000000001800ff16"], ["ABWzAbp8jYBRXMEPxo_WfehHHS6PxA0QJyCLRb-T9BY1M="])
