import hashlib
import json
import random
import secrets
import struct
import base64
from Crypto.Cipher import ARC4
from urllib.parse import quote
from xhshow.crc32_encrypt import CRC32


def build_content_string(method, uri, payload=None) -> str:
    """
    Build content string (used for MD5 calculation and signature generation)

    Args:
        method: Request method ("GET" or "POST")
        uri: Request URI (without query parameters)
        payload: Request parameters

    Returns:
        str: Built content string
    """
    payload = payload or {}

    if method.upper() == "POST":
        return uri + json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    else:
        if not payload:
            return uri
        else:
            # XHS signature algorithm requires only '=' to be encoded as '%3D',
            # other characters (including ',') should remain unencoded
            params = [
                f"{key}={(','.join(str(v) for v in value) 
                          if isinstance(value, list | tuple) else (
                    str(value) if value is not None else ''))
                .replace('=', '%3D')}"
                # noqa: E501
                for key, value in payload.items()
            ]
            return f"{uri}?{'&'.join(params)}"


def xor_transform_array(source_integers: list[int]) -> bytearray:
    """
    Perform XOR transformation on integer array

    Args:
        source_integers (list[int]): Source integer array

    Returns:
        bytearray: Transformed byte array
    """
    result_bytes = bytearray(len(source_integers))
    HEX_KEY = ("71a302257793271ddd273bcee3e4b98d9d7935e1da33f5765e2ea8afb6dc77a51a499d23b"
               "67c20660025860cbf13d4540d92497f58686c574e508f46e1956344f39139bf4faf22a3e"
               "ef120b79258145b2feb5193b6478669961298e79bedca646e1a693a926154a5a7a1bd1cf"
               "0dedb742f917a747a1e388b234f2277")  # noqa: E501
    key_bytes = bytes.fromhex(HEX_KEY)
    key_length = len(key_bytes)

    for index in range(len(source_integers)):
        if index < key_length:
            result_bytes[index] = (source_integers[index] ^ key_bytes[index]) & 0xFF
        else:
            result_bytes[index] = source_integers[index] & 0xFF

    return result_bytes


def encode_x3(input_bytes: bytes | bytearray) -> str:
    """
    Encode x3 signature using X3_BASE64_ALPHABET

    Args:
        input_bytes: Input byte data

    Returns:
        str: Base64 encoded string with X3 custom alphabet
    """
    standard_encoded_bytes = base64.b64encode(input_bytes)
    standard_encoded_string = standard_encoded_bytes.decode("utf-8")

    standard_base64_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    x3_base64_alphabet = "MfgqrsbcyzPQRStuvC7mn501HIJBo2DEFTKdeNOwxWXYZap89+/A4UVLhijkl63G"
    _x3_encode_table = str.maketrans(
        standard_base64_alphabet,
        x3_base64_alphabet,
    )
    return standard_encoded_string.translate(_x3_encode_table)


def encode(data_to_encode) -> str:
    """
    Encode a string using custom Base64 alphabet

    Args:
        data_to_encode: Original UTF-8 string to be encoded

    Returns:
        Base64 string encoded using custom alphabet
    """
    if isinstance(data_to_encode, bytes | bytearray):
        data_bytes = data_to_encode
    elif isinstance(data_to_encode, str):
        data_bytes = data_to_encode.encode("utf-8")
    else:
        # Iterable[int] case
        data_bytes = bytearray(data_to_encode)
    standard_encoded_bytes = base64.b64encode(data_bytes)
    standard_encoded_string = standard_encoded_bytes.decode("utf-8")
    standard_base64_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    custom_base64_alphabet = "ZmserbBoHQtNP+wOcza/LpngG8yJq42KWYj0DSfdikx3VT16IlUAFM97hECvuRX5"
    _custom_encode_table = str.maketrans(
        standard_base64_alphabet,
        custom_base64_alphabet,
    )
    return standard_encoded_string.translate(_custom_encode_table)

