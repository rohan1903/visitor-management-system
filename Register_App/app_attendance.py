# import os, cv2, base64, numpy as np
# import firebase_admin
# from firebase_admin import credentials, db
# from deepface import DeepFace
# from time import sleep, time
# from datetime import datetime

# # ✅ Firebase Initialization
# if not firebase_admin._apps:
#     cred = credentials.Certificate('firebase_credentials.json')
#     firebase_admin.initialize_app(cred, {
#         'databaseURL': 'https://v-guard-af8af-default-rtdb.firebaseio.com/'
#     })

# UPLOAD = 'uploads'
# THRESHOLD = 0.3
# COOLDOWN_SECONDS = 10  # prevent same person triggering again too soon

# # ✅ Face Recognition Logic
# def recognize_face(frame):
#     visitors = db.reference('visitors').get() or {}
#     for vid, v in visitors.items():
#         path = os.path.join(UPLOAD, v.get('photo_path', ''))
#         if not os.path.exists(path): continue
#         try:
#             res = DeepFace.verify(frame, path, model_name='SFace',
#                                   detector_backend='opencv', enforce_detection=False)
#             if res['verified'] and res['distance'] < THRESHOLD:
#                 return vid, v  # ✅ Return full visitor record
#         except Exception as e:
#             print(f"⚠️ Error with {v.get('name', 'Unknown')}: {e}")
#     return None, None

# # ✅ Main Attendance Loop
# def attendance_loop():
#     cap = cv2.VideoCapture(0)
#     if not cap.isOpened():
#         print("❌ Webcam not available.")
#         return

#     print("🎯 Starting attendance monitor...")
#     last_seen = {}  # vid -> last detected timestamp

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         vid, visitor = recognize_face(frame)
#         now = datetime.now()

#         if vid:
#             last_time = last_seen.get(vid)
#             if last_time and (now - last_time).total_seconds() < COOLDOWN_SECONDS:
#                 sleep(1)
#                 continue  # skip if within cooldown period

#             last_seen[vid] = now

#             rec_ref = db.reference(f'attendance/{vid}')
#             rec = rec_ref.get() or {}
#             now_str = now.strftime("%Y-%m-%d %H:%M:%S")

#             if 'check_in_time' not in rec:
#                 print(f"🟢 Check-in: {visitor['name']}")
#                 rec_ref.set({
#                     'name': visitor['name'],
#                     'photo_path': visitor.get('photo_path', ''),
#                     'gender': visitor.get('gender', 'Unknown'),
#                     'purpose': visitor.get('purpose', 'N/A'),
#                     'check_in_time': now_str,
#                     'check_out_time': '',
#                     'duration_seconds': '',
#                     'blacklisted': 'no'
#                 })

#             elif rec.get('check_out_time', '') == '':
#                 print(f"🔴 Check-out: {visitor['name']}")
#                 check_in_time = datetime.strptime(rec['check_in_time'], "%Y-%m-%d %H:%M:%S")
#                 duration = int((now - check_in_time).total_seconds())

#                 rec_ref.update({
#                     'check_out_time': now_str,
#                     'duration_seconds': duration
#                 })

#         sleep(1)

#     cap.release()

# # ✅ Entry Point
# if __name__ == '__main__':
#     import threading
#     threading.Thread(target=attendance_loop, daemon=True).start()
#     print("🌐 Attendance loop running... Press CTRL+C to stop.")
#     while True:
#         sleep(60)



# import os, cv2, base64, numpy as np
# import firebase_admin
# from firebase_admin import credentials, db
# from deepface import DeepFace
# from time import sleep, time
# from datetime import datetime

# # ✅ Firebase Initialization
# if not firebase_admin._apps:
#     cred = credentials.Certificate('firebase_credentials.json')
#     firebase_admin.initialize_app(cred, {
#         'databaseURL': 'https://v-guard-af8af-default-rtdb.firebaseio.com/'
#     })

# UPLOAD = 'uploads'
# THRESHOLD = 0.3
# COOLDOWN_SECONDS = 10  # Avoid repeated triggers

# # ✅ Face Recognition Logic
# def recognize_face(frame):
#     visitors = db.reference('visitors').get() or {}
#     for vid, v in visitors.items():
#         path = os.path.join(UPLOAD, v.get('photo_path', ''))
#         if not os.path.exists(path):
#             continue
#         try:
#             res = DeepFace.verify(
#                 frame, path,
#                 model_name='SFace',
#                 detector_backend='opencv',
#                 enforce_detection=False
#             )
#             if res['verified'] and res['distance'] < THRESHOLD:
#                 return vid, v  # Return visitor ID and data
#         except Exception as e:
#             print(f"⚠️ Error verifying {v.get('name', 'Unknown')}: {e}")
#     return None, None

