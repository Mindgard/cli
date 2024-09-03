from typing import Dict, Optional, List
import re

def parse_headers(headers_comma_separated: Optional[str] = None, headers_list: List[str] = []) -> Dict[str, str]:
    if headers_comma_separated is None:
        return parse_list_of_headers(headers_input=headers_list or [])
    else:
        return parse_list_of_headers(headers_input=headers_comma_separated.split(",") + (headers_list or []))

def parse_list_of_headers(headers_input:list[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for key_and_value_str in headers_input:
        match = re.search("(.*?): *(.*)", key_and_value_str)
        if match:
            key = match.group(1)
            value = match.group(2)
            headers[key.strip()] = value.strip()

    return headers