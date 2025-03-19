import pytest

import auth
from azure_openai_agent import Conversation


def test_azure_openai_agent():
    cookies_path = "raw/cookies.csv"
    if auth.check_cookies_expiry(cookies_path) is False:
        auth.dump_cookies(cookies_path)
    cookies = auth.load_cookies(cookies_path)
    conv = Conversation(cookies=cookies, max_func_call_rounds=5)
    model_speaking = conv.user_speaking("搜 Minecraft Cubeez 奥克兰本周 给出帖子链接")
    print(model_speaking)


if __name__ == '__main__':
    pytest.main()
