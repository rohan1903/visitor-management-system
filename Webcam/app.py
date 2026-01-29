import os
import cv2
import base64
import numpy as np
import joblib 
from flask import Flask, render_template, request, jsonify, url_for
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta
from time import time
import onnxruntime as ort
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, url_for, session, redirect
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Dlib and Environment Setup ---
try:
    import dlib
except ImportError:
    dlib = None
    print("❌ CRITICAL ERROR: Dlib not installed. Face recognition disabled.")

# Load environment variables
load_dotenv()

# --- Configuration ---
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gate_app_secret_key_123") 
VERIFICATION_THRESHOLD = 0.6 
COMPANY_IP = os.environ.get("COMPANY_IP")

# --- SMTP Config ---
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = os.environ.get("SMTP_PORT")
EMAIL_ADDRESS = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASS")

# --- Firebase Initialization ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate("firebase_credentials.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://v-guard-af8af-default-rtdb.firebaseio.com/'
        })
        print("✅ Firebase initialized successfully.")
    except Exception as e:
        print(f"❌ Error initializing Firebase: {e}. Check firebase_credentials.json.")

# Logger and db reference
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
db_ref = db.reference()

# --- Helper Functions ---

def l2_distance(vec1, vec2):
    """Calculates the Euclidean distance between two face embeddings."""
    if vec1.shape != vec2.shape:
        if vec1.ndim > vec2.ndim:
            vec2 = vec2.reshape(vec1.shape)
        elif vec2.ndim > vec1.ndim:
            vec1 = vec1.reshape(vec2.shape)
    return np.linalg.norm(vec1 - vec2)

# Dlib Model Initialization
detector = dlib.get_frontal_face_detector() if dlib else None
predictor = None 
face_recognizer = None 

if dlib:
    try:
        predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        face_recognizer = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat")
        print("✅ Dlib Models loaded.")
    except Exception as e:
        print(f"❌ WARNING: Could not load Dlib models: {e}. Check file paths.")

def get_face_embedding(cv2_img):
    """Detects face and computes the 128D embedding."""
    if not predictor or not face_recognizer: return None
    try:
        rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        faces = detector(rgb_img, 1) 
        if len(faces) == 0: return None
        face = faces[0] 
        shape = predictor(rgb_img, face)
        embedding = face_recognizer.compute_face_descriptor(rgb_img, shape)
        return np.array(embedding)
    except Exception as e:
        print(f"❌ ERROR during Dlib embedding generation: {e}")
        return None

def verify_by_distance(live_embedding):
    """
    Compares a live embedding against ALL stored embeddings in Firebase.
    """
    visitors_ref = db.reference("visitors")
    all_visitors = visitors_ref.get()
    if not all_visitors:
        return None, 999.0

    min_distance = float('inf')
    matched_id = None

    for visitor_id, data in all_visitors.items():
        # Get embedding from basic_info section
        basic_info = data.get("basic_info", {})
        emb_raw = basic_info.get('embedding')
        if not emb_raw:
            continue

        try:
            # Convert space-separated string to numpy array
            stored_embedding = np.fromstring(emb_raw, sep=' ')
            
            # Ensure correct shape for distance calculation
            if stored_embedding.ndim == 1:
                stored_embedding = stored_embedding.reshape(1, -1)

            # Compute Euclidean distance
            distance = l2_distance(live_embedding, stored_embedding)

            # Keep track of the closest match
            if distance < min_distance:
                min_distance = distance
                matched_id = visitor_id

        except Exception as e:
            print(f"⚠️ Warning: skipping embedding for {visitor_id} due to error: {e}")
            continue

    # Return matched visitor ID only if distance is below threshold
    if matched_id is not None and min_distance <= VERIFICATION_THRESHOLD:
        return matched_id, min_distance
    return None, min_distance

# --- Email Functions ---

