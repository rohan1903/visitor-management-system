# Visitor Management System (VMS)

A comprehensive visitor management system for educational institutions with face recognition, AI chatbot, and analytics capabilities.

## 🪟 Quick Start for Windows Users

If you're on Windows and your webcam doesn't work on Linux, follow these steps:

1. **Install Python 3.8+** from [python.org](https://www.python.org/downloads/)
2. **Open Command Prompt or PowerShell** as Administrator
3. **Navigate to project**: `cd path\to\major-project`
4. **Create virtual environment**: `python -m venv venv`
5. **Activate it**: `venv\Scripts\activate`
6. **Install dlib** (use conda if pip fails): `conda install -c conda-forge dlib`
7. **Follow Step 2-5 below** to install dependencies and run apps

**Note:** Even if your webcam doesn't work, you can test the system by uploading images manually during registration.

## 📁 Project Structure

```
major-project/
├── Register_App/          # Visitor Registration & Management System
│   ├── app.py            # Main Flask application (Port 5001)
│   ├── chatbot.py        # AI Chatbot (Streamlit)
│   ├── speech_app.py     # Speech-to-text service (Port 5000)
│   └── templates/        # HTML templates
│
├── Admin/                # Admin Dashboard
│   ├── app.py            # Admin Flask application (Port 5000)
│   └── templates/        # Admin dashboard templates
│
└── Webcam/               # Check-in Gate System
    ├── app.py            # Webcam check-in Flask app (Port 5002)
    └── templates/        # Check-in gate templates
```

## 🚀 Quick Start Guide

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Firebase credentials file (`firebase_credentials.json`)
- Webcam (for face recognition features) - **Note: If webcam doesn't work, you can still test with uploaded images**
- Required ML model files (already included in the project)

### Step 1: Setup Virtual Environment (Recommended)

Using a virtual environment prevents package conflicts and is especially recommended for Windows:

**Windows:**
```cmd
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# You should see (venv) in your prompt
```

**Linux/Mac:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# You should see (venv) in your prompt
```

**Note:** Activate the virtual environment before installing packages and running the apps.

### Step 2: Install Dependencies

Each component has its own requirements. Install them separately:

#### 📦 For Register_App:
**Linux/Mac:**
```bash
cd Register_App
pip install -r requirements.txt
pip install flask firebase-admin opencv-python dlib python-dotenv werkzeug
```

**Windows (Command Prompt or PowerShell):**
```cmd
cd Register_App
pip install -r requirements.txt
pip install flask firebase-admin opencv-python dlib python-dotenv werkzeug
```

#### 📦 For Admin:
**Linux/Mac:**
```bash
cd Admin
pip install -r requirements.txt
pip install flask firebase-admin pandas openpyxl python-dotenv scikit-learn
```

**Windows:**
```cmd
cd Admin
pip install -r requirements.txt
pip install flask firebase-admin pandas openpyxl python-dotenv scikit-learn
```

#### 📦 For Webcam:
**Linux/Mac:**
```bash
cd Webcam
pip install -r requirements.txt
pip install flask firebase-admin opencv-python dlib python-dotenv onnxruntime
```

**Windows:**
```cmd
cd Webcam
pip install -r requirements.txt
pip install flask firebase-admin opencv-python dlib python-dotenv onnxruntime
```

### 🔧 Installing dlib (Important!)

**dlib** is required for face recognition but can be tricky to install. Follow platform-specific instructions:

#### 🐧 Linux (Ubuntu/Debian):
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install cmake libopenblas-dev liblapack-dev libx11-dev libjpeg-dev

# Then install dlib
pip install dlib
```

#### 🪟 Windows:
**Option 1: Using pip (Easiest - Recommended)**
```cmd
pip install dlib
```

**Option 2: If pip fails, use conda (Recommended for Windows):**
```cmd
# Install Anaconda/Miniconda first, then:
conda install -c conda-forge dlib
```

**Option 3: Pre-built wheel (if above methods fail):**
1. Download dlib wheel from: https://pypi.org/project/dlib/#files
2. Choose the correct version for your Python version (e.g., `dlib-19.24.2-cp39-cp39-win_amd64.whl` for Python 3.9)
3. Install: `pip install path/to/downloaded/wheel.whl`

**Option 4: Build from source (Advanced):**
```cmd
# Install Visual Studio Build Tools first
# Then:
pip install cmake
pip install dlib
```

#### 🍎 macOS:
```bash
# Install Xcode Command Line Tools first
xcode-select --install

# Install dlib
pip install dlib
```

### Step 3: Setup Environment Variables

Create a `.env` file in each component directory with the following variables:

#### Register_App/.env:
```env
SECRET_KEY=your_secret_key_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
GEMINI_API_KEY=your_gemini_api_key
```

#### Admin/.env:
```env
SECRET_KEY=your_secret_key_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
REGISTRATION_APP_URL=http://localhost:5001
```

#### Webcam/.env:
```env
SECRET_KEY=your_secret_key_here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
COMPANY_IP=127.0.0.1
```

### Step 4: Firebase Setup

1. Ensure `firebase_credentials.json` is present in each component directory
2. The Firebase database URL is already configured in the code: `https://v-guard-af8af-default-rtdb.firebaseio.com/`

### Step 5: Run the Applications

You need to run each component in a separate terminal/command prompt window:

#### 🖥️ Windows Instructions:

**Terminal 1 - Register App (Port 5001):**
```cmd
cd Register_App
python app.py
```
Access at: http://localhost:5001

**Terminal 2 - Admin Dashboard (Port 5000):**
```cmd
cd Admin
python app.py
```
Access at: http://localhost:5000

**Terminal 3 - Webcam Check-in (Port 5002):**
```cmd
cd Webcam
python app.py
```
Access at: http://localhost:5002

**Terminal 4 - Speech App (Optional, Port 5000 - may conflict with Admin):**
```cmd
cd Register_App
python speech_app.py
```

**Terminal 5 - Chatbot (Streamlit):**
```cmd
cd Register_App
streamlit run chatbot.py
```
Access at: http://localhost:8501

#### 🐧 Linux/Mac Instructions:

**Terminal 1 - Register App (Port 5001):**
```bash
cd Register_App
python app.py
# or python3 app.py
```
Access at: http://localhost:5001

**Terminal 2 - Admin Dashboard (Port 5000):**
```bash
cd Admin
python app.py
# or python3 app.py
```
Access at: http://localhost:5000

**Terminal 3 - Webcam Check-in (Port 5002):**
```bash
cd Webcam
python app.py
# or python3 app.py
```
Access at: http://localhost:5002

**Terminal 4 - Speech App (Optional):**
```bash
cd Register_App
python speech_app.py
```

**Terminal 5 - Chatbot (Streamlit):**
```bash
cd Register_App
streamlit run chatbot.py
```
Access at: http://localhost:8501

## 🔧 Configuration

### Ports Summary:
- **Register_App**: Port 5001
- **Admin Dashboard**: Port 5000 (default Flask)
- **Webcam Check-in**: Port 5002
- **Speech App**: Port 5000 (conflicts with Admin - use different port if needed)
- **Chatbot**: Port 8501 (Streamlit default)

### Required Model Files:
The following model files should be present:
- `shape_predictor_68_face_landmarks.dat` (dlib face landmarks)
- `dlib_face_recognition_resnet_model_v1.dat` (dlib face recognition)
- `sentiment_analysis.pkl` (Admin sentiment analysis model)
- `genderage.onnx` (gender/age detection - Register_App)

## 📝 Features

### Register_App:
- Visitor registration with face capture
- Face recognition verification
- Employee management
- QR code generation
- AI chatbot for campus navigation
- Speech-to-text support
- Check-in/check-out system

### Admin Dashboard:
- Visitor management and tracking
- Employee management
- Feedback sentiment analysis
- Blacklist management
- Visitor analytics
- Email invitation system
- Excel bulk upload

### Webcam:
- Real-time face recognition check-in
- Automatic visitor verification
- Check-in/check-out logging
- Feedback collection
- Email notifications

## Troubleshooting

### Common Issues:

1. **dlib installation fails:**
   - **Windows**: Use conda or download pre-built wheel (see dlib installation section above)
   - **Linux**: Install system dependencies first: `sudo apt-get install cmake libopenblas-dev liblapack-dev`
   - **Alternative**: Use conda on any platform: `conda install -c conda-forge dlib`

2. **Webcam not working / Camera access issues:**
   
   **Windows:**
   - Check Windows Privacy Settings: Settings → Privacy → Camera → Allow apps to access camera
   - Grant permission to Python/your browser
   - Try different browsers (Chrome, Edge, Firefox)
   - Check if webcam works in other applications (Camera app, Zoom, etc.)
   - Update webcam drivers from device manufacturer
   - If using WSL (Windows Subsystem for Linux), webcam won't work - use native Windows Python
   
   **Linux:**
   - Check permissions: `ls -l /dev/video*` (should show your user has access)
   - Install v4l-utils: `sudo apt-get install v4l-utils`
   - Test webcam: `v4l2-ctl --list-devices`
   - Add user to video group: `sudo usermod -a -G video $USER` (logout/login required)
   - Check if webcam is being used by another app: `lsof | grep video`
   - Try: `sudo chmod 666 /dev/video0` (replace 0 with your device number)
   
   **Workaround if webcam doesn't work:**
   - You can still test the system by uploading images manually
   - The registration system supports image file uploads
   - Face recognition will work with uploaded images even without webcam

3. **Firebase connection errors:**
   - Verify `firebase_credentials.json` exists in each directory
   - Check Firebase database URL in code matches your project
   - Ensure you have internet connection
   - Check Firebase console for service status

4. **Port already in use:**
   - **Windows**: Find process using port: `netstat -ano | findstr :5001` then kill: `taskkill /PID <pid> /F`
   - **Linux/Mac**: Find process: `lsof -i :5001` then kill: `kill -9 <pid>`
   - Or change the port in the `app.run()` call at the bottom of each `app.py`

5. **Email not sending:**
   - For Gmail, use an "App Password" instead of your regular password
   - Generate App Password: Google Account → Security → 2-Step Verification → App Passwords
   - Enable "Less secure app access" (if available) or use OAuth2
   - Check firewall/antivirus isn't blocking SMTP connections

6. **Face recognition not working:**
   - Ensure webcam permissions are granted (see webcam troubleshooting above)
   - Check that model files are in the correct directory:
     - `shape_predictor_68_face_landmarks.dat`
     - `dlib_face_recognition_resnet_model_v1.dat`
   - Verify dlib is properly installed: `python -c "import dlib; print(dlib.__version__)"`
   - Test with uploaded images if webcam fails

7. **Python command not found (Windows):**
   - Use `py` instead of `python`: `py app.py`
   - Or use `python3` if you have multiple Python versions
   - Check Python is in PATH: `where python` (Windows) or `which python` (Linux/Mac)

8. **ModuleNotFoundError:**
   - Ensure you're in the correct directory
   - Install missing packages: `pip install <package_name>`
   - Use virtual environment to avoid conflicts: `python -m venv venv` then activate it

## 📚 Additional Notes

- The system uses Firebase Realtime Database for data storage
- Face recognition uses dlib with 128D embeddings
- Sentiment analysis uses a pre-trained scikit-learn model
- All three components share the same Firebase database
- Test upload images are preserved in `uploads/` directories

### 🌐 Platform-Specific Notes:

**Windows:**
- Use Command Prompt or PowerShell (both work)
- If `python` doesn't work, try `py` command
- Webcam access requires Windows Privacy Settings permission
- Recommended to use Anaconda/Miniconda for easier package management

**Linux:**
- May need to use `python3` instead of `python`
- Webcam may require user to be in `video` group
- Some distributions may need additional system packages

**Cross-Platform Testing:**
- You can develop on one platform and test on another
- Firebase and database work across all platforms
- Webcam functionality is platform-dependent

## 🔐 Security Notes

- Change default `SECRET_KEY` values in production
- Use environment variables for sensitive data (API keys, passwords)
- Never commit `firebase_credentials.json` to version control
- Use strong passwords and enable 2FA for email accounts

