"""Send Web Push notifications to the phones that signed up in the app."""
import json
import os
import tempfile


def send(payload):
    subs = json.loads(os.environ.get('PUSH_SUBS') or '[]')
    key = os.environ.get('VAPID_PRIVATE', '').strip()
    if not subs or not key:
        return {'sent': 0, 'skipped': 'no subscribers or no key'}
    from pywebpush import WebPushException, webpush

    with tempfile.NamedTemporaryFile('w', suffix='.pem', delete=False) as f:
        f.write(key)
        key_path = f.name
    sent, failed = 0, []
    try:
        for sub in subs:
            try:
                webpush(subscription_info=sub, data=json.dumps(payload, ensure_ascii=False),
                        vapid_private_key=key_path,
                        vapid_claims={'sub': os.environ.get('VAPID_SUBJECT', 'mailto:nyhedsradar@example.invalid')},
                        ttl=3 * 3600)
                sent += 1
            except WebPushException as e:
                code = getattr(e.response, 'status_code', None)
                failed.append('expired' if code in (404, 410) else str(code or e)[:80])
    finally:
        os.unlink(key_path)
    return {'sent': sent, 'failed': failed}