# # ✅ Attendance Monitoring Loop
# def attendance_loop():
#     cap = cv2.VideoCapture(0)
#     if not cap.isOpened():
#         print("❌ Webcam not available.")
#         return

#     print("🎯 Starting attendance monitor...")
#     last_seen = {}

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         vid, visitor = recognize_face(frame)
#         now = datetime.now()

#         if vid:
#             # Cooldown: avoid repeated triggers for the same person
#             last_time = last_seen.get(vid)
#             if last_time and (now - last_time).total_seconds() < COOLDOWN_SECONDS:
#                 sleep(1)
#                 continue

#             last_seen[vid] = now
#             now_str = now.strftime("%Y-%m-%d %H:%M:%S")

#             person_logs_ref = db.reference(f'attendance/{vid}')
#             logs = person_logs_ref.get() or {}

#             # 🔍 Check if there's an open session (not yet checked out)
#             active_log_id = None
#             for log_id in sorted(logs.keys(), reverse=True):
#                 entry = logs.get(log_id)
#                 if isinstance(entry, dict) and entry.get('check_out_time', '') == '':
#                     active_log_id = log_id
#                     break

#             if not active_log_id:
#                 # ✅ New Check-In
#                 log_id = str(int(time() * 1000))  # Use timestamp as unique log ID
#                 print(f"🟢 Check-in: {visitor['name']}")
#                 person_logs_ref.child(log_id).set({
#                     'name': visitor['name'],
#                     'photo_path': visitor.get('photo_path', ''),
#                     'gender': visitor.get('gender', 'Unknown'),
#                     'purpose': visitor.get('purpose', 'N/A'),
#                     'check_in_time': now_str,
#                     'check_out_time': '',
#                     'duration_seconds': '',
#                     'blacklisted': 'no'
#                 })
#             else:
#                 # ✅ Check-Out
#                 check_in_str = logs[active_log_id].get('check_in_time')
#                 try:
#                     check_in_time = datetime.strptime(check_in_str, "%Y-%m-%d %H:%M:%S")
#                     duration = int((now - check_in_time).total_seconds())
#                 except Exception as e:
#                     print(f"⚠️ Error parsing time: {e}")
#                     duration = 0

#                 print(f"🔴 Check-out: {visitor['name']}")
#                 person_logs_ref.child(active_log_id).update({
#                     'check_out_time': now_str,
#                     'duration_seconds': duration
#                 })

#         sleep(1)

#     cap.release()

# # ✅ Entry Point
# if __name__ == '__main__':
#     import threading
#     threading.Thread(target=attendance_loop, daemon=True).start()
#     print("🌐 Attendance loop running... Press CTRL+C to stop.")
#     while True:
#         sleep(60)

# import os, cv2, numpy as np
# import firebase_admin
# from firebase_admin import credentials, db
# from deepface import DeepFace
# from time import sleep, time
# from datetime import datetime

# # ✅ Firebase Initialization
# if not firebase_admin._apps:
#     cred = credentials.Certificate('firebase_credentials.json')
#     firebase_admin.initialize_app(cred, {
#         'databaseURL': 'https://v-guard-af8af-default-rtdb.firebaseio.com/'
#     })

# UPLOAD = 'uploads'
# THRESHOLD = 0.75
# COOLDOWN_SECONDS = 10
# NO_FACE_TIMEOUT = 20  # ⏱️ Log only if no face seen for > 20 sec

# # ✅ Face Recognition Logic
# def recognize_face(frame):
#     visitors = db.reference('visitors').get() or {}
#     for vid, v in visitors.items():
#         path = os.path.join(UPLOAD, v.get('photo_path', ''))
#         if not os.path.exists(path):
#             continue
#         try:
#             res = DeepFace.verify(
#                 frame, path,
#                 model_name='SFace',
#                 detector_backend='opencv',
#                 enforce_detection=False
#             )
#             if res['verified'] and res['distance'] < THRESHOLD:
#                 return vid, v
#         except Exception:
#             continue
#     return None, None

# # ✅ Attendance Loop
# def attendance_loop():
#     cap = cv2.VideoCapture(0)
#     if not cap.isOpened():
#         print("❌ Webcam not available.")
#         return