def send_feedback_email(visitor_email, visitor_name, feedback_link):
    """Send feedback request email to visitor after check-out"""
    logger.info(f"Attempting to send feedback email to: {visitor_email}")
    
    if not all([SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD]):
        error_msg = "Email environment variables missing. Skipping feedback email."
        logger.error(error_msg)
        return False, error_msg

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = "Share Your Feedback - Visitor Experience"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = visitor_email

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; background-color:#f8f9fa; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; padding: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h2 style="color: #3f37c9; text-align: center;">Share Your Feedback</h2>
                <p>Hello <strong>{visitor_name}</strong>,</p>
                <p>Thank you for visiting us! We hope you had a great experience.</p>
                <p>Your feedback is valuable to us and helps us improve our services. Please take a moment to share your experience:</p>

                <div style="text-align: center; margin: 25px 0;">
                    <a href="{feedback_link}" 
                       style="background-color: #3f37c9; color: white; padding: 14px 30px; 
                              text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                        📝 Share Feedback
                    </a>
                </div>

                <p style="font-size: 13px; color: #777; text-align: center;">
                    This feedback will help us enhance our visitor management system and services.
                </p>
                
                <p style="font-size: 13px; color: #777; text-align: center;">
                    Thank you for your time!
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, visitor_email, msg.as_string())
        server.quit()

        logger.info(f"✅ Feedback email successfully sent to {visitor_email}")
        return True, "Feedback email sent successfully"

    except smtplib.SMTPAuthenticationError:
        error_msg = "SMTP Authentication Error: Check EMAIL_USER and EMAIL_PASS."
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"General Email error during feedback email send: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def send_exceeded_email(visitor_email, visitor_name):
    """Send notification email when visitor exceeds duration limit"""
    if not visitor_email or visitor_email == 'N/A':
        return False, "No email address provided"
        
    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = "Visit Duration Exceeded - Action Required"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = visitor_email

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; background-color:#f8f9fa; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; padding: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h2 style="color: #dc3545; text-align: center;">Visit Duration Exceeded</h2>
                <p>Hello <strong>{visitor_name}</strong>,</p>
                <p>Your scheduled visit duration has been exceeded. Please proceed to check-out immediately at the kiosk.</p>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 15px; margin: 20px 0;">
                    <p style="color: #856404; margin: 0;">
                        <strong>Important:</strong> Please check out as soon as possible to avoid any issues.
                    </p>
                </div>

                <p style="font-size: 13px; color: #777; text-align: center;">
                    If you need to extend your visit, please contact security personnel.
                </p>
                
                <p style="font-size: 13px; color: #777; text-align: center;">
                    Thank you for your cooperation!
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, visitor_email, msg.as_string())
        server.quit()

        logger.info(f"✅ Exceeded duration email sent to {visitor_email}")
        return True, "Exceeded duration email sent successfully"

    except Exception as e:
        error_msg = f"Error sending exceeded duration email: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def simulate_send_email(recipient_email, subject, body):
    """Simulates sending an email and prints the email content to the console."""
    if recipient_email == 'N/A' or not recipient_email:
        print(f"📧 SKIPPED EMAIL: No email address provided for notification.")
        return
        
    print("--------------------------------------------------")
    print(f"📧 SIMULATED EMAIL SENT TO: {recipient_email}")
    print(f"SUBJECT: {subject}")
    print(f"BODY:\n{body}")
    print("--------------------------------------------------")

def check_for_expiring_visits():
    """Checks for visitors about to expire (30 minutes remaining) and simulates sending email."""
    visitors_ref = db.reference("visitors")
    all_visitors = visitors_ref.get()
    if not all_visitors: return "No visitors found."

    now = datetime.now()
    notification_count = 0
    
    for visitor_id, data in all_visitors.items():
        if data.get('status') == 'Checked-In' and 'expected_checkout_time' in data:
            try:
                expected_checkout = datetime.strptime(data['expected_checkout_time'], "%Y-%m-%d %H:%M:%S")
                time_remaining = expected_checkout - now
                
                # Notification window: between 0 and 30 minutes remaining
                if timedelta(minutes=0) < time_remaining <= timedelta(minutes=30):
                    if data.get('notified') != True:
                        remaining_minutes = int(time_remaining.total_seconds() / 60)
                        
                        # Get email from basic_info
                        basic_info = data.get("basic_info", {})
                        visitor_email = basic_info.get("contact")
                        
                        email_body = (
                            f"Dear {basic_info.get('name', 'Visitor')},\n\nYour scheduled visit "
                            f"is due to expire in approximately {remaining_minutes} minutes. Please check out at the Kiosk."
                        )
                        simulate_send_email(visitor_email, "Visit Duration Expiring Soon", email_body)
                        
                        visitors_ref.child(visitor_id).update({'notified': True})
                        notification_count += 1

            except Exception as e:
                print(f"Error processing notification for {data.get('name')}: {e}")

    return f"Processed notifications. {notification_count} emails simulated."

# --- Routes ---

@app.route("/")
@app.route("/checkin_gate")
def checkin_gate():
    """The main interface for automatic check-in/check-out."""
    return render_template("checkin_gate.html")

