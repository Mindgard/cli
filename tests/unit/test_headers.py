from mindgard.headers import parse_headers

def test_headers_have_key_value() -> None:
    headers = parse_headers(headers_comma_separated="Authorization: bearer XXX")
    assert headers["Authorization"] == "bearer XXX"

def test_header_values_can_be_comma_separated() -> None:
    headers = parse_headers(headers_comma_separated="Authorization: bearer YYY,Cookie: monster")
    assert headers["Authorization"] == "bearer YYY"
    assert headers["Cookie"] == "monster"

def test_can_have_multiple_headers() -> None:
    headers = parse_headers(headers_list=["Authorization: bearer YYY","Cookie: monster"])
    assert headers["Authorization"] == "bearer YYY"
    assert headers["Cookie"] == "monster"

def test_header_string_values_can_contain_colons() -> None:
    headers = parse_headers(headers_comma_separated="Referer: https://example.com/referer")
    assert headers["Referer"] == "https://example.com/referer"

def test_header_list_values_can_contain_colons() -> None:
    headers = parse_headers(headers_list=["Referer: https://example.com/referer"])
    assert headers["Referer"] == "https://example.com/referer"

def test_header_values_can_contain_commas() -> None:
    headers = parse_headers(headers_list=["Cookie: monster,yum"])
    assert headers["Cookie"] == "monster,yum"