import pytest

import auth


def test_dump_cookies():
    auth.dump_cookies("raw/cookies.csv")


if __name__ == '__main__':
    pytest.main()
