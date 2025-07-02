import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("attendance-1a9df-firebase-adminsdk-fbsvc-401b975baf.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