#     print("🎯 Starting attendance monitor...")
#     last_seen = {}
#     last_face_time = time()
#     last_no_face_log_time = time()

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         cv2.imshow("Live Attendance Camera", frame)
#         if cv2.waitKey(1) & 0xFF == 27:
#             print("🛑 ESC pressed, exiting loop.")
#             break

#         vid, visitor = recognize_face(frame)
#         now = datetime.now()
#         now_ts = time()

#         if vid:
#             last_face_time = now_ts
#             last_no_face_log_time = now_ts

#             last_time = last_seen.get(vid)
#             if last_time and (now - last_time).total_seconds() < COOLDOWN_SECONDS:
#                 sleep(1)
#                 continue

#             last_seen[vid] = now
#             now_str = now.strftime("%Y-%m-%d %H:%M:%S")
#             person_logs_ref = db.reference(f'attendance/{vid}')
#             logs = person_logs_ref.get() or {}

#             active_log_id = None
#             for log_id in sorted(logs.keys(), reverse=True):
#                 entry = logs.get(log_id)
#                 if isinstance(entry, dict) and entry.get('check_out_time', '') == '':
#                     active_log_id = log_id
#                     break

#             if not active_log_id:
#                 # ✅ New Check-In
#                 log_id = str(int(now_ts * 1000))
#                 print(f"🟢 Check-in: {visitor['name']}")
#                 person_logs_ref.child(log_id).set({
#                     'name': visitor['name'],
#                     'photo_path': visitor.get('photo_path', ''),
#                     'gender': visitor.get('gender', 'Unknown'),
#                     'purpose': visitor.get('purpose', 'N/A'),
#                     'check_in_time': now_str,
#                     'check_out_time': '',
#                     'duration_seconds': '',
#                     'blacklisted': 'no'
#                 })
#             else:
#                 # ✅ Check-Out
#                 check_in_str = logs[active_log_id].get('check_in_time')
#                 try:
#                     check_in_time = datetime.strptime(check_in_str, "%Y-%m-%d %H:%M:%S")
#                     duration = int((now - check_in_time).total_seconds())
#                 except Exception:
#                     duration = 0

#                 print(f"🔴 Check-out: {visitor['name']}")
#                 person_logs_ref.child(active_log_id).update({
#                     'check_out_time': now_str,
#                     'duration_seconds': duration
#                 })

#         else:
#             elapsed = now_ts - last_face_time
#             if elapsed >= NO_FACE_TIMEOUT and (now_ts - last_no_face_log_time >= NO_FACE_TIMEOUT):
#                 print(f"⏱️ No face detected for last {int(elapsed)} seconds.")
#                 last_no_face_log_time = now_ts

#         sleep(1)

#     cap.release()
#     cv2.destroyAllWindows()

# # ✅ Main
# if __name__ == '__main__':
#     attendance_loop()


# import os
# import cv2
# import numpy as np
# from time import sleep, time
# from datetime import datetime
# from deepface import DeepFace
# from dotenv import load_dotenv
# from twilio.rest import Client
# import firebase_admin
# from firebase_admin import credentials, db

# # ✅ Load .env
# load_dotenv()
# TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
# TWILIO_PHONE = os.getenv("TWILIO_PHONE")
# FEEDBACK_LINK = os.getenv("FEEDBACK_LINK")

# # ✅ Print for confirmation
# print("✅ TWILIO_ACCOUNT_SID:", TWILIO_ACCOUNT_SID)
# print("✅ TWILIO_PHONE:", TWILIO_PHONE)
# print("✅ FEEDBACK_LINK:", FEEDBACK_LINK)

# # ✅ Firebase Init
# if not firebase_admin._apps:
#     cred = credentials.Certificate("firebase_credentials.json")
#     firebase_admin.initialize_app(cred, {
#         'databaseURL': 'https://v-guard-af8af-default-rtdb.firebaseio.com/'
#     })

# # ✅ Constants
# UPLOAD = 'uploads'
# THRESHOLD = 0.75
# COOLDOWN_SECONDS = 15
# NO_FACE_TIMEOUT = 20

# # ✅ Send SMS function
# def send_feedback_sms(contact_number):
#     try:
#         client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
#         message = client.messages.create(
#             body=f"Thanks for visiting! Please share your feedback here: {FEEDBACK_LINK}",
#             from_=TWILIO_PHONE,
#             to=f"+91{contact_number}"  # Modify if your contacts are stored with country code
#         )
#         print(f"✅ Feedback SMS sent to {contact_number}")
#     except Exception as e:
#         print(f"❌ Error sending SMS: {e}")

