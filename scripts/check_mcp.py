#!/usr/bin/env python3
"""Check public production discovery without credentials or tool calls."""

import json
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from validate import MCP_URL

ORIGIN = "https://mcp.wimbly.ai"
ISSUER = "https://spotless-spoon-77.authkit.app"
METADATA = ORIGIN + "/.well-known/oauth-protected-resource/mcp"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, method="GET", body=None, headers=None):
    request = Request(url, data=body, method=method, headers=headers or {})
    try:
        response = build_opener(NoRedirect).open(request, timeout=15)
    except HTTPError as error:
        response = error
    with response:
        data = response.read(65537)
        if len(data) > 65536:
            raise ValueError("Public discovery response exceeds 64 KiB")
        return response.code, {k.lower(): v for k, v in response.headers.items()}, data


def check(fetch_response=fetch):
    checks = []

    def expect(condition, name):
        if not condition:
            raise ValueError(f"Production MCP preflight failed: {name}")
        checks.append(name)

    status, _, data = fetch_response(METADATA)
    expect(status == 200, "protected resource metadata status")
    metadata = json.loads(data)
    expect(metadata.get("resource") == MCP_URL, "canonical MCP resource")
    expect(metadata.get("authorization_servers") == [ISSUER], "production issuer")

    # These are anonymous discovery requests, never tools/call or real tokens.
    for headers in ({}, {"Authorization": "Bearer invalid-release-preflight"}):
        status, response_headers, _ = fetch_response(
            MCP_URL,
            method="POST",
            body=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
            headers={"Content-Type": "application/json", **headers},
        )
        expect(status == 401, "unauthorized request refused")
        expect(
            f'resource_metadata="{METADATA}"'
            in response_headers.get("www-authenticate", ""),
            "canonical authentication challenge",
        )

    status, _, data = fetch_response(ISSUER + "/.well-known/oauth-authorization-server")
    expect(status == 200, "authorization server discovery status")
    authorization = json.loads(data)
    expect(authorization.get("issuer") == ISSUER, "authorization issuer matches")
    expect(
        "S256" in authorization.get("code_challenge_methods_supported", []),
        "PKCE S256",
    )
    expect(
        authorization.get("client_id_metadata_document_supported") is True,
        "CIMD supported",
    )
    for path in ("/login", "/v1/auth/me", "/mcp/setup"):
        status, _, _ = fetch_response(ORIGIN + path)
        expect(status == 404, "private or retired route unavailable: " + path)

    return {
        "resource": MCP_URL,
        "issuer": ISSUER,
        "checks": checks,
        "authenticatedToolCalls": 0,
        "scope": "Public discovery only; not an OAuth, tool, or UI acceptance test",
    }


if __name__ == "__main__":
    try:
        print(json.dumps(check(), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(str(error))
