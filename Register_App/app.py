import os
import cv2
import base64
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, session, url_for
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
from time import time
import dlib
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from flask import send_from_directory
import random
from werkzeug.utils import secure_filename

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Load environment ---
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key")
VERIFICATION_THRESHOLD = 0.6

# --- SMTP Config ---
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = os.environ.get("SMTP_PORT")
EMAIL_ADDRESS = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASS")

# Debug email config
logger.info(f"Email Config Check - Server: {SMTP_SERVER}, Port: {SMTP_PORT}, User: {EMAIL_ADDRESS}")
if not all([SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD]):
    logger.error("WARNING: One or more SMTP environment variables are missing. Email functionality will fail.")

# --- Upload folder ---
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads_reg")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Firebase init with better error handling ---
db_app = None
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_credentials.json")
        db_app = firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://v-guard-af8af-default-rtdb.firebaseio.com/'
        })
        logger.info("Firebase initialized successfully")
    else:
        db_app = firebase_admin.get_app()
        logger.info("Firebase already initialized")
except FileNotFoundError:
    logger.critical("FATAL ERROR: firebase_credentials.json not found. Database connection will fail.")
except Exception as e:
    logger.critical(f"FATAL ERROR: Firebase initialization error: {e}")

# Global reference for the database
db_ref = db.reference() if db_app else None

# --- Dlib models ---
try:
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
    face_recognizer = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat")
    logger.info("Dlib models loaded successfully")
except Exception as e:
    logger.error(f"WARNING: Dlib model files not found or initialized: {e}.")
    def get_face_embedding(cv2_img): 
        return np.random.rand(1, 128) # Mock array

# --- Helper functions ---
def l2_distance(vec1, vec2):
    return np.linalg.norm(np.array(vec1) - np.array(vec2))

# Redefining get_face_embedding just in case the try/except above skipped it
if 'detector' in locals():
    def get_face_embedding(cv2_img):
        """Detects face and computes the 128D embedding."""
        if not predictor or not face_recognizer: 
            logger.error("Face recognition models not loaded")
            return None
        try:
            rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
            faces = detector(rgb_img, 1) 
            
            if len(faces) == 0: 
                logger.warning("No faces detected in image")
                return None
                
            face = faces[0] 
            shape = predictor(rgb_img, face)
            embedding = face_recognizer.compute_face_descriptor(rgb_img, shape)
            embedding_array = np.array(embedding)
            
            logger.info(f"Generated embedding - Shape: {embedding_array.shape}")
            return embedding_array
            
        except Exception as e:
            logger.error(f"❌ ERROR during Dlib embedding generation: {e}")
            return None