@app.route("/checkin_verify_and_log", methods=["POST"])
def checkin_verify_and_log():
    """
    Webcam endpoint with complete 7-state handling:
    - Registered, Approved, Rejected, Rescheduled, Checked-In, Checked-Out, Exceeded
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"status": "waiting", "message": "No image received.", "distance": 999.0})

        # IP check
        client_ip = request.remote_addr
        if COMPANY_IP and client_ip not in [COMPANY_IP, "127.0.0.1"]:
            return jsonify({"status": "denied", "message": "Access denied: Unauthorized IP.", "distance": 999.0})

        # ---- Decode image ----
        try:
            captured_base64 = data["image"].split(",")[1]
        except Exception:
            return jsonify({"status": "waiting", "message": "Invalid image payload.", "distance": 999.0})

        np_img = np.frombuffer(base64.b64decode(captured_base64), np.uint8)
        cv2_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        if cv2_img is None:
            return jsonify({"status": "waiting", "message": "Unable to decode image.", "distance": 999.0})

        # ---- Get live embedding ----
        live_embedding = get_face_embedding(cv2_img)
        if live_embedding is None:
            return jsonify({"status": "waiting", "message": "No face detected. Please position your face clearly in the camera.", "distance": 999.0})
        
        if len(live_embedding) != 128:
            return jsonify({"status": "waiting", "message": "Face detection failed. Please try again.", "distance": 999.0})

        # ---- Compare with all visitors ----
        all_visitors = db_ref.child("visitors").get() or {}
        matched_id, min_distance = None, float('inf')

        for vid, vdata in all_visitors.items():
            basic_info = vdata.get("basic_info", {})
            emb_str = basic_info.get("embedding")
            
            if not emb_str:
                continue
            
            try:
                stored_emb = np.array([float(x) for x in emb_str.strip().split()])
                
                if len(stored_emb) != len(live_embedding):
                    continue
                
                dist = np.linalg.norm(live_embedding - stored_emb)
                
                if dist < min_distance:
                    min_distance = dist
                    matched_id = vid
                    
            except Exception as e:
                continue

        THRESHOLD = 0.6

        if min_distance > THRESHOLD or matched_id is None:
            return jsonify({
                "status": "denied",
                "message": f"No match found. Closest distance: {min_distance:.4f} (threshold: {THRESHOLD})",
                "distance": round(float(min_distance), 4)
            })

        # ---- STEP 1: Check Blacklist Status ----
        visitor_id = matched_id
        visitor_ref = db_ref.child(f"visitors/{visitor_id}")
        visitor_data = visitor_ref.get()
        if not visitor_data:
            return jsonify({"status": "denied", "message": "Visitor record not found.", "distance": min_distance})

        basic_info = visitor_data.get("basic_info", {})
        visitor_name = basic_info.get("name", "Visitor")
        visitor_email = basic_info.get("contact")
        blacklisted = str(basic_info.get("blacklisted", "no")).lower()
        
        # Blacklist check
        if blacklisted in ['yes', 'true']:
            reason = basic_info.get('blacklist_reason', 'Security restriction')
            return jsonify({
                "status": "denied", 
                "message": f"Access denied. {visitor_name} is blacklisted. Reason: {reason}",
                "distance": min_distance
            })

        # ---- STEP 2: Check Most Recent Visit ----
        visits = visitor_data.get("visits", {})
        
        if not visits:
            return jsonify({
                "status": "denied",
                "message": f"No visits found for {visitor_name}. Please register a visit first.",
                "distance": min_distance
            })

        # Get the most recent visit (highest visit_id)
        sorted_visit_ids = sorted(visits.keys(), reverse=True)
        most_recent_visit_id = sorted_visit_ids[0]
        most_recent_visit = visits[most_recent_visit_id]
        
        print(f"🔍 DEBUG: Most recent visit ID: {most_recent_visit_id}")
        print(f"🔍 DEBUG: Visit data: {most_recent_visit}")

        # Check if visit date matches current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        visit_date = most_recent_visit.get('visit_date')
        
        if visit_date != current_date:
            return jsonify({
                "status": "denied",
                "message": f"Your visit is scheduled on {visit_date}, not today.",
                "distance": min_distance
            })

        # Get visit details FROM THE MOST RECENT VISIT
        visit_status = most_recent_visit.get('status', 'registered')
        employee_name = most_recent_visit.get('employee_name')
        has_visited = most_recent_visit.get('has_visited', False)
        purpose = most_recent_visit.get('purpose', '')
        check_in_time = most_recent_visit.get('check_in_time')
        duration = most_recent_visit.get('duration', '1 hour')
        rejection_reason = most_recent_visit.get('rejection_reason', '')
        new_visit_date = most_recent_visit.get('new_visit_date', '')
        
        print(f"🔍 DEBUG: Visitor: {visitor_name}, Visit ID: {most_recent_visit_id}")
        print(f"🔍 DEBUG: Status: {visit_status}, Employee: {employee_name}")
        print(f"🔍 DEBUG: Has visited: {has_visited}, Check-in time: {check_in_time}")

        # ---- STEP 3: Handle 7 Status Types ----
        
        # 1. REGISTERED STATE
        if visit_status.lower() == 'registered':
            if not employee_name or employee_name in ["N/A", ""]:
                # Allow check-in for registered visits without employee assignment
                return process_checkin(visitor_id, most_recent_visit_id, visitor_name, visitor_email, 
                                     employee_name, purpose, duration, min_distance, client_ip)
            else:
                # Employee meeting pending approval
                return jsonify({
                    "status": "denied", 
                    "message": f"Meeting pending approval from {employee_name}. Please wait for approval before checking in.",
                    "distance": min_distance
                })

        # 2. APPROVED STATE
        elif visit_status.lower() == 'approved':
            # Process check-in for approved visits
            result = process_checkin(visitor_id, most_recent_visit_id, visitor_name, visitor_email,
                                   employee_name, purpose, duration, min_distance, client_ip)
            
            # If check-in successful, modify message to include approval info
            if result.json and result.json.get('status') == 'granted':
                if employee_name and employee_name not in ["N/A", ""]:
                    return jsonify({
                        "status": "granted",
                        "name": visitor_name,
                        "message": f"{employee_name} approved {visitor_name}'s visit. Check-in successful.",
                        "distance": min_distance,
                        "redirect_url": url_for('checkin_success', name=visitor_name, action="checked in")
                    })
            return result

        # 3. REJECTED STATE
        elif visit_status.lower() == 'rejected':
            if employee_name and employee_name not in ["N/A", ""]:
                return jsonify({
                    "status": "denied", 
                    "message": f"{employee_name} has rejected your visit. You cannot check-in now." + 
                              (f" Reason: {rejection_reason}" if rejection_reason else ""),
                    "distance": min_distance
                })
            else:
                return jsonify({
                    "status": "denied", 
                    "message": f"Your visit has been rejected. You cannot check-in now." +
                              (f" Reason: {rejection_reason}" if rejection_reason else ""),
                    "distance": min_distance
                })

        # 4. RESCHEDULED STATE
        elif visit_status.lower() == 'rescheduled':
            reschedule_date = new_visit_date or visit_date
            if employee_name and employee_name not in ["N/A", ""]:
                return jsonify({
                    "status": "denied",
                    "message": f"{employee_name} has rescheduled your visit on {reschedule_date}. You cannot check-in today.",
                    "distance": min_distance
                })
            else:
                return jsonify({
                    "status": "denied",
                    "message": f"Your visit has been rescheduled to {reschedule_date}. You cannot check-in today.",
                    "distance": min_distance
                })

        # 5. CHECKED-IN STATE
        elif visit_status.lower() == 'checked_in':
            if has_visited:
                return jsonify({
                    "status": "denied",
                    "message": f"Visit already completed. Please register for a new visit.",
                    "distance": min_distance
                })
            return process_checkout(visitor_id, most_recent_visit_id, visitor_name, visitor_email,
                                  check_in_time, duration, min_distance, client_ip, purpose, employee_name)

        # 6. CHECKED-OUT STATE
        elif visit_status.lower() == 'checked_out':
            return jsonify({
                "status": "denied",
                "message": f"No pending visits for today, {visitor_name}.",
                "distance": min_distance
            })

        # 7. EXCEEDED STATE
        elif visit_status.lower() == 'exceeded':
            # Send exceeded notification email
            if visitor_email:
                send_exceeded_email(visitor_email, visitor_name)
            
            return jsonify({
                "status": "denied",
                "message": f"You have exceeded your duration limit. Please check out immediately.",
                "distance": min_distance
            })

        else:
            # Unknown status
            return jsonify({
                "status": "denied",
                "message": f"Access denied. Unknown visit status: {visit_status}",
                "distance": min_distance
            })

    except Exception as e:
        logger.exception("Unhandled exception in checkin_verify_and_log")
        return jsonify({"status": "error", "message": f"Server error: {e}", "distance": 999.0}), 500

def process_checkin(visitor_id, visit_id, visitor_name, visitor_email, employee_name, purpose, duration, min_distance, client_ip):
    """Process check-in for visitor"""
    try:
        now = datetime.now()
        
        # Parse duration
        try:
            duration_hours = float(str(duration).replace('hr', '').replace('hours', '').strip())
        except:
            duration_hours = 1.0
            
        expected_checkout = now + timedelta(hours=duration_hours)

        # Update visit record - ONLY UPDATE THE SPECIFIC VISIT
        db_ref.child(f"visitors/{visitor_id}/visits/{visit_id}").update({
            "check_in_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "has_visited": False,
            "status": "checked_in",
            "expected_checkout_time": expected_checkout.strftime("%Y-%m-%d %H:%M:%S")
        })

        # Log transaction
        log_key = now.strftime("%Y-%m-%d_%H:%M:%S")
        checkin_log = {
            "action": "check_in",
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": client_ip,
            "purpose": purpose,
            "visit_id": visit_id,
            "employee_name": employee_name,
            "duration": duration,
            "expected_checkout": expected_checkout.strftime("%Y-%m-%d %H:%M:%S"),
            "visitor_name": visitor_name
        }
        db_ref.child(f"visitors/{visitor_id}/transactions").child(log_key).set(checkin_log)

        # Determine message based on employee_name
        if employee_name and employee_name not in ["N/A", ""]:
            message = f"Successful check-in of {visitor_name}. Meeting with {employee_name}."
        else:
            message = f"Successful check-in of {visitor_name}."

        logger.info(f"Check-in completed for {visitor_name}, Visit ID: {visit_id}")
        return jsonify({
            "status": "granted",
            "name": visitor_name,
            "message": message,
            "distance": round(float(min_distance), 4),
            "redirect_url": url_for('checkin_success', name=visitor_name, action="checked in")
        })

    except Exception as e:
        logger.error(f"Error during check-in process: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error during check-in: {str(e)}",
            "distance": min_distance
        })
def process_checkout(visitor_id, visit_id, visitor_name, visitor_email, check_in_time, duration, min_distance, client_ip, purpose, employee_name):
    """Process check-out for visitor"""
    try:
        now = datetime.now()
        
        if not check_in_time:
            return jsonify({
                "status": "error",
                "message": "System error: No check-in time recorded.",
                "distance": min_distance
            })

        # Calculate visit duration
        start_time = datetime.strptime(check_in_time, "%Y-%m-%d %H:%M:%S")
        visit_duration = now - start_time
        
        # Format duration
        duration_hours = visit_duration.seconds // 3600
        duration_minutes = (visit_duration.seconds % 3600) // 60
        duration_seconds = visit_duration.seconds % 60
        
        if duration_hours > 0:
            time_spent = f"{duration_hours}h {duration_minutes}m {duration_seconds}s"
        else:
            time_spent = f"{duration_minutes}m {duration_seconds}s"
        
        # Check if time exceeded
        time_exceeded = False
        try:
            duration_hours_expected = float(str(duration).replace('hr', '').replace('hours', '').strip())
            expected_end = start_time + timedelta(hours=duration_hours_expected)
            if now > expected_end:
                time_exceeded = True
        except:
            pass

        # Determine final status
        final_status = "exceeded" if time_exceeded else "checked_out"

        # Update visit record
        db_ref.child(f"visitors/{visitor_id}/visits/{visit_id}").update({
            "has_visited": True,
            "check_out_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": final_status,
            "time_exceeded": time_exceeded,
            "time_spent": time_spent
        })

        # Log transaction
        log_key = now.strftime("%Y-%m-%d_%H:%M:%S")
        checkout_log = {
            "check_in": check_in_time,
            "check_out": now.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_total": str(visit_duration),
            "time_spent": time_spent,
            "distance": f"{min_distance:.4f}",
            "ip_address": client_ip,
            "purpose": purpose,
            "visit_id": visit_id,
            "status": final_status,
            "visitor_name": visitor_name,
            "employee_name": employee_name
        }
        db_ref.child(f"visitors/{visitor_id}/transactions").child(log_key).set(checkout_log)

        # Send feedback email for successful checkout (not for exceeded)
        if final_status == "checked_out" and visitor_email:
            try:
                feedback_link = f"https://verdie-fictive-margret.ngrok-free.dev/feedback_form?visitor_id={visitor_id}"
                email_sent, email_message = send_feedback_email(visitor_email, visitor_name, feedback_link)
                if email_sent:
                    logger.info(f"✅ Feedback email sent to {visitor_email}")
                else:
                    logger.warning(f"⚠️ Failed to send feedback email: {email_message}")
            except Exception as e:
                logger.error(f"❌ Error sending feedback email: {e}")

        # Send exceeded email if applicable
        if final_status == "exceeded" and visitor_email:
            send_exceeded_email(visitor_email, visitor_name)

        # Create the success message - MAKE SURE THIS IS CLEAR
        message = f"Successful checkout of {visitor_name}. Time spent: {time_spent}"
        if time_exceeded:
            message += " (Duration exceeded)"
            
        logger.info(f"Check-out completed for {visitor_name}, Visit ID: {visit_id}, Status: {final_status}, Time: {time_spent}")
        
        redirect_url = url_for('checkin_success', name=visitor_name, action="checked out", duration=time_spent, visitor_id=visitor_id)
        
        # Return the response - MAKE SURE STATUS IS 'checked_out'
        return jsonify({
            "status": "checked_out",  # This is crucial for frontend handling
            "name": visitor_name,
            "message": message,
            "distance": round(float(min_distance), 4),
            "redirect_url": redirect_url
        })

    except Exception as e:
        logger.error(f"Error during checkout process: {e}")
        return jsonify({
            "status": "error",
            "message": f"Error during checkout: {str(e)}",
            "distance": min_distance
        })
# @app.route("/checkin_verify_and_log", methods=["POST"])
# def checkin_verify_and_log():
#     """
#     Webcam endpoint with complete 7-state handling:
#     - Registered, Approved, Rejected, Rescheduled, Checked-In, Checked-Out, Exceeded
#     """
#     try:
#         data = request.get_json()
#         if not data or 'image' not in data:
#             return jsonify({"status": "waiting", "message": "No image received.", "distance": 999.0})