def sign_xs(method, uri, a1_value, xsec_appid, payload, timestamp):
    """
    Generate request signature (supports GET and POST)

    Args:
        method: Request method ("GET" or "POST")
        uri: Request URI or full URL
            - URI only: "/api/sns/web/v1/user_posted"
            - Full URL: "https://edith.xiaohongshu.com/api/sns/web/v1/user_posted"
            - Full URL with query: "https://edith.xiaohongshu.com/api/sns/web/v1/user_posted?num=30"
        a1_value: a1 value from cookies
        xsec_appid: Application identifier, defaults to `xhs-pc-web`
        payload: Request parameters
            - GET request: params value
            - POST request: payload value
        timestamp: Unix timestamp in seconds (defaults to current time)

    Returns:
        str: Complete signature string

    Raises:
        TypeError: Parameter type error
        ValueError: Parameter value error
    """
    signature = {
        "x0": "4.2.6",  # data SDK version
        "x1": xsec_appid,
        "x2": "Windows",
        "x3": "",
        "x4": "",
    }
    x3_prefix = "mns0301_"
    xys_prefix = "XYS_"

    content_string = build_content_string(method, uri, payload)

    d_value = hashlib.md5(content_string.encode("utf-8")).hexdigest()

    # --- Constants & Configuration ---
    VERSION_BYTES = [1, 0, 0]  # Assuming version 1.0.0 based on context
    ENV_FINGERPRINT_XOR_KEY = 2
    CHECKSUM_VERSION = 1
    CHECKSUM_XOR_KEY = 115
    CHECKSUM_FIXED_TAIL = [249, 65, 103, 103, 201, 181, 131, 99, 94, 7, 68, 250, 132, 21]

    # --- 1. Version ---
    part_version = VERSION_BYTES
    # --- 2. Seed (Random Integer) ---
    seed = int(random.random() * 2147483647)
    # Inline _int_to_le_bytes(seed, 4)
    part_seed = [
        seed & 0xFF,
        (seed >> 8) & 0xFF,
        (seed >> 16) & 0xFF,
        (seed >> 24) & 0xFF
    ]
    seed_byte_0 = part_seed[0]
    # --- 3. Environment Fingerprint A (Encrypted Timestamp) ---
    ts_ms = int(timestamp * 1000)
    # Inline env_fingerprint_a
    data_a = bytearray(struct.pack("<Q", ts_ms))
    sum1 = sum(data_a[1:5])
    sum2 = sum(data_a[5:8])
    mark = ((sum1 & 0xFF) + sum2) & 0xFF
    data_a[0] = mark
    part_env_a = [b ^ ENV_FINGERPRINT_XOR_KEY for b in data_a]
    # --- 4. Environment Fingerprint B (Offset Timestamp) ---
    # Random byte range: 5 to 255 (simulating config ENV_FINGERPRINT_TIME_OFFSET)
    time_offset = random.randint(5, 255)
    ts_ms_offset = int((timestamp - time_offset) * 1000)
    # Inline env_fingerprint_b
    part_env_b = list(struct.pack("<Q", ts_ms_offset))
    # --- 5. Sequence Value ---
    # Random byte range: 0 to 255 (simulating config SEQUENCE_VALUE)
    sequence_value = random.randint(0, 255)
    part_sequence = [
        sequence_value & 0xFF,
        (sequence_value >> 8) & 0xFF,
        (sequence_value >> 16) & 0xFF,
        (sequence_value >> 24) & 0xFF
    ]
    # --- 6. Window Props Length ---
    # Random byte range: 0 to 255 (simulating config WINDOW_PROPS_LENGTH)
    window_props_length = random.randint(0, 255)
    part_window_props = [
        window_props_length & 0xFF,
        (window_props_length >> 8) & 0xFF,
        (window_props_length >> 16) & 0xFF,
        (window_props_length >> 24) & 0xFF
    ]
    # --- 7. URI Length ---
    uri_length = len(content_string)
    part_uri_len = [
        uri_length & 0xFF,
        (uri_length >> 8) & 0xFF,
        (uri_length >> 16) & 0xFF,
        (uri_length >> 24) & 0xFF
    ]
    # --- 8. MD5 XOR Segment ---
    md5_bytes = bytes.fromhex(d_value)
    # Take first 8 bytes and XOR with seed_byte_0
    part_md5 = [b ^ seed_byte_0 for b in md5_bytes[:8]]
    # --- 9. A1 (Cookie) ---
    part_a1_len = [52]
    a1_bytes = a1_value.encode("utf-8")
    if len(a1_bytes) > 52:
        part_a1_content = list(a1_bytes[:52])
    else:
        part_a1_content = list(a1_bytes) + [0] * (52 - len(a1_bytes))
    # --- 10. Source (App ID) ---
    part_source_len = [10]
    source_bytes = xsec_appid.encode("utf-8")
    if len(source_bytes) > 10:
        part_source_content = list(source_bytes[:10])
    else:
        part_source_content = list(source_bytes) + [0] * (10 - len(source_bytes))
    # --- 11. Tail / Checksum ---
    part_tail_start = [1]
    part_checksum_ver = [CHECKSUM_VERSION]
    part_checksum_xor = [seed_byte_0 ^ CHECKSUM_XOR_KEY]
    part_tail_fixed = CHECKSUM_FIXED_TAIL
    # --- Final Assembly ---
    payload = (
            part_version +
            part_seed +
            part_env_a +
            part_env_b +
            part_sequence +
            part_window_props +
            part_uri_len +
            part_md5 +
            part_a1_len +
            part_a1_content +
            part_source_len +
            part_source_content +
            part_tail_start +
            part_checksum_ver +
            part_checksum_xor +
            part_tail_fixed
    )

    xor_result = xor_transform_array(payload)
    x3 = encode_x3(xor_result[:124])
    signature["x3"] = x3_prefix + x3
    signature = json.dumps(signature, separators=(",", ":"), ensure_ascii=False)
    return xys_prefix + encode(signature)