# --- Email Functions ---
def send_email(recipient_email, recipient_name, profile_link):
    """Send email to visitor with their profile link"""
    logger.info(f"Attempting to send profile link email to: {recipient_email}")
    
    if not all([SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD]):
        error_msg = "Email environment variables missing. Skipping email."
        logger.error(error_msg)
        return False, error_msg
    
    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = "Visitor Registration Confirmed"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #3f37c9; text-align: center;">Visitor Registration Confirmed</h2>
                <p>Hello <strong>{recipient_name}</strong>,</p>
                <p>Your visitor registration has been successfully completed.</p>
                <p>You can access your profile using the link below:</p>
                <div style="text-align: center; margin: 25px 0;">
                    <a href="{profile_link}" 
                       style="background-color: #3f37c9; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Your Profile
                    </a>
                </div>
                <p><strong>Profile Link:</strong><br>
                <a href="{profile_link}">{profile_link}</a></p>
                <p>Please keep this link for future reference.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    This is an automated message from the Visitor Management System.
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
        server.quit()
        
        logger.info(f"✅ Profile link email successfully sent to {recipient_email}")
        return True, "Email sent successfully"
        
    except smtplib.SMTPAuthenticationError:
        error_msg = "SMTP Authentication Error: Check EMAIL_USER and EMAIL_PASS."
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"General Email error during visitor profile send: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def send_employee_notification(employee_email, employee_name, visitor_data, profile_url):
    """Send notification email to employee with a single 'View Visitor Profile' button."""
    logger.info(f"Attempting to send employee notification to: {employee_email}")
    
    if not all([SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD]):
        error_msg = "Email environment variables missing. Skipping employee notification."
        logger.error(error_msg)
        return False, error_msg

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = f"Visitor Request: {visitor_data['name']} wants to meet you"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = employee_email

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; background-color:#f8f9fa; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; padding: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h2 style="color: #3f37c9; text-align: center;">Visitor Meeting Request</h2>
                <p>Hello <strong>{employee_name}</strong>,</p>
                <p>A visitor has registered to meet you. Please review their profile and decide further action from the portal.</p>

                <div style="background-color: #f1f3f6; padding: 15px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Visitor Details:</h3>
                    <p><strong>Name:</strong> {visitor_data.get('name', 'N/A')}</p>
                    <p><strong>Email:</strong> {visitor_data.get('contact', 'N/A')}</p>
                    <p><strong>Purpose:</strong> {visitor_data.get('purpose', 'N/A')}</p>
                    <p><strong>Duration:</strong> {visitor_data.get('duration', 'N/A')}</p>
                    <p><strong>Visit Date:</strong> {visitor_data.get('visit_date', 'N/A')}</p>
                </div>

                <div style="text-align: center; margin: 25px 0;">
                    <a href="{profile_url}" 
                       style="background-color: #3f37c9; color: white; padding: 14px 30px; 
                              text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold;">
                        🔍 View Visitor Profile
                    </a>
                </div>

                <p style="font-size: 13px; color: #777; text-align: center;">
                    This is an automated message from the Secure Visitor Management System.
                </p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, employee_email, msg.as_string())
        server.quit()

        logger.info(f"✅ Employee notification successfully sent to {employee_email}")
        return True, "Employee notification sent successfully"

    except smtplib.SMTPAuthenticationError:
        error_msg = "SMTP Authentication Error: Check EMAIL_USER and EMAIL_PASS."
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"General Email error during employee notification send: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def send_custom_email(recipient_email, subject, body):
    """Send custom email for notifications"""
    logger.info(f"Attempting to send custom email to: {recipient_email}")
    
    if not all([SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD]):
        logger.error("Email environment variables missing. Skipping custom email.")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h3 style="color: #3f37c9;">Visitor Management System Notification</h3>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
                    {body.replace('\n', '<br>')}
                </div>
                <br>
                <p style="font-size: 12px; color: #666;">
                    This is an automated message from Visitor Management System
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, recipient_email, msg.as_string())
        server.quit()
        
        logger.info(f"✅ Custom email sent successfully to {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP Authentication Error during custom email. Check credentials.")
        return False
    except Exception as e:
        logger.error(f"General Email error during custom send: {e}")
        return False

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register')
def register_page():
    if db_ref is None:
        logger.error("Database is not initialized. Cannot retrieve employee list.")
        employees_list = []
    else:
        employees_ref = db_ref.child("employees")
        employees_data = employees_ref.get() or {}
        employees_list = []
        
        for emp_id, emp_data in employees_data.items():
            employees_list.append({
                'id': emp_id,
                'name': emp_data.get('name', 'Unknown'),
                'email': emp_data.get('email', ''),
                'department': emp_data.get('department', '')
            })
    
    return render_template('register.html', employees=employees_list)

@app.route('/employees', methods=["GET"])
def get_employees():
    try:
        employees_data = db_ref.child("employees").get()
        if not employees_data:
            return jsonify([])

        employees_list = []
        for emp_id, emp_info in employees_data.items():
            employees_list.append({
                "id": emp_id,
                "name": emp_info.get("name", "Unknown"),
                "department": emp_info.get("department", "N/A")
            })

        return jsonify(employees_list)
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        return jsonify({"error": "Failed to fetch employees"}), 500

