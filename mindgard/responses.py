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

class NDJsonProcessor:
    def preprocess_line(self, line:str):
        return line

    def join_responses(self, responses: list[str]):
        return "".join(responses)

class EventStreamProcessor:
    def preprocess_line(self, line:str):
        return line[len('data: '):]

    def join_responses(self, responses: list[str]):
        stripped = [response.strip() for response in responses]
        return " ".join(stripped)

def extract_replies(response, selector=None):
    # Example of spec: https://platform.openai.com/docs/api-reference/streaming
    content_type = response.headers.get('Content-Type','').lower()
    if (content_type == 'text/event-stream' or content_type == 'application/x-ndjson'):
        reply = []
        content_processor = NDJsonProcessor() if content_type == 'application/x-ndjson' else EventStreamProcessor()
        for line in response.iter_lines():
            if len(line) < MINIMUM_MESSAGE_SIZE:
                continue
            line_value = content_processor.preprocess_line(line).decode("utf-8")
            line_json = json.loads(line_value)
            extracted = extract_reply(line_json,selector=selector, strict=False)
            if len(extracted) > 0:
                reply.append(extracted)
        return content_processor.join_responses(reply)
    else:
        # Simple RPC
        return extract_reply(response.json(), selector=selector)