def get_screen_config():
    """
    Get random screen configuration with width, height, and available dimensions

    Returns:
        Dictionary containing screen configuration
    """
    width_str, height_str = f"{random.choices(
        ["1366;768", "1600;900", "1920;1080", "2560;1440", "3840;2160", "7680;4320"], 
        weights=[0.25, 0.15, 0.35, 0.15, 0.08, 0.02], k=1)[0]
    }".split(";")
    width = int(width_str)
    height = int(height_str)
    if random.choice([True, False]):
        avail_width = width - random.choices([0, 30, 60, 80], weights=[0.1, 0.4, 0.3, 0.2], k=1)[0]
        avail_height = height
    else:
        avail_width = width
        avail_height = height - random.choices([30, 60, 80, 100], weights=[0.2, 0.5, 0.2, 0.1], k=1)[0]
    return {
        "width": width,
        "height": height,
        "availWidth": avail_width,
        "availHeight": avail_height,
    }

def generate_fingerprint(cookies, user_agent, timestamp) -> dict:
    """
    Generate browser fingerprint

    Args:
        timestamp:
        cookies: Cookie dictionary
        user_agent: User agent string

    Returns:
        Complete fingerprint dictionary
    """
    cookie_string = "; ".join(f"{k}={v}" for k, v in cookies.items())

    screen_config = get_screen_config()
    is_incognito_mode = random.choices(["true", "false"], weights=[0.95, 0.05], k=1)[0]
    gpu_vendors = [
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 400 (0x00000166) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 4400 (0x00001112) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 4600 (0x00000412) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 520 (0x1912) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 530 (0x00001912) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 550 (0x00001512) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 6000 (0x1606) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris(TM) Graphics 540 (0x1912) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris(TM) Graphics 550 (0x1913) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris(TM) Plus Graphics 640 (0x161C) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) UHD Graphics 600 (0x3E80) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) UHD Graphics 620 (0x00003EA0) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) UHD Graphics 655 (0x00009BC8) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000046A8) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x00009A49) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris(R) Xe MAX Graphics (0x00009BC0) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel Arc A370M (0x0000AF51) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel Arc A380 (0x0000AF41) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel Arc A380M (0x0000AF5E) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel Arc A550 (0x0000AF42) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel Arc A770 (0x0000AF43) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel Arc A770M (0x0000AF50) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Mesa Intel(R) Graphics (RPL‑P GT1) (0x0000A702) OpenGL 4.6)",
        "Google Inc. (Intel)|ANGLE (Intel, Mesa Intel(R) UHD Graphics 770 (0x00004680) OpenGL 4.6)",
        "Google Inc. (Intel)|ANGLE (Intel, Mesa Intel(R) HD Graphics 4400 (0x00001122) OpenGL 4.6)",
        "Google Inc. (Intel)|ANGLE (Intel, Mesa Intel(R) Graphics (ADL‑S GT1) (0x0000A0A1) OpenGL 4.6)",
        "Google Inc. (Intel)|ANGLE (Intel, Mesa Intel(R) Graphics (RKL GT1) (0x0000A9A1) OpenGL 4.6)",
        "Google Inc. (Intel)|ANGLE (Intel, Mesa Intel(R) UHD Graphics (CML GT2) (0x00009A14) OpenGL 4.6)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics 3000 (0x00001022) Direct3D9Ex vs_3_0 ps_3_0, igdumd64.dll)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) HD Graphics Family (0x00000A16) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris Pro OpenGL Engine, OpenGL 4.1)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris(TM) Plus Graphics 645 (0x1616) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) Iris(TM) Plus Graphics 655 (0x161E) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) UHD Graphics 730 (0x0000A100) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Intel)|ANGLE (Intel, Intel(R) UHD Graphics 805 (0x0000B0A0) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon Vega 3 Graphics (0x000015E0) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon Vega 8 Graphics (0x000015D8) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon Vega 11 Graphics (0x000015DD) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon Graphics (0x00001636) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 5500 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 560 (0x000067EF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 570 (0x000067DF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 580 2048SP (0x00006FDF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 590 (0x000067FF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 6600 (0x000073FF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 6600 XT (0x000073FF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 6650 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 6700 XT (0x000073DF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 6800 (0x000073BF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 6900 XT (0x000073C2) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon RX 7700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon Pro 5300M OpenGL Engine, OpenGL 4.1)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon Pro 5500 XT OpenGL Engine, OpenGL 4.1)",
        "Google Inc. (AMD)|ANGLE (AMD, AMD Radeon R7 370 Series (0x00006811) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (AMD)|ANGLE (AMD, ATI Technologies Inc. AMD Radeon RX Vega 64 OpenGL Engine, OpenGL 4.1)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 (0x00001C81) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti (0x00001C8C) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB (0x000010DE) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce GTX 1070 (0x00001B81) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 (0x00001B80) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 (0x00001F06) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 SUPER (0x00001F06) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 (0x00001F10) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 2070 SUPER (0x00001F10) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x0000250F) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Ti (0x00002489) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002488) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Ti (0x000028A5) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 (0x00002206) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Ti (0x00002208) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 3090 (0x00002204) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 (0x00002882) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Ti (0x00002803) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 (0x00002786) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Ti (0x00002857) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 (0x00002819) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 (0x00002684) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA Quadro RTX 5000 Ada Generation (0x000026B2) Direct3D11 vs_5_0 ps_5_0, D3D11)",  # noqa: E501
        "Google Inc. (NVIDIA)|ANGLE (NVIDIA, NVIDIA Quadro P400 (0x00001CB3) Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Google Inc. (Google)|ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)",  # noqa: E501
        "Google Inc. (Google)|ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)",
        "Google Inc. (Google)|ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device), SwiftShader driver)",
    ]
    renderer_str = random.choice(gpu_vendors)
    vendor, renderer = renderer_str.split("|")

    x78_y = random.randint(2350, 2450)
    fp = {
        "x1": user_agent,
        "x2": "false",
        "x3": "zh-CN",
        "x4": random.choices([16, 24, 30, 32], weights=[0.05, 0.6, 0.05, 0.3], k=1)[0],
        "x5": random.choices([1, 2, 4, 8, 12, 16], weights=[0.10, 0.25, 0.4, 0.2, 0.03, 0.01], k=1)[0],
        "x6": "24",
        "x7": f"{vendor},{renderer}",
        "x8": random.choices([2, 4, 6, 8, 12, 16, 24, 32], weights=[0.1, 0.4, 0.2, 0.15, 0.08, 0.04, 0.02, 0.01], k=1)[0],
        "x9": f"{screen_config['width']};{screen_config['height']}",
        "x10": f"{screen_config['availWidth']};{screen_config['availHeight']}",
        "x11": "-480",
        "x12": "Asia/Shanghai",
        "x13": is_incognito_mode,
        "x14": is_incognito_mode,
        "x15": is_incognito_mode,
        "x16": "false",
        "x17": "false",
        "x18": "un",
        "x19": "Win32",
        "x20": "",
        "x21": "PDF Viewer,Chrome PDF Viewer,Chromium PDF Viewer,Microsoft Edge PDF Viewer,WebKit built-in PDF",
        "x22": hashlib.md5(secrets.token_bytes(32)).hexdigest(),
        "x23": "false",
        "x24": "false",
        "x25": "false",
        "x26": "false",
        "x27": "false",
        "x28": "0,false,false",
        "x29": "4,7,8",
        "x30": "swf object not loaded",
        "x33": "0",
        "x34": "0",
        "x35": "0",
        "x36": f"{random.randint(1, 20)}",
        "x37": "0|0|0|0|0|0|0|0|0|1|0|0|0|0|0|0|0|0|1|0|0|0|0|0",
        "x38": "0|0|1|0|1|0|0|0|0|0|1|0|1|0|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0",
        "x39": 0,
        "x40": "0",
        "x41": "0",
        "x42": "3.4.4",
        "x43": "742cc32c",
        "x44": str(timestamp),
        "x45": "__SEC_CAV__1-1-1-1-1|__SEC_WSA__|",
        "x46": "false",
        "x47": "1|0|0|0|0|0",
        "x48": "",
        "x49": "{list:[],type:}",
        "x50": "",
        "x51": "",
        "x52": "",
        "x55": "380,380,360,400,380,400,420,380,400,400,360,360,440,420",
        "x56": f"{vendor}|{renderer}|{hashlib.md5(secrets.token_bytes(32)).hexdigest()}|35",
        "x57": cookie_string,
        "x58": "180",
        "x59": "2",
        "x60": "63",
        "x61": "1291",
        "x62": "2047",
        "x63": "0",
        "x64": "0",
        "x65": "0",
        "x66": {
            "referer": "",
            "location": "https://www.xiaohongshu.com/explore",
            "frame": 0,
        },
        "x67": "1|0",
        "x68": "0",
        "x69": "326|1292|30",
        "x70": ["location"],
        "x71": "true",
        "x72": "complete",
        "x73": "1191",
        "x74": "0|0|0",
        "x75": "Google Inc.",
        "x76": "true",
        "x77": "1|1|1|1|1|1|1|1|1|1",
        "x78": {
            "x": 0,
            "y": x78_y,
            "left": 0,
            "right": 290.828125,
            "bottom": x78_y + 18,
            "height": 18,
            "top": x78_y,
            "width": 290.828125,
            "font": (
                'system-ui, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", '
                '"Noto Color Emoji", -apple-system, "Segoe UI", Roboto, Ubuntu, Cantarell, '
                '"Noto Sans", sans-serif, BlinkMacSystemFont, "Helvetica Neue", Arial, '
                '"PingFang SC", "PingFang TC", "PingFang HK", "Microsoft Yahei", '
                '"Microsoft JhengHei"'  # noqa: E501
            ),
        },
        "x82": "_0x17a2|_0x1954",
        "x31": "124.04347527516074",
        "x79": "144|599565058866",
        "x53": hashlib.md5(secrets.token_bytes(32)).hexdigest(),
        "x54": "10311144241322244122",
        "x80": "1|[object FileSystemDirectoryHandle]",
    }
    return fp