@app.route('/register', methods=['POST'])
def finalize_registration():
    try:
        # Clear any existing session data first
        session.clear()
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data received"}), 400

        logger.info(f"--- STARTING NEW REGISTRATION FOR: {data.get('name')} ---")
        
        if db_ref is None:
            return jsonify({"success": False, "message": "Internal Server Error: Database not connected."}), 500

        name = data.get("name")
        email = data.get("email")
        duration = data.get("duration", "Not sure")
        photo_base64_full = data.get("photo_base64")
        visit_date = data.get("visit_date")

        if not all([name, email, photo_base64_full]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        if not photo_base64_full or "," not in photo_base64_full:
            return jsonify({"success": False, "message": "Invalid photo data"}), 400

        photo_base64 = photo_base64_full.split(",")[1]

        # Handle purpose and employee association
        purpose_type = data.get("purposeType")
        employee_id = data.get("employeeSelect")
        custom_purpose = data.get("purpose", "Other")

        employee_name = None
        employee_data = None
        requires_employee_approval = False  # Default to false

        # ONLY set requires_employee_approval to True when purpose is to meet employee
        if purpose_type == "meetEmployee" and employee_id:
            employee_data = db_ref.child(f"employees/{employee_id}").get()
            if employee_data:
                employee_name = employee_data.get('name')
                employee_email = employee_data.get('email')
                employee_dept = employee_data.get('department', 'N/A')
                purpose = f"Meeting with {employee_name} ({employee_dept})"
                requires_employee_approval = True  # ONLY for employee meetings
            else:
                purpose = "Meeting (Employee not found)"
                employee_id = None
                requires_employee_approval = False
        else:
            # For all other purposes, no employee approval needed
            purpose = custom_purpose
            requires_employee_approval = False

        # Save photo to uploads_reg folder
        try:
            image_data = base64.b64decode(photo_base64)
            
            uploads_reg_folder = "uploads_reg"
            if not os.path.exists(uploads_reg_folder):
                os.makedirs(uploads_reg_folder)
            
            filename = f"{name.replace(' ', '_')}_{int(time())}.jpg"
            filepath = os.path.join(uploads_reg_folder, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            photo_url = f"/uploads_reg/{filename}"
            logger.info(f"Photo saved successfully: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving photo: {e}")
            return jsonify({"success": False, "message": "Failed to save photo"}), 500

        # Generate face embedding
        try:
            np_img = np.frombuffer(base64.b64decode(photo_base64), np.uint8)
            cv2_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            embedding_array = get_face_embedding(cv2_img)
            if embedding_array is None:
                return jsonify({"success": False, "message": "No face detected in photo"}), 400
            embedding_str = " ".join(map(str, embedding_array.flatten().tolist()))
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return jsonify({"success": False, "message": "Face analysis failed"}), 500

        # ✅ CREATE NEW VISITOR
        visitor_id = str(int(time() * 1000))
        profile_link = request.url_root.rstrip("/") + url_for('profile_page', visitor_id=visitor_id)
        
        base_data = {
            "name": name,
            "contact": email,
            "photo_filename": filename,
            "photo_url": photo_url,
            "photo_path": filepath,
            "embedding": embedding_str,
            "blacklisted": "no",
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "profile_link": profile_link
        }
        
        # Create new visitor with basic_info
        db_ref.child(f"visitors/{visitor_id}/basic_info").set(base_data)
        logger.info(f"✅ NEW VISITOR CREATED: {name} with ID: {visitor_id}")

        # ✅ Create new visit record with employee approval logic
        visit_id = str(int(time() * 1000))
        
        # Determine initial status and approval based on whether employee approval is needed
        initial_status = "Pending Approval" if requires_employee_approval else "Registered"
        is_approved = not requires_employee_approval  # Auto-approved if no employee approval needed
        
        visit_data = {
            "visit_id": visit_id,
            "purpose": purpose,
            "employee_id": employee_id,
            "employee_name": employee_name if employee_name else "N/A",
            "duration": duration,
            "visit_date": visit_date if visit_date else datetime.now().strftime('%Y-%m-%d'),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "check_in_time": None,
            "check_out_time": None,
            "time_spent": None,
            "status": initial_status,  # "Pending Approval" for employee meetings, "Registered" for others
            "visit_approved": is_approved,  # False for employee meetings, True for others
            "has_visited": False,
            "requires_employee_approval": requires_employee_approval,  # CRITICAL: Only True for employee meetings
            "employee_notified": False,  # Will be updated after email sent
            "employee_actions": []  # Initialize empty actions array for tracking decisions
        }

        # Save the visit under visitor
        db_ref.child(f"visitors/{visitor_id}/visits/{visit_id}").set(visit_data)
        logger.info(f"✅ NEW VISIT CREATED under visitor {visitor_id} - Status: {initial_status}")

        # Update root visitor status based on whether approval is needed
        root_status = "Pending Approval" if requires_employee_approval else "Registered"
        db_ref.child(f"visitors/{visitor_id}").update({
            "status": root_status,
            "last_visit_id": visit_id
        })

        # ✅ STORE IN SESSION
        session['current_visitor'] = {
            'visitor_id': visitor_id,
            'visit_id': visit_id,
            'name': name,
            'email': email,
            'purpose': purpose,
            'status': initial_status,
            'photo_url': photo_url,
            'employee_name': employee_name,
            'visit_date': visit_date if visit_date else datetime.now().strftime('%Y-%m-%d'),
            'requires_employee_approval': requires_employee_approval
        }
        
        # Also set visitor_id in session for check-in page
        session['visitor_id'] = visitor_id
        session['last_registration_time'] = datetime.now().isoformat()

        # Send email to visitor
        email_success, email_message = send_email(email, name, profile_link)
        employee_notification_sent = False

        # ✅ ONLY send email notification if it's an employee meeting requiring approval
        if requires_employee_approval and employee_data and employee_data.get('email'):
            employee_email = employee_data.get('email')
            profile_url = f"https://verdie-fictive-margret.ngrok-free.dev/employee_action/{visitor_id}"
            
            visitor_data_for_employee = {
                "name": name,
                "contact": email,
                "purpose": purpose,
                "duration": duration,
                "visit_date": visit_date if visit_date else datetime.now().strftime("%Y-%m-%d"),
                "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            emp_success, emp_message = send_employee_notification(
                employee_email, 
                employee_name, 
                visitor_data_for_employee, 
                profile_url
            )
            employee_notification_sent = emp_success
            
            # Update visit with notification status
            if emp_success:
                db_ref.child(f"visitors/{visitor_id}/visits/{visit_id}").update({
                    "employee_notified": True,
                    "notification_sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                logger.info(f"✅ Employee notification sent to {employee_email}")
            else:
                logger.error(f"❌ Failed to send employee notification: {emp_message}")
        else:
            employee_notification_sent = False
            logger.info(f"ℹ️ No employee notification sent (purpose: {purpose_type}, requires_approval: {requires_employee_approval})")

        response_data = {
            "success": True,
            "message": "Registration complete." + (" Waiting for employee approval." if requires_employee_approval else ""),
            "redirect_url": "/check_in",
            "visitor_id": visitor_id,
            "visit_id": visit_id,
            "email_status": "success" if email_success else "failure",
            "employee_notified": employee_notification_sent,
            "photo_url": photo_url,
            "requires_employee_approval": requires_employee_approval,
            "current_status": initial_status
        }

        logger.info(f"--- NEW REGISTRATION COMPLETED SUCCESSFULLY FOR {name} ---")
        logger.info(f"📋 Registration Details: Purpose: {purpose}, Employee Approval Required: {requires_employee_approval}, Status: {initial_status}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Unexpected error in finalize_registration: {e}")
        return jsonify({"success": False, "message": "Internal server error"}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/check_in')
def check_in():
    # Try multiple ways to get visitor_id
    visitor_id = session.get("visitor_id") or request.args.get("visitor_id")
    logger.info(f"Check-in page accessed for visitor: {visitor_id}")

    if not visitor_id:
        logger.warning("No visitor_id found in session or URL parameters")
        return redirect("/")

    if db_ref is None:
        logger.error("Database connection not available")
        return render_template("check_in.html", visitor=None, recent_visit=None)

    try:
        # Fetch visitor info
        visitor_data = db_ref.child(f"visitors/{visitor_id}").get()
        if not visitor_data:
            logger.error(f"Visitor {visitor_id} not found in database")
            return redirect("/verify")

        basic_info = visitor_data.get("basic_info", {})
        visits = visitor_data.get("visits", {})
        
        logger.info(f"Found {len(visits)} visits for visitor {visitor_id}")

        recent_visit = None
        if visits:
            # Get the most recent visit (works for both new and returning visitors)
            sorted_visits = sorted(visits.items(), key=lambda x: x[0], reverse=True)
            
            if sorted_visits:
                latest_visit_id, latest_visit_data = sorted_visits[0]
                logger.info(f"Latest visit ID: {latest_visit_id}, Purpose: {latest_visit_data.get('purpose')}")
                
                recent_visit = {
                    "purpose": latest_visit_data.get("purpose", "Not specified"),
                    "duration": latest_visit_data.get("duration", "Not specified"),
                    "visit_date": latest_visit_data.get("visit_date", "Unknown"),
                    "employee_name": latest_visit_data.get("employee_name", "N/A"),
                    "status": latest_visit_data.get("status", "Registered"),
                    "employee_id": latest_visit_data.get("employee_id", None),
                    "visit_approved": latest_visit_data.get("visit_approved", False),
                    "has_visited": latest_visit_data.get("has_visited", False)
                }

        # Store visitor_id in session for future use
        session["visitor_id"] = visitor_id
        
        # Get email status from session or set default
        email_status = session.get("email_status", "unknown")
        email_message = session.get("email_message", "")

        logger.info(f"Rendering check-in page for {basic_info.get('name', 'Unknown')}")

        return render_template(
            "check_in.html",
            visitor=visitor_data,
            basic_info=basic_info,
            email_status=email_status,
            email_message=email_message,
            recent_visit=recent_visit,
            visitor_id=visitor_id
        )

    except Exception as e:
        logger.error(f"Error retrieving visitor data: {e}")
        return render_template(
            "check_in.html",
            visitor=None,
            recent_visit=None,
            email_status="error",
            email_message="Error loading visitor data"
        )

@app.route("/profile/<visitor_id>")
def profile_page(visitor_id):
    logger.info(f"Accessing profile page for: {visitor_id}")
    
    if db_ref is None:
        return "Internal Server Error: Database not connected.", 500
        
    visitor_data = db_ref.child(f"visitors/{visitor_id}").get()
    if not visitor_data:
        return "Profile not found", 404

    # Get basic info
    basic_info = visitor_data.get('basic_info', {})
    
    # Get visits history
    visits = visitor_data.get('visits', {})
    visits_list = []
    for visit_id, visit_data in visits.items():
        visits_list.append({
            'id': visit_id,
            'purpose': visit_data.get('purpose', 'N/A'),
            'employee_name': visit_data.get('employee_name', 'N/A'),
            'duration': visit_data.get('duration', 'N/A'),
            'visit_date': visit_data.get('visit_date', 'N/A'),
            'status': visit_data.get('status', 'N/A'),
            'check_in_time': visit_data.get('check_in_time', 'N/A'),
            'check_out_time': visit_data.get('check_out_time', 'N/A')
        })

    # Get transactions (if any)
    transactions = visitor_data.get('transactions', {})
    transactions_list = []
    for txn_id, txn_data in transactions.items():
        transactions_list.append({
            'id': txn_id,
            'check_in': txn_data.get('check_in_time', 'N/A'),
            'check_out': txn_data.get('check_out_time', 'N/A'),
            'duration': txn_data.get('duration_total', 'N/A')
        })

    logger.info(f"Profile page rendered for: {basic_info.get('name')}")
    
    return render_template(
        "profile_view.html",
        visitor=visitor_data,
        basic_info=basic_info,
        visitor_id=visitor_id,
        transactions=transactions_list,
        visits=visits_list,
        visit_count=len(visits_list),
        chatbot_url="https://chatbot-by3vbcpseur9ldw9ylnzpo.streamlit.app/"
    )
@app.route("/employee_action/<visitor_id>", methods=["GET"])
def employee_action(visitor_id):
    if not visitor_id:
        return render_template("error.html", message="Invalid visitor ID")

    if db_ref is None:
        return render_template("error.html", message="Database connection failed")

    try:
        visitor_data = db_ref.child(f"visitors/{visitor_id}").get()
        if not visitor_data:
            return render_template("error.html", message="Visitor not found")

        # Get basic info
        basic_info = visitor_data.get("basic_info", {})
        
        # Get the latest visit
        visits = visitor_data.get("visits", {})
        latest_visit_id, latest_visit = None, None
        if visits:
            sorted_visits = sorted(visits.items(), key=lambda x: x[0], reverse=True)
            latest_visit_id, latest_visit = sorted_visits[0]

        # Get photo
        photo_filename = basic_info.get("photo_filename")
        photo_url = None
        
        if photo_filename:
            clean_filename = os.path.basename(photo_filename)
            uploads_folder = "uploads_reg"
            photo_path = os.path.join(uploads_folder, clean_filename)
            
            if os.path.exists(photo_path):
                photo_url = f"/uploads_reg/{clean_filename}"

        # Extract details
        email = basic_info.get('contact', 'Not provided')
        purpose = latest_visit.get('purpose', 'Not specified') if latest_visit else 'Not specified'
        status = latest_visit.get('status', 'Unknown') if latest_visit else 'Unknown'
        visit_date = latest_visit.get('visit_date', 'Not scheduled') if latest_visit else 'Not scheduled'
        
        # Get employee actions history (renamed from previous_actions for clarity)
        employee_actions = latest_visit.get('employee_actions', []) if latest_visit else []
        
        # Get rejection reason if previously rejected
        rejection_reason = latest_visit.get('rejection_reason', '') if latest_visit else ''
        
        # Get reschedule details if previously rescheduled
        reschedule_date = latest_visit.get('new_visit_date', '') if latest_visit else ''
        reschedule_reason = latest_visit.get('reschedule_reason', '') if latest_visit else ''
        
        # Get last action details for display
        last_action = None
        last_action_by = None
        last_action_at = None
        if employee_actions:
            last_action_data = employee_actions[-1]  # Get most recent action
            last_action = last_action_data.get('action')
            last_action_by = last_action_data.get('by')
            last_action_at = last_action_data.get('timestamp')

        # Check if visit requires employee approval
        requires_approval = latest_visit.get('requires_employee_approval', False) if latest_visit else False

        return render_template("employee_action.html", 
                             visitor_id=visitor_id,
                             latest_visit_id=latest_visit_id,
                             photo_url=photo_url,
                             email=email,
                             purpose=purpose,
                             status=status,
                             visit_date=visit_date,
                             employee_actions=employee_actions,  # Changed from previous_actions
                             rejection_reason=rejection_reason,
                             reschedule_date=reschedule_date,
                             reschedule_reason=reschedule_reason,
                             last_action=last_action,
                             last_action_by=last_action_by,
                             last_action_at=last_action_at,
                             requires_employee_approval=requires_approval)

    except Exception as e:
        logger.error(f"Error in employee_action: {e}")
        return render_template("error.html", message="Something went wrong while fetching visitor data")

@app.route('/employee_action_approve/<visitor_id>', methods=['POST'])
def employee_action_approve(visitor_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400
            
        visit_id = data.get('visit_id')
        
        if not visit_id:
            return jsonify({
                'status': 'error',
                'message': 'Visit ID is required'
            }), 400
        
        # Update the visit status in Firebase
        visit_ref = db.reference(f'visitors/{visitor_id}/visits/{visit_id}')
        
        # Get current visit data
        visit_data = visit_ref.get() or {}
        
        # Update the visit status and timestamp
        updates = {
            'status': 'approved',
            'visit_approved': True,
            'approved_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # Merge updates with existing data
        visit_data.update(updates)
        visit_ref.update(updates)
        
        # Also update the main visitor's last_visit status
        visitor_ref = db.reference(f'visitors/{visitor_id}')
        visitor_ref.update({
            'last_visit_status': 'approved',
            'last_updated': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Visit approved successfully'
        })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error approving visit: {str(e)}'
        }), 500

@app.route('/employee_action_reject/<visitor_id>', methods=['POST'])
def employee_action_reject(visitor_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400
            
        visit_id = data.get('visit_id')
        rejection_reason = data.get('rejection_reason')
        
        if not visit_id:
            return jsonify({
                'status': 'error',
                'message': 'Visit ID is required'
            }), 400
        
        # Update the visit status in Firebase
        visit_ref = db.reference(f'visitors/{visitor_id}/visits/{visit_id}')
        
        # Get current visit data
        visit_data = visit_ref.get() or {}
        
        # Update the visit status and rejection reason
        updates = {
            'status': 'rejected',
            'rejection_reason': rejection_reason,
            'visit_approved': False,
            'rejected_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # Merge updates with existing data
        visit_data.update(updates)
        visit_ref.update(updates)
        
        # Also update the main visitor's last_visit status
        visitor_ref = db.reference(f'visitors/{visitor_id}')
        visitor_ref.update({
            'last_visit_status': 'rejected',
            'last_updated': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Visit rejected successfully'
        })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error rejecting visit: {str(e)}'
        }), 500

@app.route('/employee_action_reschedule/<visitor_id>', methods=['POST'])
def employee_action_reschedule(visitor_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400
            
        visit_id = data.get('visit_id')
        new_visit_date = data.get('new_visit_date')
        reschedule_reason = data.get('reschedule_reason')
        
        if not visit_id or not new_visit_date:
            return jsonify({
                'status': 'error',
                'message': 'Visit ID and new visit date are required'
            }), 400
        
        # Update the visit in Firebase
        visit_ref = db.reference(f'visitors/{visitor_id}/visits/{visit_id}')
        
        # Get current visit data
        visit_data = visit_ref.get() or {}
        
        # Update the visit date and status
        updates = {
            'status': 'rescheduled',
            'visit_date': new_visit_date,
            'reschedule_reason': reschedule_reason,
            'rescheduled_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # Merge updates with existing data
        visit_data.update(updates)
        visit_ref.update(updates)
        
        # Also update the main visitor's visit_date
        visitor_ref = db.reference(f'visitors/{visitor_id}')
        visitor_ref.update({
            'last_visit': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'status': 'success',
            'message': 'Visit rescheduled successfully'
        })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error rescheduling visit: {str(e)}'
        }), 500


@app.route("/verify")
def verify_page():
    logger.info("Verify page accessed")
    return render_template('verify.html')
@app.route("/verify-face", methods=['POST'])
def verify_face():
    data = request.get_json()
    logger.info("Face verification request received")
    
    try:
        # Extract and decode image
        captured_base64 = data["image"].split(",")[1]
        np_img = np.frombuffer(base64.b64decode(captured_base64), np.uint8)
        cv2_img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        
        if cv2_img is None:
            logger.warning("Unable to decode image during verification")
            return jsonify({"match": False, "message": "Unable to process image"})
        
        # Get live embedding
        live_embedding = get_face_embedding(cv2_img)
        
        if live_embedding is None:
            logger.warning("No face detected during verification")
            return jsonify({"match": False, "message": "No face detected"})
        
        # Check embedding dimensions
        if len(live_embedding) != 128:
            logger.error(f"Invalid embedding dimension: {len(live_embedding)} (expected 128)")
            return jsonify({"match": False, "message": "Face detection failed"})
        
        # ---- Compare with all visitors using basic_info.embedding ----
        all_visitors = db_ref.child("visitors").get() or {}
        matched_id, min_distance = None, float('inf')
        visitor_count = 0
        valid_embeddings = 0

        logger.info(f"Total visitors in DB for verification: {len(all_visitors)}")

        for vid, vdata in all_visitors.items():
            visitor_count += 1
            # Get embedding from basic_info section
            basic_info = vdata.get("basic_info", {})
            emb_str = basic_info.get("embedding")
            
            if not emb_str:
                continue
            
            try:
                # Parse the embedding string to numpy array
                stored_emb = np.array([float(x) for x in emb_str.strip().split()])
                valid_embeddings += 1
                
                # Ensure embeddings have the same dimensions
                if len(stored_emb) != len(live_embedding):
                    logger.warning(f"Embedding dimension mismatch for visitor {vid}: stored={len(stored_emb)}, live={len(live_embedding)}")
                    continue
                
                # Calculate Euclidean distance
                dist = np.linalg.norm(live_embedding - stored_emb)
                
                if dist < min_distance:
                    min_distance = dist
                    matched_id = vid
                    
            except Exception as e:
                logger.error(f"Error processing embedding for visitor {vid}: {e}")
                continue

        logger.info(f"Verification summary: {visitor_count} visitors checked, {valid_embeddings} valid embeddings, best distance: {min_distance:.4f}")

        THRESHOLD = 0.6
        
        if min_distance <= THRESHOLD and matched_id:
            # Fetch visitor name for logging
            visitor_data = db_ref.child(f"visitors/{matched_id}").get() or {}
            basic_info = visitor_data.get("basic_info", {})
            visitor_name = basic_info.get("name", "Unknown")
            
            session["visitor_id"] = matched_id
            logger.info(f"Face verified successfully for visitor: {visitor_name} (ID: {matched_id}), distance: {min_distance:.4f}")
            
            return jsonify({
                "match": True, 
                "redirect": "/old_register", 
                "message": f"Welcome back {visitor_name}! Verification successful.",
                "distance": round(float(min_distance), 4),
                "visitor_name": visitor_name
            })
        else:
            logger.info(f"Face not verified, closest distance: {min_distance:.4f}")
            return jsonify({
                "match": False, 
                "redirect": "/register", 
                "message": f"Not recognized. Please register as a new visitor.",
                "distance": round(float(min_distance), 4)
            })
            
    except Exception as e:
        logger.exception(f"Error during face verification: {e}")
        return jsonify({
            "match": False, 
            "message": f"Verification error: {str(e)}"
        })



@app.route("/old_register", methods=["GET", "POST"])
def old_register():
    visitor_id = session.get("visitor_id")
    if not visitor_id:
        logger.warning("No visitor_id in session for old_register, redirecting to verify")
        return redirect("/verify")

    if db_ref is None:
        logger.critical("DB_REF IS NONE. DATABASE IS NOT AVAILABLE.")
        return "Internal Server Error: Database not connected.", 500

    # --- Get visitor data ---
    visitor_data = db_ref.child(f"visitors/{visitor_id}").get()
    if not visitor_data:
        logger.error(f"Visitor data not found for ID: {visitor_id}")
        return redirect("/verify")

    # --- Fetch all employees for dropdown ---
    employees_data = db_ref.child("employees").get() or {}
    employees = {}
    for emp_id, emp in employees_data.items():
        employees[emp_id] = {
            "name": emp.get("name", "Unknown"),
            "department": emp.get("department", "N/A"),
            "email": emp.get("email", "")  # Include email for notification
        }

    if request.method == "POST":
        purpose_type = request.form.get("purpose_type")  # 'employee' or 'other'
        selected_employee_name = request.form.get("employee_name")  # Get employee name from dropdown
        other_purpose = request.form.get("other_purpose")
        visit_date = request.form.get("visit_date")
        duration = request.form.get("duration", "Not sure")

        employee_name = None
        employee_email = None
        purpose = "Not specified"

        # Find employee by name instead of ID
        if purpose_type == "employee" and selected_employee_name:
            employee_found = False
            for emp_id, emp_data in employees_data.items():
                if emp_data.get('name') == selected_employee_name:
                    employee_name = emp_data.get("name", "Unknown")
                    employee_email = emp_data.get("email")
                    department = emp_data.get("department", "N/A")
                    purpose = f"Meeting with {employee_name} ({department})"
                    employee_found = True
                    break
            
            if not employee_found:
                purpose = f"Meeting with {selected_employee_name} (Employee details not found)"
                employee_name = selected_employee_name
        elif purpose_type == "other" and other_purpose:
            purpose = other_purpose

        # Update basic visitor info
        visitor_ref = db_ref.child(f"visitors/{visitor_id}")
        visitor_ref.child("basic_info").update({
            "last_visit": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # --- Create a new visit record ---
        visit_id = str(int(time() * 1000))
        visit_record = {
            "visit_id": visit_id,
            "purpose": purpose,
            "employee_name": employee_name if employee_name else "N/A",
            "duration": duration,
            "visit_date": visit_date if visit_date else datetime.now().strftime("%Y-%m-%d"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "check_in_time": None,
            "check_out_time": None,
            "time_spent": None,
            "status": "Registered",
            "visit_approved": False if employee_name else True,  # approval needed if meeting employee
            "has_visited": False
        }

        # Store new visit under "visits" node
        visitor_ref.child(f"visits/{visit_id}").set(visit_record)
        logger.info(f"New visit added under returning visitor {visitor_id}")

        session["current_visit_id"] = visit_id

        # --- Profile link handling ---
        profile_link = visitor_data.get("basic_info", {}).get("profile_link") or (
            request.url_root.rstrip("/") + url_for('profile_page', visitor_id=visitor_id)
        )
        visitor_ref.child("basic_info").update({"profile_link": profile_link})
        session["profile_link"] = profile_link

        # --- Send email to visitor ---
        visitor_email = visitor_data.get("basic_info", {}).get("contact")
        visitor_name = visitor_data.get("basic_info", {}).get("name")
        email_success, email_message = send_email(visitor_email, visitor_name, profile_link)
        session["email_status"] = "success" if email_success else "failure"
        session["email_message"] = email_message
        logger.info(f"Returning visitor email: {'Success' if email_success else 'Failed'}")

        # --- Notify employee for approval/rejection ---
        employee_notification_sent = False
        if employee_email and employee_name:
            profile_url = f"http://127.0.0.1:5001/employee_action/{visitor_id}"
            
            # Prepare visitor data for employee notification email
            visitor_info_for_email = {
                "name": visitor_name,
                "contact": visitor_email,
                "purpose": purpose,
                "duration": duration,
                "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "visit_date": visit_date if visit_date else datetime.now().strftime("%Y-%m-%d")
            }
            
            emp_success, emp_message = send_employee_notification(
                employee_email,
                employee_name,
                visitor_info_for_email,
                profile_url
            )
            employee_notification_sent = emp_success
            logger.info(f"Employee notification: {'Success' if emp_success else 'Failed'} - {emp_message}")

        logger.info(f"Returning visitor registration completed for {visitor_name}")
        return redirect("/check_in")  # Redirect to check-in page

    # --- Render form page for returning visitor ---
    logger.info(f"Old register page rendered for returning visitor: {visitor_data.get('basic_info', {}).get('name')}")
    return render_template("old_register.html", visitor=visitor_data, employees=employees)



# File serving routes
@app.route('/uploads_reg/<filename>')
def serve_uploaded_photo(filename):
    return send_from_directory('uploads_reg', filename)

@app.route('/static/uploads_reg/<filename>')
def serve_static_uploaded_photo(filename):
    return send_from_directory('uploads_reg', filename)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

if __name__ == "__main__":
    logger.info("Starting Flask application...")
    app.run(host="0.0.0.0", port=5001, debug=True)
