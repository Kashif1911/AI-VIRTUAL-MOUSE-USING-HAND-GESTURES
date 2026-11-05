from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    Response,
    redirect,
    url_for,
    session,
)
import atexit
import json
import os
import subprocess
import sys
from pathlib import Path
import secrets
import hmac
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from functools import wraps
from datetime import timedelta

import hashlib
import time
import secrets

import cv2
import numpy as np
from flask_limiter import Limiter
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import sqlite3

# Gmail SMTP configuration
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.environ.get("AI_VM_EMAIL", "").strip()
EMAIL_APP_PASSWORD = os.environ.get("AI_VM_EMAIL_APP_PASSWORD", "").replace(" ", "")


def send_password_reset_email(recipient_email, reset_link):
    """Send a password-reset link using Gmail SMTP."""
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        app.logger.error("Password-reset email is not configured.")
        return False

    message = EmailMessage()
    message["Subject"] = "AI Virtual Mouse - Password Reset"
    message["From"] = formataddr(
        ("AI Virtual Mouse", EMAIL_ADDRESS)
    )
    message["To"] = recipient_email

    message.set_content(
        "Hello,\n\n"
        "We received a request to reset your AI Virtual Mouse password.\n\n"
        f"Use this link to reset your password:\n{reset_link}\n\n"
        "If you did not request this, you can ignore this email.\n\n"
        "For your security, this link should expire and work only once.\n"
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(message)

        app.logger.info("Password-reset email sent successfully.")
        return True

    except (smtplib.SMTPException, OSError):
        app.logger.exception("Unable to send password-reset email.")
        return False



from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)
from auth.database import (
    initialize_database,
    create_user,
    user_exists,
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    update_user_profile,
    update_user_password,
    create_password_reset_token,
    get_valid_password_reset_token,
    reset_password_with_token,
)

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


def _load_secret_key():
    """
    Use AI_VM_SECRET_KEY if set; otherwise create a random key once and
    keep it in web/.secret_key so the app starts on any machine with no
    manual configuration (and sessions survive restarts).
    """
    env_key = os.environ.get("AI_VM_SECRET_KEY", "").strip()
    if env_key:
        return env_key

    key_file = Path(__file__).resolve().parent / ".secret_key"

    try:
        if key_file.exists():
            saved = key_file.read_text(encoding="utf-8").strip()
            if saved:
                return saved

        generated = secrets.token_hex(32)
        key_file.write_text(generated, encoding="utf-8")
        try:
            os.chmod(key_file, 0o600)
        except OSError:
            pass  # not supported on some filesystems / Windows
        return generated
    except OSError:
        # Read-only install: fall back to a per-run key
        return secrets.token_hex(32)


app.secret_key = _load_secret_key()

from datetime import timedelta

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
)




def get_csrf_token():
    token = session.get("csrf_token")

    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token

    return token


