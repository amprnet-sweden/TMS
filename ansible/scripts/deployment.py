"""Validate the single public origin before using it in certificates or templates."""
import json
import re
from urllib.parse import urlsplit


def load(path):
    values = json.loads(path.read_text())
    if not isinstance(values, dict) or set(values) - {'tms_public_origin', 'tms_tenant'}:
        raise ValueError('Deployment JSON accepts only tms_public_origin and tms_tenant.')
    origin = values.get('tms_public_origin', '')
    url = urlsplit(origin)
    host = url.hostname or ''
    if (url.scheme != 'https' or url.username or url.password or url.path or url.query or url.fragment
            or len(host) > 253 or '.' not in host
            or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                       for label in host.split('.'))):
        raise ValueError('Use an HTTPS origin with a DNS hostname, optional port, and no trailing slash.')
    port = url.port or 443
    expected = f'https://{host}' + (f':{port}' if port != 443 else '')
    if origin != expected or not 1 <= port <= 65535:
        raise ValueError('Use a lowercase canonical HTTPS origin; omit the default port 443.')
    tenant = values.get('tms_tenant', 'default')
    if not isinstance(tenant, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', tenant):
        raise ValueError('Tenant must contain 1–64 letters, digits, underscores or hyphens.')
    return dict(tms_public_origin=origin, tms_hostname=host, tms_https_port=port, tms_tenant=tenant)