# # ✅ Face recognition logic
# def recognize_face(frame):
#     visitors = db.reference("visitors").get() or {}
#     for vid, v in visitors.items():
#         img_path = os.path.join(UPLOAD, v.get("photo_path", ""))
#         if not os.path.exists(img_path):
#             continue
#         try:
#             result = DeepFace.verify(frame, img_path,
#                                      model_name="SFace",
#                                      detector_backend="opencv",
#                                      enforce_detection=False)
#             if result["verified"] and result["distance"] < THRESHOLD:
#                 return vid, v
#         except Exception:
#             continue
#     return None, None

# # ✅ Main Attendance Loop
# def attendance_loop():
#     cap = cv2.VideoCapture(0)
#     if not cap.isOpened():
#         print("❌ Webcam not accessible.")
#         return

#     print("🎯 Starting attendance monitor...")
#     last_seen = {}
#     last_face_time = time()
#     last_no_face_log_time = time()

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         cv2.imshow("Live Attendance", frame)
#         if cv2.waitKey(1) & 0xFF == 27:
#             print("🛑 ESC pressed. Exiting.")
#             break

#         now_ts = time()
#         now = datetime.now()
#         vid, visitor = recognize_face(frame)

#         if vid:
#             last_face_time = now_ts
#             last_no_face_log_time = now_ts

#             if vid in last_seen and (now - last_seen[vid]).total_seconds() < COOLDOWN_SECONDS:
#                 continue  # Cooldown period

#             last_seen[vid] = now
#             person_logs = db.reference(f"attendance/{vid}")
#             logs = person_logs.get() or {}

#             active_log_id = None
#             for log_id in sorted(logs.keys(), reverse=True):
#                 entry = logs[log_id]
#                 if entry.get("check_out_time", "") == "":
#                     active_log_id = log_id
#                     break

#             now_str = now.strftime("%Y-%m-%d %H:%M:%S")

#             if not active_log_id:
#                 # ✅ First time - Check-in
#                 print(f"🟢 Check-in: {visitor['name']}")
#                 log_id = str(int(now_ts * 1000))
#                 person_logs.child(log_id).set({
#                     "name": visitor["name"],
#                     "photo_path": visitor.get("photo_path", ""),
#                     "gender": visitor.get("gender", "Unknown"),
#                     "purpose": visitor.get("purpose", "N/A"),
#                     "check_in_time": now_str,
#                     "check_out_time": "",
#                     "duration_seconds": "",
#                     "blacklisted": "no"
#                 })
#             else:
#                 # ✅ Already present - Check-out
#                 print(f"🔴 Check-out: {visitor['name']}")
#                 check_in_str = logs[active_log_id].get("check_in_time")
#                 try:
#                     check_in_time = datetime.strptime(check_in_str, "%Y-%m-%d %H:%M:%S")
#                     duration = int((now - check_in_time).total_seconds())
#                 except Exception:
#                     duration = 0

#                 person_logs.child(active_log_id).update({
#                     "check_out_time": now_str,
#                     "duration_seconds": duration
#                 })

#                 # ✅ Send SMS
#                 contact = visitor.get("contact", "")
#                 if contact:
#                     send_feedback_sms(contact)
#                 else:
#                     print(f"⚠️ No contact found for {visitor['name']}")

#         else:
#             elapsed = now_ts - last_face_time
#             if elapsed >= NO_FACE_TIMEOUT and (now_ts - last_no_face_log_time >= NO_FACE_TIMEOUT):
#                 print(f"⏱️ No face detected for {int(elapsed)} seconds.")
#                 last_no_face_log_time = now_ts

#         sleep(1)

#     cap.release()
#     cv2.destroyAllWindows()

# # ✅ Run
# if __name__ == "__main__":
#     attendance_loop()


import os
import cv2
import numpy as np
from time import sleep, time
from datetime import datetime
from deepface import DeepFace
from dotenv import load_dotenv
from twilio.rest import Client
import firebase_admin
from firebase_admin import credentials, db
import ctypes  # For showing a popup message

# ✅ Load .env
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
FEEDBACK_LINK = os.getenv("FEEDBACK_LINK")

# ✅ Print for confirmation
print("✅ TWILIO_ACCOUNT_SID:", TWILIO_ACCOUNT_SID)
print("✅ TWILIO_PHONE:", TWILIO_PHONE)
print("✅ FEEDBACK_LINK:", FEEDBACK_LINK)