#         # IP check
#         client_ip = request.remote_addr
#         if COMPANY_IP and client_ip not in [COMPANY_IP, "127.0.0.1"]:
#             return jsonify({"status": "denied", "message": "Access denied: Unauthorized IP.", "distance": 999.0})

#         # ---- Decode image ----
#         try:
#             captured_base64 = data["image"].split(",")[1]
#         except Exception:
#             return jsonify({"status": "waiting", "message": "Invalid image payload.", "distance": 999.0})

#         np_img = np.frombuffer(base64.b64decode(captured_base64), np.uint8)
#         cv2_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
#         if cv2_img is None:
#             return jsonify({"status": "waiting", "message": "Unable to decode image.", "distance": 999.0})

#         # ---- Get live embedding ----
#         live_embedding = get_face_embedding(cv2_img)
#         if live_embedding is None:
#             return jsonify({"status": "waiting", "message": "No face detected. Please position your face clearly in the camera.", "distance": 999.0})
        
#         if len(live_embedding) != 128:
#             return jsonify({"status": "waiting", "message": "Face detection failed. Please try again.", "distance": 999.0})

#         # ---- Compare with all visitors ----
#         all_visitors = db_ref.child("visitors").get() or {}
#         matched_id, min_distance = None, float('inf')

#         for vid, vdata in all_visitors.items():
#             basic_info = vdata.get("basic_info", {})
#             emb_str = basic_info.get("embedding")
            
