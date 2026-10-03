#!/usr/bin/env python3
"""Read-only application checks; credentials on stdin, no tokens in output."""
import json
import ssl
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener, HTTPSHandler, ProxyHandler, Request


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify(origin, password, opener, websocket_check=None):
    def request(path, headers=None, form=None):
        headers = dict(headers or {})
        body = None
        if form is not None:
            body = urlencode(form).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        with opener.open(Request(origin + path, data=body, headers=headers), timeout=120) as response:
            return json.load(response)

    for headers in ({}, {'Authorization': 'Bearer deliberately-invalid-lab-test-token'}):
        try:
            request('/api/user', headers)
        except HTTPError as error:
            require(error.code == 401, 'Unauthenticated or invalid-token request did not return 401')
        else:
            raise RuntimeError('API unexpectedly accepted an unauthenticated or invalid-token request')

    token = request('/auth/realms/amprnet/protocol/openid-connect/token', form={
        'grant_type': 'password', 'client_id': 'admin-cli', 'scope': 'openid',
        'username': 'appuser', 'password': password})['access_token']
    bearer = {'Authorization': 'Bearer ' + token}
    user = request('/api/user', bearer)
    require(user.get('username') == 'appuser' and 'tms-superuser' in user.get('roles', []),
            'Authenticated API user or roles differ from the expected configured identity')
    cookie_user = request('/api/user', {'Cookie': 'JWT=' + token})
    require(cookie_user.get('id') == user.get('id'), 'Browser JWT cookie did not resolve the same user')
    for path in ('/api/missions', '/api/user/missions'):
        result = request(path, bearer)
        require(result.get('status') is True and isinstance(result.get('data'), list),
                'Database-backed mission read failed')
    users = request('/api/keycloak/admin/users?q=appuser', bearer)
    require(isinstance(users, list) and any(u.get('username') == 'appuser' for u in users),
            'Backend Keycloak user search failed')
    groups = request('/api/keycloak/admin/groups', bearer)
    require(isinstance(groups, list) and any(g.get('name') == 'TMS Superusers' for g in groups),
            'Backend Keycloak group lookup failed')
    roles = request('/api/keycloak/admin/roles', bearer)
    require(isinstance(roles, list) and any(r.get('name') == 'tms-superuser' for r in roles),
            'Backend Keycloak role lookup failed')
    if websocket_check is not None:
        websocket_check(origin, token)
    return {'unauthenticated_and_invalid_token': '401', 'bearer_and_browser_cookie': 'passed',
            'database_mission_reads': 'passed', 'backend_keycloak_users_groups_roles': 'passed',
            'java_https_jwt_and_lookup': 'passed', 'browser_workflows': 'pending',
            'websocket_stomp_connect': 'passed' if websocket_check else 'not checked'}


def websocket_check(origin, token):
    result = subprocess.run([
        '/usr/lib/jvm/java-21-openjdk-arm64/bin/java',
        '-Djavax.net.ssl.trustStore=/etc/ssl/certs/tms-backend-cacerts',
        '-Djavax.net.ssl.trustStorePassword=changeit',
        '/usr/local/lib/tms-ansible/WebSocketProbe.java', origin],
        input=token, text=True, capture_output=True, timeout=150)
    require(result.returncode == 0 and result.stdout.strip() == 'STOMP CONNECTED',
            'WSS/STOMP did not acknowledge authenticated CONNECT')


def main():
    values = json.load(sys.stdin)
    opener = build_opener(ProxyHandler({}), HTTPSHandler(
        context=ssl.create_default_context(cafile='/etc/tms/tls/ca.crt')))
    print(json.dumps(verify(values['origin'], values['password'], opener, websocket_check)))


if __name__ == '__main__':
    try:
        main()
    except HTTPError as error:
        sys.exit('Backend verification HTTP ' + str(error.code) + ' at ' + urlsplit(error.url).path)
    except RuntimeError as error:
        sys.exit(str(error))
    except Exception:
        sys.exit('Backend verification failed; inspect service health and configuration locally.')
