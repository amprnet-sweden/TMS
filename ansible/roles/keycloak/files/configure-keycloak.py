#!/usr/bin/env python3
"""Reconcile configured identity through verified HTTPS. Secrets arrive only on stdin."""
import copy
import gzip
import json
from pathlib import Path
import re
import ssl
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import build_opener, HTTPSHandler, ProxyHandler, Request


def realm_settings(source, origin):
    realm = copy.deepcopy(source)
    realm.update(registrationAllowed=False, bruteForceProtected=True)
    realm.pop("users", None)
    for role in realm["roles"]["realm"]:
        if role["name"] == "default-roles-amprnet":
            role["composites"]["realm"] = [r for r in role["composites"]["realm"] if r != "tms-superuser"]
    for client in realm["clients"]:
        client.pop("secret", None)
        if client["clientId"] == "admin-cli":
            client.setdefault("attributes", {})["client.use.lightweight.access.token.enabled"] = "false"
        if client["clientId"] == "tms-backend":
            # The application validates JWTs and uses admin-cli for lookups.
            client.update(enabled=False, redirectUris=[], webOrigins=[])
        if client["clientId"] == "tms-web-app":
            client.update(rootUrl=origin + "/tms/", baseUrl=origin + "/tms/",
                          adminUrl=origin + "/tms/", publicClient=True,
                          redirectUris=[origin + "/tms", origin + "/tms/*"], webOrigins=[origin],
                          standardFlowEnabled=True, implicitFlowEnabled=False,
                          directAccessGrantsEnabled=False, serviceAccountsEnabled=False)
            client.setdefault("attributes", {})["post.logout.redirect.uris"] = origin + "/tms##" + origin + "/tms/*"
    return realm


def client_needs_update(current, desired):
    for key, value in desired.items():
        if key in ("redirectUris", "webOrigins"):
            # Keycloak serializes these set-valued fields in its own order.
            if set(current.get(key) or []) != set(value):
                return True
        elif current.get(key) != value:
            return True
    return False


def verify_lookup_roles(roles):
    # Keycloak 26.4.7 expands view-users into query-users and query-groups.
    expected = {"query-users", "view-users", "query-groups"}
    actual = {role["name"] for role in roles}
    if actual != expected:
        raise RuntimeError("Backend lookup account has unexpected realm permissions: "
                           + ", ".join(sorted(actual)))