#             if not emb_str:
#                 continue
            
#             try:
#                 stored_emb = np.array([float(x) for x in emb_str.strip().split()])
                
#                 if len(stored_emb) != len(live_embedding):
#                     continue
                
#                 dist = np.linalg.norm(live_embedding - stored_emb)
                
#                 if dist < min_distance:
#                     min_distance = dist
#                     matched_id = vid
                    
#             except Exception as e:
#                 continue

#         THRESHOLD = 0.6

#         if min_distance > THRESHOLD or matched_id is None:
#             return jsonify({
#                 "status": "denied",
#                 "message": f"No match found. Closest distance: {min_distance:.4f} (threshold: {THRESHOLD})",
#                 "distance": round(float(min_distance), 4)
#             })

#         # ---- STEP 1: Check Blacklist Status ----
#         visitor_id = matched_id
#         visitor_ref = db_ref.child(f"visitors/{visitor_id}")
#         visitor_data = visitor_ref.get()
#         if not visitor_data:
#             return jsonify({"status": "denied", "message": "Visitor record not found.", "distance": min_distance})

#         basic_info = visitor_data.get("basic_info", {})
#         visitor_name = basic_info.get("name", "Visitor")
#         visitor_email = basic_info.get("contact")
#         blacklisted = str(basic_info.get("blacklisted", "no")).lower()
        
#         # Blacklist check
#         if blacklisted in ['yes', 'true']:
#             reason = basic_info.get('blacklist_reason', 'Security restriction')
#             return jsonify({
#                 "status": "denied", 
#                 "message": f"Access denied. {visitor_name} is blacklisted. Reason: {reason}",
#                 "distance": min_distance
#             })

