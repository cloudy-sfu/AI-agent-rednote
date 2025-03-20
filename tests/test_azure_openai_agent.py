import pytest

import auth
from azure_openai_agent import Conversation


def test_azure_openai_agent():
    cookies_path = "raw/cookies.csv"
    cookies = auth.load_cookies(cookies_path)
    conv = Conversation(cookies=cookies, max_func_call_rounds=5)
    conv.answer_query("搜 Minecraft Cubeez 奥克兰本周 给出帖子链接")
    print(conv.messages)


if __name__ == '__main__':
    pytest.main()