def csrf_protect(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if request.method == "POST":
            session_token = session.get("csrf_token")
            request_token = request.headers.get("X-CSRF-Token")

            if request_token is None:
                request_token = request.form.get("csrf_token")

            if (
                not session_token
                or not request_token
                or not hmac.compare_digest(
                    session_token,
                    request_token
                )
            ):
                return jsonify({
                    "success": False,
                    "message": "Invalid CSRF token."
                }), 403

        return view_function(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_csrf_token():
    return {
        "csrf_token": get_csrf_token()
    }




app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
initialize_database()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN_FILE = PROJECT_ROOT / "main.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.browser_frame import BrowserFrameBuffer

mouse_process = None
camera_mode = None

# One shared-memory frame buffer is used only for Browser Vision.
browser_frames = BrowserFrameBuffer(create=True)


def _close_browser_buffer():
    browser_frames.close()


atexit.register(_close_browser_buffer)


@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/logout", methods=["POST"])
@csrf_protect
def logout():

    session.clear()

    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "index.html",
        username=session.get("username")
    )


@app.route("/account/profile")
def account_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    return jsonify({
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "created_at": user["created_at"]
    })


@app.route("/account/profile/update", methods=["POST"])
@csrf_protect
def update_account_profile():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in again."
        }), 401

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not username or not email:
        return jsonify({
            "success": False,
            "message": "Username and email are required."
        }), 400
    
    if len(username) < 3:
        return jsonify({
            "success": False,
            "message": "Username must contain at least 3 characters."
        }), 400

    if not all(char.isalnum() or char in "_-" for char in username):
        return jsonify({
            "success": False,
            "message": "Username may contain only letters, numbers, underscores, and hyphens."
        }), 400

    email_parts = email.split("@")

    if (
        len(email_parts) != 2
        or not email_parts[0]
        or "." not in email_parts[1]
        or email_parts[1].startswith(".")
        or email_parts[1].endswith(".")
        or ".." in email
    ):
        return jsonify({
            "success": False,
            "message": "Please enter a valid email address."
        }), 400


    if len(username) > 50:
        return jsonify({
            "success": False,
            "message": "Username must be 50 characters or fewer."
        }), 400

    if len(email) > 254 or "@" not in email:
        return jsonify({
            "success": False,
            "message": "Please enter a valid email address."
        }), 400

    try:
        update_user_profile(
            session["user_id"],
            username,
            email
        )
    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "message": "That username or email is already in use."
        }), 409

    session["username"] = username

    return jsonify({
        "success": True,
        "message": "Profile updated successfully.",
        "username": username,
        "email": email
    })


@app.route("/account/password/change", methods=["POST"])
@csrf_protect
def change_account_password():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Please log in again."
        }), 401

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_password or not new_password or not confirm_password:
        return jsonify({
            "success": False,
            "message": "All password fields are required."
        }), 400

    
    if len(new_password) < 8:
        return jsonify({
            "success": False,
            "message": "The new password must contain at least 8 characters."
        }), 400

    if not any(char.isupper() for char in new_password):
        return jsonify({
            "success": False,
            "message": "The new password must contain at least one uppercase letter."
        }), 400

    if not any(char.islower() for char in new_password):
        return jsonify({
            "success": False,
            "message": "The new password must contain at least one lowercase letter."
        }), 400

    if not any(char.isdigit() for char in new_password):
        return jsonify({
            "success": False,
            "message": "The new password must contain at least one digit."
        }), 400

    if not any(not char.isalnum() for char in new_password):
        return jsonify({
            "success": False,
            "message": "The new password must contain at least one special character."
        }), 400


    if new_password != confirm_password:
        return jsonify({
            "success": False,
            "message": "The new passwords do not match."
        }), 400

    if current_password == new_password:
        return jsonify({
            "success": False,
            "message": "The new password must differ from the current password."
        }), 400

    user = get_user_by_id(session["user_id"])

    if user is None:
        session.clear()
        return jsonify({
            "success": False,
            "message": "Account not found. Please log in again."
        }), 401

    
    connection = None
    try:
        connection = sqlite3.connect(
            str(Path(__file__).resolve().parent / "auth" / "users.db")
        )
        connection.row_factory = sqlite3.Row
        password_record = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()
    finally:
        if connection is not None:
            connection.close()


    if password_record is None or not check_password_hash(
        password_record["password_hash"], current_password
    ):
        return jsonify({
            "success": False,
            "message": "The current password is incorrect."
        }), 400

    new_password_hash = generate_password_hash(new_password)

    update_user_password(session["user_id"], new_password_hash)

    return jsonify({
        "success": True,
        "message": "Password changed successfully."
    })