#         # ---- STEP 2: Check Most Recent Visit ----
#         visits = visitor_data.get("visits", {})
#         eligible_visit_id, eligible_visit = None, None
#         sorted_visits = sorted(visits.items(), key=lambda x: x[0], reverse=True)
        
#         # Find the most recent visit that matches current date
#         current_date = datetime.now().strftime("%Y-%m-%d")
#         for vid, vdata in sorted_visits:
#             visit_date = vdata.get("visit_date")
#             has_visited = vdata.get("has_visited", False)
            
#             if visit_date == current_date:
#                 eligible_visit_id, eligible_visit = vid, vdata
#                 break

#         if not eligible_visit:
#             return jsonify({
#                 "status": "denied",
#                 "message": f"No visit found for {visitor_name} for today. Your visit is not scheduled for today.",
#                 "distance": min_distance
#             })

#         # Check if visit date matches current date
#         visit_date = eligible_visit.get('visit_date')
#         if visit_date != current_date:
#             return jsonify({
#                 "status": "denied",
#                 "message": f"Your visit is scheduled on {visit_date}, not today.",
#                 "distance": min_distance
#             })

#         # Get visit details
#         visit_status = eligible_visit.get('status', 'registered')
#         employee_name = eligible_visit.get('employee_name')
#         has_visited = eligible_visit.get('has_visited', False)
#         purpose = eligible_visit.get('purpose', '')
#         check_in_time = eligible_visit.get('check_in_time')
#         duration = eligible_visit.get('duration', '1 hour')

#         # ---- STEP 3: Handle 7 Status Types ----
        
#         # 1. REGISTERED STATE
#         if visit_status == 'Registered':
#             if not employee_name or employee_name == "N/A":
#                 # Allow check-in for registered visits without employee assignment
#                 return process_checkin(visitor_id, eligible_visit_id, visitor_name, visitor_email, 
#                                      employee_name, purpose, duration, min_distance, client_ip)
#             else:
#                 # Employee meeting pending approval
#                 return jsonify({
#                     "status": "denied", 
#                     "message": f"Meeting pending approval from {employee_name}. Please wait for approval before checking in.",
#                     "distance": min_distance
#                 })

#         # 2. APPROVED STATE
#         elif visit_status == 'Approved':
#             if employee_name:
#                 return jsonify({
#                     "status": "granted",
#                     "name": visitor_name,
#                     "message": f"{employee_name} approved {visitor_name}'s visit. Check-in successful.",
#                     "distance": min_distance,
#                     "redirect_url": url_for('checkin_success', name=visitor_name, action="checked in")
#                 })
#             else:
#                 return process_checkin(visitor_id, eligible_visit_id, visitor_name, visitor_email,
#                                      employee_name, purpose, duration, min_distance, client_ip)

#         # 3. REJECTED STATE
#         elif visit_status == 'Rejected':
#             rejection_reason = eligible_visit.get('rejection_reason', 'No reason provided')
#             if employee_name:
#                 return jsonify({
#                     "status": "denied", 
#                     "message": f"{employee_name} has rejected your visit. You cannot check-in now. Reason: {rejection_reason}",
#                     "distance": min_distance
#                 })
#             else:
#                 return jsonify({
#                     "status": "denied", 
#                     "message": f"Your visit has been rejected. You cannot check-in now. Reason: {rejection_reason}",
#                     "distance": min_distance
#                 })

#         # 4. RESCHEDULED STATE
#         elif visit_status == 'Rescheduled':
#             new_visit_date = eligible_visit.get('new_visit_date', eligible_visit.get('visit_date'))
#             if employee_name:
#                 return jsonify({
#                     "status": "denied",
#                     "message": f"{employee_name} has rescheduled your visit on {new_visit_date}. You cannot check-in today.",
#                     "distance": min_distance
#                 })
#             else:
#                 return jsonify({
#                     "status": "denied",
#                     "message": f"Your visit has been rescheduled to {new_visit_date}. You cannot check-in today.",
#                     "distance": min_distance
#                 })

#         # 5. CHECKED-IN STATE
#         elif visit_status == 'Checked_in':
#             return process_checkout(visitor_id, eligible_visit_id, visitor_name, visitor_email,
#                                   check_in_time, duration, min_distance, client_ip, purpose, employee_name)

#         # 6. CHECKED-OUT STATE
#         elif visit_status == 'Checked_out':
#             return jsonify({
#                 "status": "denied",
#                 "message": f"No pending visits for today, {visitor_name}.",
#                 "distance": min_distance
#             })

#         # 7. EXCEEDED STATE
#         elif visit_status == 'Exceeded':
#             # Send exceeded notification email
#             if visitor_email:
#                 send_exceeded_email(visitor_email, visitor_name)
            
#             return jsonify({
#                 "status": "denied",
#                 "message": f"You have exceeded your duration limit. Please check out immediately.",
#                 "distance": min_distance
#             })

#         else:
#             # Unknown status
#             return jsonify({
#                 "status": "denied",
#                 "message": f"Access denied. Unknown visit status: {visit_status}",
#                 "distance": min_distance
#             })

#     except Exception as e:
#         logger.exception("Unhandled exception in checkin_verify_and_log")
#         return jsonify({"status": "error", "message": f"Server error: {e}", "distance": 999.0}), 500

# def process_checkin(visitor_id, visit_id, visitor_name, visitor_email, employee_name, purpose, duration, min_distance, client_ip):
#     """Process check-in for visitor"""
#     try:
#         now = datetime.now()
        