class Identity:
    def __init__(self, values):
        self.values = values
        self.origin = values["origin"]
        self.base = self.origin + "/auth"
        self.opener = build_opener(ProxyHandler({}), HTTPSHandler(
            context=ssl.create_default_context(cafile="/etc/tms/tls/ca.crt")))
        self.token = None
        self.changed = False

    def request(self, method, path, body=None, token=None, form=False):
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + token
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
            body = (urlencode(body) if form else json.dumps(body)).encode()
        with self.opener.open(Request(self.base + path, data=body, headers=headers, method=method), timeout=300) as response:
            data = response.read()
            return json.loads(data) if data else None

    def api(self, method, path, body=None):
        try:
            result = self.request(method, "/admin/realms/" + path, body, self.token)
        except HTTPError as error:
            if error.code != 401:
                raise
            self.token = self.login("master", *self.admin_credentials)
            result = self.request(method, "/admin/realms/" + path, body, self.token)
        if method != "GET":
            self.changed = True
        return result

    def login(self, realm, username, password):
        return self.request("POST", "/realms/" + realm + "/protocol/openid-connect/token", {
            "grant_type": "password", "client_id": "admin-cli", "scope": "openid", "username": username, "password": password,
        }, form=True)["access_token"]

    def user(self, realm, username, password):
        path = realm + "/users"
        users = self.api("GET", path + "?" + urlencode({"username": username, "exact": "true"}))
        if not users:
            self.api("POST", path, {"username": username, "enabled": True,
                "firstName": "TMS", "lastName": username, "email": username + "@example.invalid",
                "emailVerified": True, "requiredActions": [],
                "attributes": {"tms-managed-by": [self.values["deployment_id"]]},
                "credentials": [{"type": "password", "value": password, "temporary": False}]})
            users = self.api("GET", path + "?" + urlencode({"username": username, "exact": "true"}))
        if len(users) != 1 or users[0].get("attributes", {}).get("tms-managed-by") != [self.values["deployment_id"]]:
            raise RuntimeError("Refusing to adopt an unmanaged identity account")
        return users[0]["id"]

    def ownership_attribute(self, realm):
        # Keycloak's declarative profile may discard undefined user attributes.
        # Declare only this administrator-owned marker, preserving other fields.
        path = realm + "/users/profile"
        profile = self.api("GET", path)
        attributes = profile.setdefault("attributes", [])
        expected = {"name": "tms-managed-by", "displayName": "TMS deployment identity",
                    "permissions": {"view": ["admin"], "edit": ["admin"]}, "multivalued": False}
        current = next((a for a in attributes if a["name"] == expected["name"]), None)
        if current is None:
            attributes.append(expected)
            self.api("PUT", path, profile)
        elif current.get("permissions") != expected["permissions"]:
            raise RuntimeError("Deployment ownership attribute has unexpected permissions")

    def grant(self, path, roles):
        existing = {r["name"] for r in self.api("GET", path)}
        missing = [r for r in roles if r["name"] not in existing]
        if missing:
            self.api("POST", path, missing)

    def configure(self, source):
        v = self.values
        self.admin_credentials = ("tms-admin", v["admin_password"])
        try:
            self.token = self.login("master", "tms-admin", v["admin_password"])
        except HTTPError as error:
            if error.code not in (400, 401):
                raise
            self.admin_credentials = (v["bootstrap_user"], v["bootstrap_password"])
            self.token = self.login("master", v["bootstrap_user"], v["bootstrap_password"])
        self.ownership_attribute("master")
        administrator = self.user("master", "tms-admin", v["admin_password"])
        self.grant("master/users/" + administrator + "/role-mappings/realm",
                   [self.api("GET", "master/roles/admin")])
        self.token = self.login("master", "tms-admin", v["admin_password"])
        self.admin_credentials = ("tms-admin", v["admin_password"])
        # Confirm the permanent account has administrative access before retiring bootstrap.
        realms = self.api("GET", "")
        desired = realm_settings(source, self.origin)
        if not any(r["realm"] == "amprnet" for r in realms):
            self.api("POST", "", desired)
        current = self.api("GET", "amprnet")
        settings = {"registrationAllowed": False, "bruteForceProtected": True}
        if any(current.get(k) != value for k, value in settings.items()):
            self.api("PUT", "amprnet", settings)
        defaults = self.api("GET", "amprnet/roles/default-roles-amprnet/composites")
        excessive = [r for r in defaults if r["name"] == "tms-superuser" and not r.get("clientRole")]
        if excessive:
            self.api("DELETE", "amprnet/roles/default-roles-amprnet/composites", excessive)
        for desired_client in desired["clients"]:
            name = desired_client["clientId"]
            if name not in ("tms-web-app", "tms-backend", "admin-cli"):
                continue
            matches = self.api("GET", "amprnet/clients?" + urlencode({"clientId": name}))
            if len(matches) != 1:
                raise RuntimeError("Expected application client is missing or ambiguous")
            client = matches[0]
            if name == "admin-cli":
                attributes = dict(client.get("attributes", {}))
                if attributes.get("client.use.lightweight.access.token.enabled") != "false":
                    attributes["client.use.lightweight.access.token.enabled"] = "false"
                    self.api("PUT", "amprnet/clients/" + client["id"], {"attributes": attributes})
                continue
            keys = ("enabled",) if name == "tms-backend" else (
                "rootUrl", "baseUrl", "adminUrl", "publicClient", "redirectUris", "webOrigins",
                "standardFlowEnabled", "implicitFlowEnabled", "directAccessGrantsEnabled", "serviceAccountsEnabled")
            patch = {k: desired_client[k] for k in keys}
            if name == "tms-web-app":
                patch["attributes"] = dict(client.get("attributes", {}), **{
                    "post.logout.redirect.uris": desired_client["attributes"]["post.logout.redirect.uris"]})
            if client_needs_update(client, patch):
                self.api("PUT", "amprnet/clients/" + client["id"], patch)
        self.ownership_attribute("amprnet")
        operator = self.user("amprnet", "appuser", v["operator_password"])
        groups = self.api("GET", "amprnet/groups?" + urlencode({"search": "TMS Superusers", "exact": "true"}))
        if len(groups) != 1:
            raise RuntimeError("Expected TMS Superusers group is missing")
        group = groups[0]["id"]
        memberships = self.api("GET", "amprnet/users/" + operator + "/groups")
        if not any(g["id"] == group for g in memberships):
            self.api("PUT", "amprnet/users/" + operator + "/groups/" + group)
        lookup = self.user("master", "admin-cli", v["lookup_password"])
        clients = self.api("GET", "master/clients?clientId=amprnet-realm")
        if len(clients) != 1:
            raise RuntimeError("Expected master realm management client is missing")
        client = clients[0]["id"]
        self.grant("master/users/" + lookup + "/role-mappings/clients/" + client,
                   [self.api("GET", "master/clients/" + client + "/roles/" + r) for r in ("query-users", "view-users")])
        effective = self.api("GET", "master/users/" + lookup + "/role-mappings/clients/" + client + "/composite")
        verify_lookup_roles(effective)
        lookup_token = self.login("master", "admin-cli", v["lookup_password"])
        for path in ("users?username=appuser&exact=true", "users/" + operator, "groups", "roles"):
            self.request("GET", "/admin/realms/amprnet/" + path, token=lookup_token)
        try:
            self.request("GET", "/admin/realms/master/users", token=lookup_token)
        except HTTPError as error:
            if error.code != 403:
                raise
        else:
            raise RuntimeError("Backend lookup account unexpectedly has master administration access")
        operator_token = self.login("amprnet", "appuser", v["operator_password"])
        info = self.request("GET", "/realms/amprnet/protocol/openid-connect/userinfo", token=operator_token)
        if "tms-superuser" not in info.get("realm_access", {}).get("roles", []):
            raise RuntimeError("Operator userinfo lacks the required TMS role")
        bootstrap = self.api("GET", "master/users?" + urlencode({"username": v["bootstrap_user"], "exact": "true"}))
        for user in bootstrap:
            self.api("DELETE", "master/users/" + user["id"])
        return {"changed": self.changed, "lookup_checks": "users, groups, roles; master access denied",
                "operator_check": "authenticated userinfo includes tms-superuser", "bootstrap_admin": "removed"}

    def assets(self):
        url = self.base + "/admin/master/console/"
        with self.opener.open(url, timeout=90) as response:
            page = response.read().decode()
        paths = re.findall(r'(?:src|href)=["\x27]([^"\x27]+\.(?:js|css)(?:\?[^"\x27]*)?)["\x27]', page)
        checked = []
        for path in paths:
            target = urljoin(url, path)
            if urlsplit(target).netloc != urlsplit(self.origin).netloc:
                raise RuntimeError("Admin asset escaped the canonical origin")
            request = Request(target, headers={"Accept-Encoding": "gzip"})
            with self.opener.open(request, timeout=90) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                if not body or "text/html" in response.headers.get("Content-Type", ""):
                    raise RuntimeError("Admin asset did not return JavaScript or CSS")
                checked.append(urlsplit(target).path)
        if not any(p.endswith(".js") for p in checked) or not any(p.endswith(".css") for p in checked):
            raise RuntimeError("Could not verify both JavaScript and CSS admin assets")
        return checked


def main():
    values = json.load(sys.stdin)
    identity = Identity(values)
    result = identity.configure(json.loads(Path(sys.argv[1]).read_text()))
    result["admin_assets_requested_with_gzip"] = identity.assets()
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except HTTPError as error:
        sys.exit("Keycloak HTTPS API check failed with HTTP " + str(error.code) + " at " + urlsplit(error.url).path)
    except RuntimeError as error:
        sys.exit(str(error))
    except Exception:
        # Never echo request bodies, tokens, passwords or the stdin payload.
        sys.exit("Keycloak reconciliation failed; inspect service health and managed account settings locally.")