@app.route("/register", methods=["GET", "POST"])
@csrf_protect
def register():

    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Basic validation
    if not username:
        return render_template(
            "register.html",
            error="Username is required."
        )

    if not email:
        return render_template(
            "register.html",
            error="Email address is required."
        )

    if not password:
        return render_template(
            "register.html",
            error="Password is required."
        )

    
    
    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must contain at least 8 characters.",
            username=username,
            email=email,
        )

    if not any(char.isupper() for char in password):
        return render_template(
            "register.html",
            error="Password must contain at least one uppercase letter.",
            username=username,
            email=email,
        )

    if not any(char.islower() for char in password):
        return render_template(
            "register.html",
            error="Password must contain at least one lowercase letter.",
            username=username,
            email=email,
        )

    if not any(char.isdigit() for char in password):
        return render_template(
            "register.html",
            error="Password must contain at least one digit.",
            username=username,
            email=email,
        )

    if not any(not char.isalnum() for char in password):
        return render_template(
            "register.html",
            error="Password must contain at least one special character.",
            username=username,
            email=email,
        )

    if password != confirm_password:
        return render_template(
            "register.html",
            error="Passwords do not match.",
            username=username,
            email=email,
        )

    # Check for existing account
    if user_exists(username, email):
        return render_template(
            "register.html",
            error="Username or email is already registered.",
            username=username,
            email=email,
        )

    # Never store the plain-text password
    password_hash = generate_password_hash(password)

    try:
        create_user(
            username=username,
            email=email,
            password_hash=password_hash
        )

    except sqlite3.IntegrityError:
        return render_template(
            "register.html",
            error="Username or email is already registered."
        )

    return redirect(
        url_for("login", registered="1")
    )