def generate_b1(fp: dict) -> str:
    """
    Generate b1 parameter from fingerprint

    Args:
        fp: Fingerprint dictionary

    Returns:
        Base64 encoded b1 string
    """
    b1_fp = {
        "x33": fp["x33"],
        "x34": fp["x34"],
        "x35": fp["x35"],
        "x36": fp["x36"],
        "x37": fp["x37"],
        "x38": fp["x38"],
        "x39": fp["x39"],
        "x42": fp["x42"],
        "x43": fp["x43"],
        "x44": fp["x44"],
        "x45": fp["x45"],
        "x46": fp["x46"],
        "x48": fp["x48"],
        "x49": fp["x49"],
        "x50": fp["x50"],
        "x51": fp["x51"],
        "x52": fp["x52"],
        "x82": fp["x82"],
    }
    b1_json = json.dumps(b1_fp, separators=(",", ":"), ensure_ascii=False)
    cipher = ARC4.new("xhswebmplfbt".encode())
    ciphertext = cipher.encrypt(b1_json.encode("utf-8")).decode("latin1")
    encoded_url = quote(ciphertext, safe="!*'()~_-")
    b = []
    for c in encoded_url.split("%")[1:]:
        chars = list(c)
        b.append(int("".join(chars[:2]), 16))
        [b.append(ord(j)) for j in chars[2:]]

    b1 = encode(bytearray(b))
    return b1

def sign_xs_common(cookie_dict, user_agent, timestamp) -> str:
    """
    Generate x-s-common signature

    Args:
        timestamp:
        user_agent:
        cookie_dict: Cookie dictionary (must be dict, not string)

    Returns:
        x-s-common signature string

    Raises:
        KeyError: If 'a1' cookie is missing
    """
    a1_value = cookie_dict["a1"]
    fingerprint = generate_fingerprint(
        cookies=cookie_dict, user_agent=user_agent, timestamp=timestamp)
    b1 = generate_b1(fingerprint)
    x9 = CRC32.crc32_js_int(b1)

    sign_struct = {"s0": 5, "s1": "", "x0": "1", "x1": "4.2.6", "x2": "Windows",
                   "x3": "xhs-pc-web", "x4": "4.86.0", "x5": a1_value, "x6": "", "x7": "",
                   "x8": b1, "x9": x9, "x10": 0, "x11": "normal"}

    sign_json = json.dumps(sign_struct, separators=(",", ":"), ensure_ascii=False)
    xs_common = encode(sign_json)
    return xs_common