# ✅ Firebase Init
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://v-guard-af8af-default-rtdb.firebaseio.com/'
    })

# ✅ Constants
UPLOAD = 'uploads'
THRESHOLD = 0.75
COOLDOWN_SECONDS = 15
NO_FACE_TIMEOUT = 20

# ✅ Send SMS function
def send_feedback_sms(contact_number):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Thanks for visiting! Please share your feedback here: {FEEDBACK_LINK}",
            from_=TWILIO_PHONE,
            to=f"+91{contact_number}"  # Modify if contacts are stored differently
        )
        print(f"✅ Feedback SMS sent to {contact_number}")
    except Exception as e:
        print(f"❌ Error sending SMS: {e}")

# ✅ Face recognition logic
def recognize_face(frame):
    visitors = db.reference("visitors").get() or {}
    for vid, v in visitors.items():
        img_path = os.path.join(UPLOAD, v.get("photo_path", ""))
        if not os.path.exists(img_path):
            continue
        try:
            result = DeepFace.verify(frame, img_path,
                                     model_name="SFace",
                                     detector_backend="opencv",
                                     enforce_detection=False)
            if result["verified"] and result["distance"] < THRESHOLD:
                return vid, v
        except Exception:
            continue
    return None, None

# ✅ Main Attendance Loop
def attendance_loop():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Webcam not accessible.")
        return

    print("🎯 Starting attendance monitor...")
    last_seen = {}
    last_face_time = time()
    last_no_face_log_time = time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow("Live Attendance", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            print("🛑 ESC pressed. Exiting.")
            break

        now_ts = time()
        now = datetime.now()
        vid, visitor = recognize_face(frame)

        if vid:
            last_face_time = now_ts
            last_no_face_log_time = now_ts

            # ✅ Check if visitor is blacklisted
            if str(visitor.get("blacklisted", "no")).lower() in ["yes", "true"]:
                print(f"⛔ {visitor['name']} is blacklisted. Access denied.")
                ctypes.windll.user32.MessageBoxW(0, f"{visitor['name']} is blacklisted. You are not allowed.", "Access Denied", 0x10)
                continue

            if vid in last_seen and (now - last_seen[vid]).total_seconds() < COOLDOWN_SECONDS:
                continue  # Cooldown period

            last_seen[vid] = now
            person_logs = db.reference(f"attendance/{vid}")
            logs = person_logs.get() or {}

            active_log_id = None
            for log_id in sorted(logs.keys(), reverse=True):
                entry = logs[log_id]
                if entry.get("check_out_time", "") == "":
                    active_log_id = log_id
                    break

            now_str = now.strftime("%Y-%m-%d %H:%M:%S")

            if not active_log_id:
                # ✅ First time - Check-in
                print(f"🟢 Check-in: {visitor['name']}")
                log_id = str(int(now_ts * 1000))
                person_logs.child(log_id).set({
                    "name": visitor["name"],
                    "photo_path": visitor.get("photo_path", ""),
                    "gender": visitor.get("gender", "Unknown"),
                    "purpose": visitor.get("purpose", "N/A"),
                    "check_in_time": now_str,
                    "check_out_time": "",
                    "duration_seconds": "",
                    "blacklisted": "no"
                })
            else:
                # ✅ Already present - Check-out
                print(f"🔴 Check-out: {visitor['name']}")
                check_in_str = logs[active_log_id].get("check_in_time")
                try:
                    check_in_time = datetime.strptime(check_in_str, "%Y-%m-%d %H:%M:%S")
                    duration = int((now - check_in_time).total_seconds())
                except Exception:
                    duration = 0

                person_logs.child(active_log_id).update({
                    "check_out_time": now_str,
                    "duration_seconds": duration
                })

                # ✅ Send SMS
                contact = visitor.get("contact", "")
                if contact:
                    send_feedback_sms(contact)
                else:
                    print(f"⚠️ No contact found for {visitor['name']}")

        else:
            elapsed = now_ts - last_face_time
            if elapsed >= NO_FACE_TIMEOUT and (now_ts - last_no_face_log_time >= NO_FACE_TIMEOUT):
                print(f"⏱️ No face detected for {int(elapsed)} seconds.")
                last_no_face_log_time = now_ts

        sleep(1)

    cap.release()
    cv2.destroyAllWindows()

# ✅ Run
if __name__ == "__main__":
    attendance_loop()
