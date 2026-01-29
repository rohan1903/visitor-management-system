import firebase_admin
from firebase_admin import credentials, db

# Initialize Firebase only if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("firebaseKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://v-guard-af8af-default-rtdb.firebaseio.com/'
    })

firebase_db = db
