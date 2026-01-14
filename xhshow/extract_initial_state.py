import logging
import re

import demjson3
from bs4 import BeautifulSoup


def extract_initial_state(html_content: str) -> dict | None:
    """
    从HTML中的<script>标签中提取window.__INITIAL_STATE__ 解析并保存为JSON格式

    如果未找到 window.__INITIAL_STATE__ 函数会返回 None 并输出响应的HTML内容
    Args:
        html_content: html文档内容
    Returns:
        dict: 提取并格式化后的JSON数据
    """

    soup = BeautifulSoup(html_content, 'html.parser')
    script_tags = soup.find_all('script')
    pattern = re.compile(r'window\.__INITIAL_STATE__\s*=\s*({.*})', re.S)

    # 初始化初始状态字符串
    initial_state_str = None

    # 查找包含 "window.__INITIAL_STATE__" 的脚本标签
    for script_tag in script_tags:
        if script_tag.string and 'window.__INITIAL_STATE__' in script_tag.string:
            match = pattern.search(script_tag.string)
            if match:
                initial_state_str = match.group(1)
                break

    if initial_state_str:
        return demjson3.decode(initial_state_str, encoding="utf-8")
    else:
        # 如果未找到, 说明请求出问题 可能账户被特征了
        logging.error("window.__INITIAL_STATE__ not found.")
        return None
