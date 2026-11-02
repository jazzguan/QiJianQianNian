"""服务端文本与视觉模型接入。"""
import base64
import json
import os
import time
from pathlib import Path
from urllib import error, request


def load_environment():
    path = Path(__file__).resolve().parents[1] / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                name, value = line.split('=', 1)
                os.environ.setdefault(name.strip(), value.strip().strip('\"\''))


load_environment()
_text_fallback_until=0


class ProviderError(RuntimeError):
    pass


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise error.HTTPError(req.full_url, code, '接口发生重定向', headers, fp)


def post_json(url, body, headers, secret):
    if not secret:
        raise ProviderError('模型服务尚未配置密钥')
    req = request.Request(url, data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                          headers={'Content-Type': 'application/json', **headers}, method='POST')
    try:
        with request.build_opener(NoRedirect).open(req, timeout=180) as response:
            return json.load(response)
    except error.HTTPError as exc:
        message = exc.read().decode('utf-8', errors='replace').replace(secret, '[redacted]')
        raise ProviderError(f'模型服务返回 {exc.code}：{message[:240]}') from None
    except (error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError(f'模型服务连接失败：{str(exc).replace(secret, "[redacted]")[:200]}') from None
    except (ValueError, KeyError, IndexError):
        raise ProviderError('模型服务返回格式无法解析') from None


def parse_object(text):
    text = text.strip()
    if text.startswith('```'):
        text = '\n'.join(text.splitlines()[1:])
        if text.rstrip().endswith('```'):
            text = text.rstrip()[:-3]
    try:
        result = json.loads(text)
    except ValueError:
        raise ProviderError('视觉服务未返回有效 JSON') from None
    if not isinstance(result, dict):
        raise ProviderError('视觉服务返回值必须为对象')
    return result


def text_completion(messages, max_tokens=1600):
    global _text_fallback_until
    if time.monotonic() < _text_fallback_until and os.environ.get('GEMINI_API_KEY'):
        return gemini_text_completion(messages,max_tokens)
    key = os.environ.get('ATRIA_API_KEY', '')
    base = os.environ.get('ATRIA_BASE_URL', 'https://api.atria-asi.ai/v1').rstrip('/')
    try:
        result = post_json(f'{base}/chat/completions', {
            'model': os.environ.get('ATRIA_MODEL', 'Atria-Dawn-Preview'),
            'messages': messages, 'max_completion_tokens': max_tokens,
        }, {'Authorization': f'Bearer {key}'}, key)
    except ProviderError as exc:
        if os.environ.get('GEMINI_API_KEY') and any(word in str(exc).lower() for word in ['429','quota','503','502','连接失败']):
            _text_fallback_until=time.monotonic()+300
            return gemini_text_completion(messages,max_tokens)
        raise
    try:
        content = result['choices'][0]['message']['content']
        if not isinstance(content, str) or not content.strip():
            raise ValueError()
        return content.strip()
    except (KeyError, IndexError, TypeError, ValueError):
        raise ProviderError('文本服务没有返回回答正文') from None


def gemini_text_completion(messages,max_tokens=1600):
    key=os.environ.get('GEMINI_API_KEY','')
    base=os.environ.get('GOOGLE_GEMINI_BASE_URL','https://generativelanguage.googleapis.com').rstrip('/')
    model=os.environ.get('GEMINI_MODEL','gemini-3.8-flash')
    systems='\n'.join(m['content'] for m in messages if m['role']=='system')
    body={'contents':[{'role':'model' if m['role']=='assistant' else 'user','parts':[{'text':m['content']}]} for m in messages if m['role']!='system'],
          'generationConfig':{'maxOutputTokens':max(4096,max_tokens+2048)}}
    if systems: body['systemInstruction']={'parts':[{'text':systems}]}
    result=post_json(f'{base}/v1beta/models/{model}:generateContent',body,{'x-goog-api-key':key},key)
    try:
        content=''.join(p.get('text','') for p in result['candidates'][0]['content']['parts'] if not p.get('thought'))
        if not content.strip(): raise ValueError()
        return content.strip()
    except (KeyError,IndexError,TypeError,ValueError): raise ProviderError('备用文本模型没有返回回答正文') from None


def vision_completion(image_bytes, mime_type, prompt):
    key = os.environ.get('GEMINI_API_KEY', '')
    base = os.environ.get('GOOGLE_GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com').rstrip('/')
    model = os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash')
    result = post_json(f'{base}/v1beta/models/{model}:generateContent', {
        'contents': [{'role': 'user', 'parts': [{'text': prompt}, {
            'inlineData': {'mimeType': mime_type, 'data': base64.b64encode(image_bytes).decode('ascii')},
        }]}], 'generationConfig': {'maxOutputTokens': 2048, 'responseMimeType': 'application/json'},
    }, {'x-goog-api-key': key}, key)
    try:
        parts = result['candidates'][0]['content']['parts']
        content = ''.join(p.get('text', '') for p in parts if not p.get('thought'))
        return parse_object(content)
    except (KeyError, IndexError, TypeError):
        raise ProviderError('视觉服务没有返回识别正文') from None


def provider_status():
    return {'textConfigured': bool(os.environ.get('ATRIA_API_KEY')),
            'visionConfigured': bool(os.environ.get('GEMINI_API_KEY')),
            'textModel': os.environ.get('GEMINI_MODEL','gemini-3.8-flash') if time.monotonic() < _text_fallback_until else os.environ.get('ATRIA_MODEL', 'Atria-Dawn-Preview'),
            'visionModel': os.environ.get('GEMINI_MODEL', 'gemini-3.8-flash')}