#         # Parse duration
#         try:
#             duration_hours = float(str(duration).replace('hr', '').replace('hours', '').strip())
#         except:
#             duration_hours = 1.0
            
#         expected_checkout = now + timedelta(hours=duration_hours)

#         # Update visit record
#         db_ref.child(f"visitors/{visitor_id}/visits/{visit_id}").update({
#             "check_in_time": now.strftime("%Y-%m-%d %H:%M:%S"),
#             "has_visited": False,
#             "status": "checked_in",
#             "expected_checkout_time": expected_checkout.strftime("%Y-%m-%d %H:%M:%S")
#         })

#         # Log transaction
#         log_key = now.strftime("%Y-%m-%d_%H:%M:%S")
#         checkin_log = {
#             "action": "check_in",
#             "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
#             "ip_address": client_ip,
#             "purpose": purpose,
#             "visit_id": visit_id,
#             "employee_name": employee_name,
#             "duration": duration,
#             "expected_checkout": expected_checkout.strftime("%Y-%m-%d %H:%M:%S"),
#             "visitor_name": visitor_name
#         }
#         db_ref.child(f"visitors/{visitor_id}/transactions").child(log_key).set(checkin_log)

#         # Determine message
#         if employee_name and employee_name != "N/A":
#             message = f"Successful check-in of {visitor_name}. Meeting with {employee_name}."
#         else:
#             message = f"Successful check-in of {visitor_name}."

#         logger.info(f"Check-in completed for {visitor_name}")
#         return jsonify({
#             "status": "granted",
#             "name": visitor_name,
#             "message": message,
#             "distance": round(float(min_distance), 4),
#             "redirect_url": url_for('checkin_success', name=visitor_name, action="checked in")
#         })

#     except Exception as e:
#         logger.error(f"Error during check-in process: {e}")
#         return jsonify({
#             "status": "error",
#             "message": f"Error during check-in: {str(e)}",
#             "distance": min_distance
#         })

# def process_checkout(visitor_id, visit_id, visitor_name, visitor_email, check_in_time, duration, min_distance, client_ip, purpose, employee_name):
#     """Process check-out for visitor"""
#     try:
#         now = datetime.now()
        
#         if not check_in_time:
#             return jsonify({
#                 "status": "error",
#                 "message": "System error: No check-in time recorded.",
#                 "distance": min_distance
#             })

#         # Calculate visit duration
#         start_time = datetime.strptime(check_in_time, "%Y-%m-%d %H:%M:%S")
#         visit_duration = now - start_time
        
#         # Format duration
#         duration_hours = visit_duration.seconds // 3600
#         duration_minutes = (visit_duration.seconds % 3600) // 60
#         duration_seconds = visit_duration.seconds % 60
        
#         if duration_hours > 0:
#             time_spent = f"{duration_hours}h {duration_minutes}m {duration_seconds}s"
#         else:
#             time_spent = f"{duration_minutes}m {duration_seconds}s"
        
#         # Check if time exceeded
#         time_exceeded = False
#         try:
#             duration_hours_expected = float(str(duration).replace('hr', '').replace('hours', '').strip())
#             expected_end = start_time + timedelta(hours=duration_hours_expected)
#             if now > expected_end:
#                 time_exceeded = True
#         except:
#             pass

#         # Determine final status
#         final_status = "exceeded" if time_exceeded else "checked_out"

#         # Update visit record
#         db_ref.child(f"visitors/{visitor_id}/visits/{visit_id}").update({
#             "has_visited": True,
#             "check_out_time": now.strftime("%Y-%m-%d %H:%M:%S"),
#             "status": final_status,
#             "time_exceeded": time_exceeded,
#             "time_spent": time_spent
#         })

#         # Log transaction
#         log_key = now.strftime("%Y-%m-%d_%H:%M:%S")
#         checkout_log = {
#             "check_in": check_in_time,
#             "check_out": now.strftime("%Y-%m-%d %H:%M:%S"),
#             "duration_total": str(visit_duration),
#             "time_spent": time_spent,
#             "distance": f"{min_distance:.4f}",
#             "ip_address": client_ip,
#             "purpose": purpose,
#             "visit_id": visit_id,
#             "status": final_status,
#             "visitor_name": visitor_name,
#             "employee_name": employee_name
#         }
#         db_ref.child(f"visitors/{visitor_id}/transactions").child(log_key).set(checkout_log)

#         # Send feedback email for successful checkout (not for exceeded)
#         if final_status == "checked_out" and visitor_email:
#             try:
#                 feedback_link = f"http://127.0.0.1:5000/feedback_form?visitor_id={visitor_id}"
#                 email_sent, email_message = send_feedback_email(visitor_email, visitor_name, feedback_link)
#                 if email_sent:
#                     logger.info(f"✅ Feedback email sent to {visitor_email}")
#                 else:
#                     logger.warning(f"⚠️ Failed to send feedback email: {email_message}")
#             except Exception as e:
#                 logger.error(f"❌ Error sending feedback email: {e}")

#         # Send exceeded email if applicable
#         if final_status == "exceeded" and visitor_email:
#             send_exceeded_email(visitor_email, visitor_name)

#         message = f"Successful checkout of {visitor_name}. Time spent: {time_spent}"
#         if time_exceeded:
#             message += " (Duration exceeded)"
            
#         logger.info(f"Check-out completed for {visitor_name}: {final_status}, Time: {time_spent}")
        
