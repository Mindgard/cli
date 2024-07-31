import jsonpath_ng
import json

# Filters to only LLM messages with content.
MINIMUM_MESSAGE_SIZE = 10

def extract_reply(json_response,selector=None, strict=True):
    if selector:
        jsonpath_expr = jsonpath_ng.parse(selector)
        match = jsonpath_expr.find(json_response)
        if match:
            return str(match[0].value)
        elif strict:
            raise Exception(f"Selector {selector} did not match any elements in the response. {json_response=}")
        else:
            return ""
    else:
        return json.dumps(json_response)

def extract_replies(response, selector=None):
    # Example of spec: https://platform.openai.com/docs/api-reference/streaming
    if (response.headers.get('Content-Type','').lower() == 'text/event-stream'):
        reply = []
        for line in response.iter_lines():
            line_value = line[len('data: '):].decode("utf-8")
            if len(line_value) < MINIMUM_MESSAGE_SIZE:
                continue
            line_json = json.loads(line_value)
            extracted = extract_reply(line_json,selector=selector, strict=False).strip()
            if (len(extracted) > 0):
                reply.append(extracted)

        return " ".join(reply)
    else:
        # Simple RPC
        return extract_reply(response.json(), selector=selector)