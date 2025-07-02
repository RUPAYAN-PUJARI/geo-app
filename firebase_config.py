import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore

# Get the base64-encoded JSON string from the environment variable
base64_key = os.environ.get("FIREBASE_CREDENTIALS_BASE64")

if not base64_key:
    raise RuntimeError("FIREBASE_CREDENTIALS_BASE64 environment variable is missing.")

# Decode and load the credentials
decoded_json = base64.b64decode(base64_key).decode("utf-8")
service_account_info = json.loads(decoded_json)

cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

db = firestore.client()