@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
@csrf_protect
def login():

    if request.method == "GET":
        registered = request.args.get("registered")

        return render_template(
            "login.html",
            registered=registered
        )

    identifier = request.form.get(
        "identifier",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if not identifier or not password:
        return render_template(
            "login.html",
            error="Username/email and password are required."
        )

    # Try username first.
    user = get_user_by_username(identifier)

    # If not found, try email.
    if user is None:
        user = get_user_by_email(
            identifier.lower()
        )

    # Do not reveal whether the username/email exists.
    if user is None:
        return render_template(
            "login.html",
            error="Invalid username/email or password."
        )

    # Verify the stored password hash.
    if not check_password_hash(
        user["password_hash"],
        password
    ):
        return render_template(
            "login.html",
            error="Invalid username/email or password."
        )

    # Successful authentication.
    session.clear()

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session.permanent = True

    return redirect(
        url_for("dashboard")
    )


@app.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per minute", methods=["POST"])
@csrf_protect

def forgot_password():
    payload = request.get_json(silent=True) or {}
    email = str(
        payload.get("email", request.form.get("email", ""))
    ).strip().lower()

    message = (
        "If an account exists for that email, "
        "a password-reset link will be sent shortly."
    )

    if not email or len(email) > 254:
        return jsonify({
            "success": True,
            "message": message
        })

    user = get_user_by_email(email)

    if user is not None:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

        expires_at = int(time.time()) + 1800

        create_password_reset_token(
            user["id"], token_hash, expires_at
        )

        reset_link = url_for(
            "reset_password",
            token=raw_token,
            _external=True
        )

        if not send_password_reset_email(email, reset_link):
            app.logger.error(
                "Password-reset email delivery failed."
            )

    return jsonify({
        "success": True,
        "message": message
    })


@app.route("/reset-password/<token>", methods=["GET", "POST"])
@csrf_protect
def reset_password(token):
    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    now = int(time.time())
    valid_token = get_valid_password_reset_token(
        token_hash, now
    )

    if valid_token is None:
        return render_template(
            "reset_password.html",
            token="",
            error="This reset link is invalid, expired, or already used."
        ), 400

    if request.method == "GET":
        return render_template(
            "reset_password.html", token=token
        )

    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get(
        "confirm_password", ""
    )

    if len(new_password) < 8:
        error = "Password must contain at least 8 characters."
    elif not any(c.isupper() for c in new_password):
        error = "Password must contain an uppercase letter."
    elif not any(c.islower() for c in new_password):
        error = "Password must contain a lowercase letter."
    elif not any(c.isdigit() for c in new_password):
        error = "Password must contain a digit."
    elif not any(not c.isalnum() for c in new_password):
        error = "Password must contain a special character."
    elif new_password != confirm_password:
        error = "Passwords do not match."
    else:
        error = None

    if error:
        return render_template(
            "reset_password.html",
            token=token,
            error=error
        ), 400

    password_hash = generate_password_hash(new_password)

    success = reset_password_with_token(
        token_hash, int(time.time()), password_hash
    )

    if not success:
        return render_template(
            "reset_password.html",
            token="",
            error="This reset link is invalid, expired, or already used."
        ), 400

    return render_template(
        "reset_password.html",
        token="",
        success="Password reset successfully. You can now log in."
    )


@app.route("/api/start", methods=["POST"])
@csrf_protect
def start_mouse():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401
    global mouse_process, camera_mode

    if mouse_process is not None and mouse_process.poll() is None:
        return jsonify({
            "success": True,
            "running": True,
            "status": "started",
            "camera_mode": camera_mode or "window",
            "message": "AI Virtual Mouse is already running.",
        })

    payload = request.get_json(silent=True) or {}
    requested_mode = str(payload.get("camera_mode", "window")).lower()

    if requested_mode not in ("window", "browser"):
        requested_mode = "window"

    try:
        if requested_mode == "browser":
            browser_frames.clear()

        env = os.environ.copy()
        env["AI_VM_CAMERA_MODE"] = requested_mode

        mouse_process = subprocess.Popen(
            [sys.executable, str(MAIN_FILE)],
            cwd=str(PROJECT_ROOT),
            env=env,
        )

        camera_mode = requested_mode

        return jsonify({
            "success": True,
            "running": True,
            "status": "started",
            "camera_mode": requested_mode,
            "message": "AI Virtual Mouse started.",
        })

    except Exception as error:
        mouse_process = None
        camera_mode = None

        return jsonify({
            "success": False,
            "running": False,
            "message": str(error),
        }), 500


@app.route("/api/stop", methods=["POST"])
@csrf_protect
def stop_mouse():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    global mouse_process, camera_mode

    if mouse_process is None or mouse_process.poll() is not None:
        mouse_process = None
        camera_mode = None

        return jsonify({
            "success": True,
            "running": False,
            "message": "AI Virtual Mouse is not running.",
        })

    try:
        mouse_process.terminate()
        mouse_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        mouse_process.kill()
    finally:
        mouse_process = None
        camera_mode = None

    return jsonify({
        "success": True,
        "running": False,
        "message": "AI Virtual Mouse stopped.",
    })


@app.route("/api/browser_frame", methods=["POST"])
@csrf_protect
def browser_frame():

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401
    # The browser sends one JPEG frame at a time. Flask decodes it
    # and places the newest BGR frame into shared memory.
    if mouse_process is None or mouse_process.poll() is not None:
        return jsonify({
            "success": False,
            "message": "AI Virtual Mouse is not running.",
        }), 409

    if camera_mode != "browser":
        return jsonify({
            "success": False,
            "message": "Browser Vision is not the active camera mode.",
        }), 409

    raw = request.get_data(cache=False)

    if not raw or len(raw) > 350_000:
        return jsonify({
            "success": False,
            "message": "Invalid browser frame.",
        }), 400

    image = cv2.imdecode(
        np.frombuffer(raw, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        return jsonify({
            "success": False,
            "message": "Could not decode browser frame.",
        }), 400

    browser_frames.write(image)

    return Response(status=204)




@app.route("/api/status")
def status():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401
    global mouse_process, camera_mode

    process_running = (
        mouse_process is not None
        and mouse_process.poll() is None
    )

    status_file = PROJECT_ROOT / "web" / "status.json"

    data = {
        "running": process_running,
        "hand_detected": False,
        "gesture": "NONE",
        "fps": 0,
        "mode": "NORMAL",
        "camera_mode": camera_mode or "window",
    }

    if status_file.exists():
        try:
            with open(status_file, "r", encoding="utf-8") as file:
                engine_status = json.load(file)

            if not process_running:
                engine_status["running"] = False

            data.update(engine_status)

            if process_running:
                camera_mode = engine_status.get(
                    "camera_mode",
                    camera_mode,
                )

            data["camera_mode"] = camera_mode or engine_status.get(
                "camera_mode",
                "window",
            )

        except (json.JSONDecodeError, OSError):
            pass

    return jsonify(data)


if __name__ == "__main__":
    app.run(
        host=os.environ.get("AI_VM_HOST", "127.0.0.1"),
        port=int(os.environ.get("AI_VM_PORT", "5000")),
        debug=False,
    )
