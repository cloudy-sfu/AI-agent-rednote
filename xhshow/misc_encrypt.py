import random
import string
from collections.abc import Iterable
from numbers import Integral

lookup = [
    "Z", "m", "s", "e", "r", "b", "B", "o", "H", "Q", "t", "N", "P", "+", "w", "O", "c", "z", "a", "/", "L", "p", "n",
    "g", "G", "8", "y", "J", "q", "4", "2", "K", "W", "Y", "j", "0", "D", "S", "f", "d", "i", "k", "x", "3", "V", "T",
    "1", "6", "I", "l", "U", "A", "F", "M", "9", "7", "h", "E", "C", "v", "u", "R", "X", "5",
]


def encode_utf8(text) -> list:
    encoded = [ord(i) for i in text]
    return encoded


def decode_utf8(encoded_list) -> str:
    decoded = [chr(i) for i in encoded_list]
    return "".join(decoded)


def random_str(length: Integral) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choice(alphabet) for _ in range(length))


def base36encode(number: Integral,
                 alphabet: Iterable[str] = '0123456789abcdefghijklmnopqrstuvwxyz') -> str:
    """
    将数字转换为base36编码
    Args:
        number: 需要base36的数字
        alphabet: base36的字符集 默认: 0123456789abcdefghijklmnopqrstuvwxyz
    Returns:
        base36编码后的内容
    """
    base36 = ''
    alphabet = ''.join(alphabet)
    sign = '-' if number < 0 else ''
    number = abs(number)

    while number:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + (base36 or alphabet[0])


def b64_decode(encoded_str):
    reverse_lookup = {v: i for i, v in enumerate(lookup)}
    encoded_str = encoded_str.rstrip("=")
    decoded_bytes = []
    i = 0
    while i < len(encoded_str):
        chunk = encoded_str[i:i+4]
        if len(chunk) < 4:
            chunk += "=" * (4 - len(chunk))  # Padding if needed
        num = (reverse_lookup[chunk[0]] << 18) + (reverse_lookup[chunk[1]] << 12) + \
              (reverse_lookup.get(chunk[2], 0) << 6) + reverse_lookup.get(chunk[3], 0)
        decoded_bytes.append((num >> 16) & 0xFF)
        if chunk[2] != "=":
            decoded_bytes.append((num >> 8) & 0xFF)
        if chunk[3] != "=":
            decoded_bytes.append(num & 0xFF)
        i += 4
    return decoded_bytes


def b64_encode(e: list) -> str:
    P = len(e)
    W = P % 3
    U = []
    z = 16383
    H = 0
    Z = P - W
    while H < Z:
        U.append(encode_chunk(e, H, Z if H + z > Z else H + z))
        H += z
    if 1 == W:
        F = e[P - 1]
        U.append(lookup[F >> 2] + lookup[(F << 4) & 63] + "==")
    elif 2 == W:
        F = (e[P - 2] << 8) + e[P - 1]
        U.append(lookup[F >> 10] + lookup[63 & (F >> 4)] + lookup[(F << 2) & 63] + "=")
    return "".join(U)


def encode_chunk(e, t, r):
    m = []
    for b in range(t, r, 3):
        n = (16711680 & (e[b] << 16)) + \
            ((e[b + 1] << 8) & 65280) + (e[b + 2] & 255)
        m.append(triplet_to_base64(n))
    return ''.join(m)


def triplet_to_base64(e):
    return (
            lookup[63 & (e >> 18)] + lookup[63 & (e >> 12)] + lookup[(e >> 6) & 63] +
            lookup[e & 63]
    )


def x_b3_traceid(hex_chars="abcdef0123456789", b3_traceid_length=16) -> str:
    return "".join(random.choice(hex_chars) for _ in range(b3_traceid_length))


def search_id(timestamp: int) -> str:
    e = timestamp << 64
    t = int(random.uniform(0, 2147483646))
    return base36encode((e + t))


def x_xray_traceid(timestamp, max_seq=8388607) -> str:
    # default max_seq: 2**23-1
    seq = random.randint(0, max_seq)
    timestamp_shift = 23
    part_1_length = 16
    part_2_length = 16
    part1 = format(
        ((timestamp << timestamp_shift) | seq),
        f"0{part_1_length}x",
    )
    part_2 = x_b3_traceid(b3_traceid_length=part_2_length)
    return part1 + part_2