#         redirect_url = url_for('checkin_success', name=visitor_name, action="checked out", duration=time_spent)
#         return jsonify({
#             "status": "checked_out",
#             "name": visitor_name,
#             "message": message,
#             "distance": round(float(min_distance), 4),
#             "redirect_url": redirect_url
#         })

#     except Exception as e:
#         logger.error(f"Error during checkout process: {e}")
#         return jsonify({
#             "status": "error",
#             "message": f"Error during checkout: {str(e)}",
#             "distance": min_distance
#         })

@app.route("/checkin_success")
def checkin_success():
    name = request.args.get('name', 'Visitor')
    action = request.args.get('action', 'processed')
    duration = request.args.get('duration')
    visitor_id = request.args.get('visitor_id', '')
    
    return render_template("checkin_success.html", 
                           visitor_name=name, 
                           action=action, 
                           duration=duration,
                           visitor_id=visitor_id)
@app.route("/trigger_notifications")
def trigger_notifications():
    """Route to manually trigger the notification check for demonstration."""
    notification_result = check_for_expiring_visits()
    return jsonify({"message": "Notification check executed successfully.", "result": notification_result})

@app.route("/feedback_form")
def feedback_form():
    visitor_id = request.args.get("visitor_id")
    return render_template("feedback_form.html", visitor_id=visitor_id)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    visitor_id = request.form.get('visitor_id')
    feedback_text = request.form.get('feedback_text')

    if not feedback_text or feedback_text.strip() == "":
        return render_template('feedback_form.html', visitor_id=visitor_id, error="Feedback cannot be empty!")

    try:
        # Store feedback under the visitor's ID in Realtime Database with proper structure
        feedback_ref = db.reference(f'visitors/{visitor_id}/feedbacks')
        new_feedback_ref = feedback_ref.push()
        new_feedback_ref.set({
            'text': feedback_text,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'visitor_id': visitor_id
        })
        print(f"✅ Feedback stored successfully for visitor {visitor_id}")
        
        # Verify storage
        stored_feedbacks = feedback_ref.get()
        print(f"📝 Total feedbacks stored: {len(stored_feedbacks) if stored_feedbacks else 0}")
        
    except Exception as e:
        print(f"❌ Error storing feedback: {e}")
        return render_template('feedback_form.html', visitor_id=visitor_id, error="Failed to store feedback. Please try again.")

    return render_template('thankyou.html', visitor_id=visitor_id)

# Employee Action Routes
@app.route('/employee_action/<visitor_id>')
def employee_action(visitor_id):
    try:
        visitor_ref = db.reference(f"visitors/{visitor_id}")
        visitor_data = visitor_ref.get()
        
        if not visitor_data:
            return "Visitor not found", 404
        
        # Get the latest visit
        visits = visitor_data.get("visits", {})
        latest_visit_id = None
        latest_visit = None
        
        if visits:
            latest_visit_id = max(visits.keys())
            latest_visit = visits[latest_visit_id]
        
        return render_template('employee_action.html',
                             visitor_id=visitor_id,
                             latest_visit_id=latest_visit_id,
                             purpose=latest_visit.get('purpose', 'Not specified') if latest_visit else 'Not specified',
                             status=latest_visit.get('status', 'registered') if latest_visit else 'registered',
                             visit_date=latest_visit.get('visit_date', 'Not specified') if latest_visit else 'Not specified',
                             photo_url=visitor_data.get('basic_info', {}).get('photo_url'))
    except Exception as e:
        return f"Error loading page: {str(e)}", 500

@app.route('/employee_action_approve/<visitor_id>', methods=['POST'])
def employee_action_approve(visitor_id):
    try:
        data = request.get_json()
        employee_name = data.get('employee_name', 'Employee')
        
        visitor_ref = db.reference(f"visitors/{visitor_id}")
        visitor_data = visitor_ref.get()
        
        if not visitor_data:
            return jsonify({'status': 'error', 'message': 'Visitor not found'}), 404
        
        # Get latest visit
        visits = visitor_data.get("visits", {})
        if not visits:
            return jsonify({'status': 'error', 'message': 'No visits found'}), 404
            
        latest_visit_id = max(visits.keys())
        
        # Update visit status
        db_ref.child(f"visitors/{visitor_id}/visits/{latest_visit_id}").update({
            'status': 'approved',
            'employee_name': employee_name,
            'approved_at': datetime.now().isoformat()
        })
        
        # Send notification email
        visitor_name = visitor_data.get('basic_info', {}).get('name', 'Visitor')
        visitor_email = visitor_data.get('basic_info', {}).get('contact')
        if visitor_email:
            email_body = f"""
            <p>Hi {visitor_name},</p>
            <p>Your visit has been approved by {employee_name}. You can now check-in on your scheduled date.</p>
            <p>Best regards,<br>Security Team</p>
            """
            # You can implement email sending here
        
        return jsonify({
            'status': 'success',
            'message': f'{employee_name} approved {visitor_name}\'s visit successfully'
        })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error approving visit: {str(e)}'
        }), 500

if __name__ == "__main__":
    print("--- GATE APP STARTUP ---")
    print(f"VERIFICATION THRESHOLD: {VERIFICATION_THRESHOLD}")
    if COMPANY_IP:
        print(f"✅ CHECK-IN IP ENFORCEMENT: {COMPANY_IP}")
    else:
        print("⚠️ WARNING: COMPANY_IP is not set in .env. IP check disabled.")
        
    app.run(host="0.0.0.0", port=5002, debug=True)