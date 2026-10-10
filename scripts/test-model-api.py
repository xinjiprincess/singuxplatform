"""Test an OpenAI-compatible model endpoint using only the Python standard library."""

import argparse
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def completion_url(value):
    value = value.strip().rstrip('/')
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('Base URL must start with http:// or https://.')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Do not put credentials, a query, or a fragment in the base URL.')
    _ = parsed.port
    return value if parsed.path.endswith('/chat/completions') else value + '/chat/completions'


def check_error(data):
    if not isinstance(data, dict):
        raise ValueError('The response is not a JSON object.')
    if data.get('error') or data.get('success') is False:
        error = data.get('error') or data.get('message') or data.get('code')
        raise ValueError('API error: ' + str(error)[:400])


def stream_events(response):
    parts = []
    for raw in response:
        line = raw.decode('utf-8-sig').rstrip('\r\n')
        if not line:
            if parts:
                yield '\n'.join(parts)
                parts = []
        elif line.startswith('data:'):
            parts.append(line[5:].lstrip(' '))
    if parts:
        yield '\n'.join(parts)


def run_test(url, key, model, stream, timeout, max_tokens, no_proxy=False):
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': 'Reply with only OK.'}],
        'max_tokens': max_tokens,
        'stream': stream,
    }
    headers = {'Content-Type': 'application/json', 'Accept': 'text/event-stream' if stream else 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method='POST')
    started = time.monotonic()
    label = 'stream' if stream else 'non-stream'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if no_proxy else urllib.request.build_opener()
    try:
        with opener.open(request, timeout=timeout) as response:
            print(f'[{label}] HTTP {response.status}; content-type={response.headers.get("Content-Type", "missing")}')
            content, reasoning, usage, finish = [], [], None, None
            if stream:
                if response.headers.get_content_type() != 'text/event-stream':
                    data = json.loads(response.read(65536))
                    check_error(data)
                    raise ValueError('Expected SSE but received a non-stream response.')
                records = stream_events(response)
            else:
                records = [response.read(1048576).decode('utf-8')]
            for record in records:
                if not record.strip():
                    continue
                if record.strip() == '[DONE]':
                    break
                data = json.loads(record)
                check_error(data)
                usage = data.get('usage') or usage
                for choice in data.get('choices') or []:
                    message = choice.get('delta' if stream else 'message') or {}
                    if isinstance(message.get('content'), str):
                        content.append(message['content'])
                    reasoning_text = message.get('reasoning_content') or message.get('reasoning')
                    if isinstance(reasoning_text, str):
                        reasoning.append(reasoning_text)
                    finish = choice.get('finish_reason') or finish
            text = ''.join(content)
            print(f'[{label}] seconds={time.monotonic()-started:.2f}; output_chars={len(text)}; reasoning_chars={len("".join(reasoning))}; finish_reason={finish}')
            if isinstance(usage, dict):
                print(f'[{label}] usage=' + json.dumps({k: usage.get(k) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}))
            if not text.strip():
                raise ValueError('Empty answer. Token usage or HTTP 200 alone does not mean a successful response.')
            preview = text[:200].replace(key, '[REDACTED]') if key else text[:200]
            print(f'[{label}] PASS; answer={preview}')
            return True
    except urllib.error.HTTPError as error:
        detail = error.read(4096).decode('utf-8', errors='replace')
        if key:
            detail = detail.replace(key, '[REDACTED]')
        print(f'[{label}] FAIL; HTTP {error.code}; {detail[:500]}')
    except (ValueError, OSError, urllib.error.URLError) as error:
        detail = str(error)
        if key:
            detail = detail.replace(key, '[REDACTED]')
        print(f'[{label}] FAIL; {detail[:500]}')
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://61.188.36.255:18000/mass/v1')
    parser.add_argument('--model', default='DeepSeek-V4-Flash')
    parser.add_argument('--mode', choices=('both', 'stream', 'non-stream'), default='both')
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--max-tokens', type=int, default=512)
    parser.add_argument('--no-proxy', action='store_true', help='Connect directly, ignoring system HTTP proxies.')
    parser.add_argument('--probe', action='store_true', help='Send a small unauthenticated request; never reads an API key.')
    args = parser.parse_args()
    try:
        url = completion_url(args.base_url)
    except ValueError as error:
        parser.error(str(error))
    if args.timeout <= 0 or args.max_tokens <= 0:
        parser.error('Timeout and max tokens must be positive.')
    key = '' if args.probe else os.environ.get('MODEL_API_KEY', '').strip()
    if not args.probe and not key:
        key = getpass.getpass('API Key (hidden): ').strip()
        if not key:
            parser.error('An API key is required; alternatively use --probe.')
    print('Endpoint:', url)
    print('Model:', args.model)
    print('Network:', 'direct' if args.no_proxy else 'system proxy settings')
    if args.probe:
        print('Unauthenticated probe: 401/403 confirms reachability but does not test model generation.')
    modes = [False, True] if args.mode == 'both' and not args.probe else [args.mode == 'stream']
    results = [run_test(url, key, args.model, mode, args.timeout, args.max_tokens, args.no_proxy) for mode in modes]
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
