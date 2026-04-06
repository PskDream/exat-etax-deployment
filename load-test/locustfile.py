import base64
import hashlib
import time

import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from locust import HttpUser, task, between

# ---- Config ---------------------------------------------------------------
BASE_URL      = "http://localhost:9000"
KEY_ALIAS     = "my-key"
PRIV_KEY_PATH = "ec-prime256v1-priv-key-pkcs8.pem"

# Load EC private key once at module level
with open(PRIV_KEY_PATH, "rb") as f:
    _ec_private_key = load_pem_private_key(f.read(), password=None)

# Load fixtures once
with open("fixtures/pdf_hash.txt") as f:
    _pdf_hash_b64 = f.read().strip()

with open("fixtures/xml.txt") as f:
    _xml_b64 = f.read().strip()

# ---------------------------------------------------------------------------

def _make_jwt() -> str:
    """Generate ES256 JWT valid for 5 minutes."""
    now = int(time.time())
    payload = {"iat": now, "exp": now + 300, "sub": "load-test"}
    return jwt.encode(payload, _ec_private_key, algorithm="ES256")


class SignUser(HttpUser):
    host = BASE_URL
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self._token_exp = 0
        self._refresh_token()

    def _refresh_token(self):
        self.headers = {
            "Authorization": f"Bearer {_make_jwt()}",
            "Content-Type": "application/json",
        }
        self._token_exp = int(time.time()) + 240  # refresh ก่อนหมด 1 นาที

    def _ensure_token(self):
        if time.time() >= self._token_exp:
            self._refresh_token()

    @task(1)
    def sign_pdf_hash(self):
        self._ensure_token()
        self.client.post(
            "/api/sign/pdf-hash",
            json={"hash_base64": _pdf_hash_b64, "key_alias": KEY_ALIAS},
            headers=self.headers,
            name="/api/sign/pdf-hash",
        )

    @task(1)
    def sign_xml(self):
        self._ensure_token()
        self.client.post(
            "/api/sign/xml",
            json={"xml_base64": _xml_b64, "key_alias": KEY_ALIAS},
            headers=self.headers,
            name="/api/sign/xml",
        )
