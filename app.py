from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    jsonify,
    url_for,
    g
)
from werkzeug.middleware.proxy_fix import ProxyFix
from pathlib import Path
import tempfile
import uuid
import os
import logging
import time
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
import math


from werkzeug.utils import secure_filename


# ============================================================
# Project paths
# ============================================================

BASE_DIR = Path(__file__).parent

TEMP_UPLOAD_DIR = BASE_DIR / "temp_uploads"
TEMP_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# Import existing photo-processing system
# ============================================================

import sys

sys.path.insert(
    0,
    str(BASE_DIR / "src")
)

from specifications import SPECS, PhotoSpec
from photo_maker import create_recruitment_photo


# ============================================================
# Flask application
# ============================================================

app = Flask(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[]
)
# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


@app.before_request
def start_request_logging():

    if request.path.startswith(("/api", "/create", "/browser")):

        request.request_id = uuid.uuid4().hex[:8]
        request.start_time = time.perf_counter()

        logger.info(
            "REQUEST %s | %s %s",
            request.request_id,
            request.method,
            request.path
        )


@app.after_request
def finish_request_logging(response):

    if request.path.startswith(("/api", "/create", "/browser")):

        request_id = getattr(
            request,
            "request_id",
            "unknown"
        )

        start_time = getattr(
            request,
            "start_time",
            None
        )

        if start_time is not None:
            duration = time.perf_counter() - start_time
            duration_text = f"{duration:.3f}s"
        else:
            duration_text = "unknown"

        logger.info(
            "REQUEST %s | HTTP %s | %s",
            request_id,
            response.status_code,
            duration_text
        )

        response.headers["X-Request-ID"] = request_id

    return response

@app.after_request
def add_security_headers(response):

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Allow the public website to use browser endpoints
    if request.path.startswith("/browser/"):

        origin = request.headers.get("Origin")

        allowed_origins = {
            "https://photojob.me",
            "https://www.photojob.me",
            "http://127.0.0.1:5000",
            "http://localhost:5000"
        }

        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"

    return response


app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1
)
# ============================================================
# API Security
# ============================================================

API_KEY = os.environ.get(
    "PHOTO_MAKER_API_KEY"
)

app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# ============================================================
# API authentication
# ============================================================

def authenticate_api_request():

    # Browser endpoint is allowed to reuse the API processing logic
    # without exposing the API key to the browser.
    if getattr(g, "browser_request", False):
        logger.info(
            "REQUEST %s | Browser request: authentication bypassed",
            getattr(request, "request_id", "unknown")
        )
        return None

    if not API_KEY:
        logger.error(
            "REQUEST %s | API authentication failed: "
            "server API key is not configured",
            getattr(request, "request_id", "unknown")
        )

        return jsonify({
            "status": "ERROR",
            "error": "API key is not configured on the server."
        }), 500

    provided_key = request.headers.get("X-API-Key")

    if not provided_key:
        logger.warning(
            "REQUEST %s | API authentication failed: "
            "missing API key",
            getattr(request, "request_id", "unknown")
        )

        return jsonify({
            "status": "ERROR",
            "error": "Missing X-API-Key header."
        }), 401

    if provided_key != API_KEY:
        logger.warning(
            "REQUEST %s | API authentication failed: "
            "invalid API key",
            getattr(request, "request_id", "unknown")
        )

        return jsonify({
            "status": "ERROR",
            "error": "Invalid API key."
        }), 401

    logger.info(
        "REQUEST %s | API authentication: PASS",
        getattr(request, "request_id", "unknown")
    )

    return None


def find_uploaded_file(upload_id):
    """
    Find a temporary uploaded photo by its upload ID.
    Returns the path if valid, otherwise None.
    """

    if not upload_id:
        return None

    # UUIDs generated by /api/upload are 32 hexadecimal characters.
    if len(upload_id) != 32:
        return None

    try:
        int(upload_id, 16)
    except ValueError:
        return None

    matches = list(
        TEMP_UPLOAD_DIR.glob(f"{upload_id}.*")
    )

    if len(matches) != 1:
        return None

    file_path = matches[0]

    if not file_path.is_file():
        return None

    return file_path

# ============================================================
# Helper: convert specification to browser-friendly data
# ============================================================

def specification_info(spec):

    data = {
        "name": spec.name,
        "width_px": spec.width_px,
        "height_px": spec.height_px,
        "min_width_px": spec.min_width_px,
        "max_width_px": spec.max_width_px,
        "min_height_px": spec.min_height_px,
        "max_height_px": spec.max_height_px,
        "min_kb": spec.min_kb,
        "max_kb": spec.max_kb,
        "physical_size_mm": spec.physical_size_mm,
        "background": spec.background,
        "notes": spec.notes
    }

    return data

def cleanup_old_uploads(max_age_minutes=30):
    cutoff = datetime.now() - timedelta(
        minutes=max_age_minutes
    )

    for file_path in TEMP_UPLOAD_DIR.glob("*"):

        if not file_path.is_file():
            continue

        try:
            modified_time = datetime.fromtimestamp(
                file_path.stat().st_mtime
            )

            if modified_time < cutoff:
                file_path.unlink()

                logger.info(
                    "Cleanup | Deleted old temporary upload: %s",
                    file_path.name
                )

        except Exception:
            logger.exception(
                "Cleanup | Failed to delete temporary upload: %s",
                file_path
            )


def cleanup_old_outputs(max_age_hours=24):
    cutoff = datetime.now() - timedelta(hours=max_age_hours)

    for file_path in OUTPUT_DIR.glob("*"):

        if not file_path.is_file():
            continue

        try:
            modified_time = datetime.fromtimestamp(
                file_path.stat().st_mtime
            )

            if modified_time < cutoff:
                file_path.unlink()

                logger.info(
                    "Cleanup | Deleted old output: %s",
                    file_path.name
                )

        except Exception:
            logger.exception(
                "Cleanup | Failed to delete: %s",
                file_path
            )
def validate_custom_specification(
    ratio_width,
    ratio_height,
    long_side,
    max_kb
):
    if not math.isfinite(ratio_width) or not math.isfinite(ratio_height):
        return "Ratio values must be finite numbers."

    if ratio_width <= 0 or ratio_height <= 0:
        return "Ratio values must be greater than zero."

    if ratio_width > 100 or ratio_height > 100:
        return "Ratio values cannot exceed 100."

    if long_side <= 0 or long_side > 4000:
        return "long_side must be between 1 and 4000 pixels."

    if max_kb <= 0 or max_kb > 5000:
        return "max_kb must be between 1 and 5000 KB."

    if ratio_width >= ratio_height:
        width = long_side
        height = round(
            long_side * ratio_height / ratio_width
        )
    else:
        height = long_side
        width = round(
            long_side * ratio_width / ratio_height
        )

    if width <= 0 or height <= 0:
        return "Custom specification produces invalid dimensions."

    if width * height > 20_000_000:
        return "Requested image dimensions are too large."

    return None
# ============================================================
# Home page
# ============================================================

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "OK",
        "service": "Photo Maker API"
    }), 200

@app.route("/", methods=["GET"])
def index():

    specifications = {}

    for key, spec in SPECS.items():

        specifications[key] = (
            specification_info(spec)
        )

    return render_template(
        "index.html",
        specifications=specifications
    )

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "status": "ERROR",
        "error": "Uploaded file is too large. Maximum request size is 10 MB."
    }), 413

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({
        "status": "ERROR",
        "error": "Too many requests. Please try again later."
    }), 429

# ============================================================
# Create photo
# ============================================================

@app.route(
    "/create",
    methods=["POST"]
)
def create_photo():

    # --------------------------------------------------------
    # Check uploaded file
    # --------------------------------------------------------

    uploaded_file = request.files.get(
        "photo"
    )

    if (
        uploaded_file is None
        or uploaded_file.filename == ""
    ):

        return render_template(
            "index.html",
            specifications={
                key: specification_info(spec)
                for key, spec in SPECS.items()
            },
            error="Please select a photo."
        )


    # --------------------------------------------------------
    # Get selected specification
    # --------------------------------------------------------

    spec_key = request.form.get(
        "specification"
    )


    # --------------------------------------------------------
    # Build specification
    # --------------------------------------------------------
    if spec_key == "custom":

        try:

            ratio_width = float(
                request.form.get(
                    "ratio_width",
                    "3"
                )
            )

            ratio_height = float(
                request.form.get(
                    "ratio_height",
                    "4"
                )
            )

            long_side = int(
                request.form.get(
                    "long_side",
                    "800"
                )
            )

            max_kb = int(
                request.form.get(
                    "max_kb",
                    "100"
                )
            )

            # ------------------------------------------------
            # Validate custom specification
            # ------------------------------------------------

            validation_error = validate_custom_specification(
                ratio_width,
                ratio_height,
                long_side,
                max_kb
            )

            if validation_error:
                raise ValueError(validation_error)

            # ------------------------------------------------
            # Calculate dimensions
            # ------------------------------------------------

            if ratio_width >= ratio_height:

                width = long_side

                height = round(
                    long_side
                    * ratio_height
                    / ratio_width
                )

            else:

                height = long_side

                width = round(
                    long_side
                    * ratio_width
                    / ratio_height
                )

            spec = PhotoSpec(
                name=(
                    f"Custom "
                    f"{ratio_width:g}:"
                    f"{ratio_height:g}"
                ),

                width_px=width,

                height_px=height,

                max_kb=max_kb,

                background="white",

                notes=(
                    "Custom user-defined specification."
                )
            )

            output_name = (
                f"custom_"
                f"{uuid.uuid4().hex[:8]}"
                f".jpg"
            )

        except ValueError as error:

            logger.warning(
                "REQUEST %s | Validation failed: %s",
                getattr(request, "request_id", "unknown"),
                str(error)
            )

            return render_template(
                "index.html",
                specifications={
                    key: specification_info(spec)
                    for key, spec in SPECS.items()
                },
                error=str(error)
            ), 400


    # --------------------------------------------------------
    # Preset
    # --------------------------------------------------------

    else:

        if spec_key not in SPECS:

            return render_template(
                "index.html",
                specifications={
                    key: specification_info(spec)
                    for key, spec in SPECS.items()
                },
                error="Invalid specification."
            )


        spec = SPECS[
            spec_key
        ]

        output_name = (
            f"{spec_key}_"
            f"{uuid.uuid4().hex[:8]}.jpg"
        )
        


    # --------------------------------------------------------
    # --------------------------------------------------------
    # Save uploaded photo temporarily
    # --------------------------------------------------------

    safe_name = secure_filename(
        uploaded_file.filename
    )

    suffix = Path(
        safe_name
    ).suffix.lower()

    if suffix not in [".jpg", ".jpeg", ".png"]:
        return render_template(
            "index.html",
            specifications={
                key: specification_info(spec)
                for key, spec in SPECS.items()
            },
            error="Please upload a JPG, JPEG or PNG image."
        )


    temp_file = tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False
    )

    input_path = Path(
        temp_file.name
    )

    temp_file.close()

    uploaded_file.save(
        input_path
    )


    # --------------------------------------------------------
# Output
# --------------------------------------------------------

    output_path = (
        OUTPUT_DIR
        / output_name
    )

    # Calculate uploaded file size
    file_size_kb = input_path.stat().st_size / 1024

    logger.info(
        "REQUEST %s | Specification: %s",
        getattr(request, "request_id", "unknown"),
        spec.name
    )

    logger.info(
        "REQUEST %s | Uploaded file: %s | %.2f KB",
        getattr(request, "request_id", "unknown"),
        uploaded_file.filename,
        file_size_kb
    )

    logger.info(
        "REQUEST %s | Processing started",
        getattr(request, "request_id", "unknown")
    )


# --------------------------------------------------------
# Process
# --------------------------------------------------------

    try:

        result = create_recruitment_photo(
            input_path,
            output_path,
            spec
        )

        if result["status"] != "READY":

            logger.warning(
                "REQUEST %s | Processing produced invalid result: %s",
                getattr(request, "request_id", "unknown"),
                result["status"]
            )

            return render_template(
                "index.html",
                specifications={
                    key: specification_info(spec)
                    for key, spec in SPECS.items()
                },
                error=(
                    "The generated photo does not meet "
                    "the selected specification."
                )
            ), 400

    except ValueError as error:

        logger.warning(
            "REQUEST %s | Validation failed: %s",
            getattr(request, "request_id", "unknown"),
            str(error)
        )

        return render_template(
            "index.html",
            specifications={
                key: specification_info(spec)
                for key, spec in SPECS.items()
            },
            error=str(error)
        ), 400


    except Exception as error:

        logger.exception(
            "REQUEST %s | Processing failed",
            getattr(request, "request_id", "unknown")
        )

        return render_template(
            "index.html",
            specifications={
                key: specification_info(spec)
                for key, spec in SPECS.items()
            },
            error="An unexpected error occurred while processing the photo."
        ), 500

    finally:

        # Remove temporary uploaded image
        try:

            input_path.unlink(
                missing_ok=True
            )

        except Exception:

            pass


    logger.info(
        "REQUEST %s | Processing completed",
        getattr(request, "request_id", "unknown")
    )

    logger.info(
        "REQUEST %s | Output: %sx%s | %.2f KB",
        getattr(request, "request_id", "unknown"),
        result["resolution"]["width"],
        result["resolution"]["height"],
        result["file_size_kb"]
    )




    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return render_template(
        "index.html",

        specifications={
            key: specification_info(spec)
            for key, spec in SPECS.items()
        },

        result=result,

        output_filename=output_name,

        selected_spec=spec_key
    )


# ============================================================
# API Test Page
# ============================================================

@app.route("/api-test", methods=["GET"])
def api_test():

    specifications = {}

    for key, spec in SPECS.items():

        specifications[key] = specification_info(spec)

    return render_template(
        "api_test.html",
        specifications=specifications
    )

# ============================================================
# API information
# ============================================================

@app.route("/api", methods=["GET"])
def api_info():

    available_specs = {}

    for key, spec in SPECS.items():

        available_specs[key] = {
            "name": spec.name,
            "width_px": spec.width_px,
            "height_px": spec.height_px,
            "min_width_px": spec.min_width_px,
            "max_width_px": spec.max_width_px,
            "min_height_px": spec.min_height_px,
            "max_height_px": spec.max_height_px,
            "min_kb": spec.min_kb,
            "max_kb": spec.max_kb,
            "physical_size_mm": spec.physical_size_mm,
            "notes": spec.notes
        }

    return jsonify({
        "name": "Recruitment Photo Maker API",
        "version": "1.0",

        "description": (
            "Generate recruitment-ready passport photos "
            "from an uploaded JPG, JPEG or PNG image."
        ),

        "base_url": request.host_url.rstrip("/"),

        "endpoint": "/api/create-photo",
        "method": "POST",

        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "required": True
        },

        "upload": {
            "field": "photo",
            "accepted_formats": [
                "JPG",
                "JPEG",
                "PNG"
            ],
            "max_request_size_mb": 10
        },

        "specification_field": {
            "name": "specification",
            "required": True
        },

        "specifications": available_specs,

        "custom": {
            "description": "User-defined photo specification.",
            "required_fields": {
                "ratio_width": "number",
                "ratio_height": "number",
                "long_side": "integer",
                "max_kb": "integer"
            }
        },

        "response": {
            "success_status": 200,
            "success_format": "JSON",
            "fields": [
                "status",
                "specification",
                "resolution",
                "file_size_kb",
                "resolution_ok",
                "file_size_ok",
                "filename",
                "download_url"
            ]
        },

        "errors": {
            "400": "Invalid request or photo specification.",
            "401": "Missing or invalid API key.",
            "413": "Uploaded request exceeds the 10 MB limit.",
            "429": "Too many requests.",
            "500": "Unexpected server error."
        },

        "rate_limit": {
            "endpoint": "/api/create-photo",
            "limit": "10 requests per minute"
        }
    })

@app.route("/api/upload", methods=["POST"])
@limiter.limit("10 per minute")
def upload_photo_api():

    auth_error = authenticate_api_request()

    if auth_error:
        return auth_error

    if "photo" not in request.files:
        return jsonify({
            "status": "ERROR",
            "error": "No photo was uploaded."
        }), 400

    photo = request.files["photo"]

    if not photo or not photo.filename:
        return jsonify({
            "status": "ERROR",
            "error": "No photo was uploaded."
        }), 400

    original_name = secure_filename(photo.filename)

    if not original_name:
        return jsonify({
            "status": "ERROR",
            "error": "Invalid filename."
        }), 400

    allowed_extensions = {".jpg", ".jpeg", ".png"}

    extension = Path(original_name).suffix.lower()

    if extension not in allowed_extensions:
        return jsonify({
            "status": "ERROR",
            "error": "Unsupported image format. Use JPG, JPEG or PNG."
        }), 400

    # Clean up abandoned uploads before storing the new one
    cleanup_old_uploads()

    upload_id = uuid.uuid4().hex

    upload_path = TEMP_UPLOAD_DIR / f"{upload_id}{extension}"

    try:
        photo.save(upload_path)

        logger.info(
            "REQUEST %s | Upload stored: %s",
            getattr(request, "request_id", "unknown"),
            upload_path.name
        )

        return jsonify({
            "status": "UPLOADED",
            "upload_id": upload_id,
            "filename": original_name
        }), 200

    except Exception:
        logger.exception(
            "REQUEST %s | Upload failed",
            getattr(request, "request_id", "unknown")
        )

        if upload_path.exists():
            upload_path.unlink()

        return jsonify({
            "status": "ERROR",
            "error": "Could not store uploaded photo."
        }), 500


# ============================================================
# Browser: Upload photo
# ============================================================

@app.route("/browser/upload", methods=["POST"])
@limiter.limit("10 per minute")
def browser_upload_photo():

    if "photo" not in request.files:
        return jsonify({
            "status": "ERROR",
            "error": "No photo was uploaded."
        }), 400

    photo = request.files["photo"]

    if not photo or not photo.filename:
        return jsonify({
            "status": "ERROR",
            "error": "No photo was uploaded."
        }), 400

    original_name = secure_filename(photo.filename)

    if not original_name:
        return jsonify({
            "status": "ERROR",
            "error": "Invalid filename."
        }), 400

    allowed_extensions = {".jpg", ".jpeg", ".png"}

    extension = Path(original_name).suffix.lower()

    if extension not in allowed_extensions:
        return jsonify({
            "status": "ERROR",
            "error": "Unsupported image format. Use JPG, JPEG or PNG."
        }), 400

    # Remove abandoned temporary uploads
    cleanup_old_uploads()

    upload_id = uuid.uuid4().hex
    upload_path = TEMP_UPLOAD_DIR / f"{upload_id}{extension}"

    try:

        photo.save(upload_path)

        logger.info(
            "REQUEST %s | Browser upload stored: %s",
            getattr(request, "request_id", "unknown"),
            upload_path.name
        )

        return jsonify({
            "status": "UPLOADED",
            "upload_id": upload_id,
            "filename": original_name
        }), 200

    except Exception:

        logger.exception(
            "REQUEST %s | Browser upload failed",
            getattr(request, "request_id", "unknown")
        )

        if upload_path.exists():
            upload_path.unlink()

        return jsonify({
            "status": "ERROR",
            "error": "Could not store uploaded photo."
        }), 500
    

# ============================================================
# Browser: Create recruitment photo
# ============================================================

@app.route("/browser/create-photo", methods=["POST"])
@limiter.limit("10 per minute")
def browser_create_photo():

    # Mark this request as an internally trusted browser request.
    # This flag exists only on the server and is never sent by the browser.
    g.browser_request = True

    return create_photo_api()

# ============================================================
# API: Create recruitment photo
# ============================================================

@app.route("/api/create-photo", methods=["POST"])
@limiter.limit("10 per minute")

def create_photo_api():

        # --------------------------------------------------------
    # Authenticate API request
    # --------------------------------------------------------

    auth_error = authenticate_api_request()

    if auth_error:

        return auth_error

    # --------------------------------------------------------
    # Check uploaded photo
    # --------------------------------------------------------

    upload_id = request.form.get("upload_id")

    uploaded_file = None
    input_path = None
    temporary_upload = False

    if upload_id:
        # New two-step upload flow
        input_path = find_uploaded_file(upload_id)

        if input_path is None:
            return jsonify({
                "status": "ERROR",
                "error": "Uploaded photo was not found or has expired."
            }), 400

    else:
        # Existing direct-upload API flow
        uploaded_file = request.files.get("photo")

        if (
            uploaded_file is None
            or uploaded_file.filename == ""
        ):
            return jsonify({
                "status": "ERROR",
                "error": "No photo was uploaded."
            }), 400

        temporary_upload = True


    # --------------------------------------------------------
    # Validate file type
    # --------------------------------------------------------

    if input_path is not None:
        suffix = input_path.suffix.lower()

    else:
        safe_name = uploaded_file.filename

        suffix = Path(
            safe_name
        ).suffix.lower()

    if suffix not in [
        ".jpg",
        ".jpeg",
        ".png"
    ]:
        return jsonify({
            "status": "ERROR",
            "error": (
                "Unsupported image format. "
                "Use JPG, JPEG or PNG."
            )
        }), 400


    # --------------------------------------------------------
    # Get specification
    # --------------------------------------------------------

    spec_key = request.form.get(
        "specification"
    )


    if not spec_key:

        return jsonify({
            "status": "ERROR",
            "error": (
                "Missing 'specification'."
            )
        }), 400


    # ========================================================
# Custom specification
# ========================================================

    if spec_key == "custom":

        try:
            ratio_width = float(
                request.form.get("ratio_width", "")
            )

            ratio_height = float(
                request.form.get("ratio_height", "")
            )

            long_side = int(
                request.form.get("long_side", "")
            )

            max_kb = int(
                request.form.get("max_kb", "")
            )

        except (TypeError, ValueError):

            return jsonify({
                "status": "ERROR",
                "error": (
                    "Custom specification requires "
                    "valid ratio_width, ratio_height, "
                    "long_side and max_kb values."
                )
            }), 400

        # ----------------------------------------------------
        # Validate custom values
        # ----------------------------------------------------

        if not math.isfinite(ratio_width) or not math.isfinite(ratio_height):

            return jsonify({
                "status": "ERROR",
                "error": "Ratio values must be finite numbers."
            }), 400

        if ratio_width <= 0 or ratio_height <= 0:

            return jsonify({
                "status": "ERROR",
                "error": "Ratio values must be greater than zero."
            }), 400

        # Prevent absurd aspect ratios
        if ratio_width > 100 or ratio_height > 100:

            return jsonify({
                "status": "ERROR",
                "error": "Ratio values cannot exceed 100."
            }), 400

        # Prevent excessive image dimensions
        if long_side <= 0 or long_side > 4000:

            return jsonify({
                "status": "ERROR",
                "error": (
                    "long_side must be between "
                    "1 and 4000 pixels."
                )
            }), 400

        # Prevent excessive requested file size
        if max_kb <= 0 or max_kb > 5000:

            return jsonify({
                "status": "ERROR",
                "error": (
                    "max_kb must be between "
                    "1 and 5000 KB."
                )
            }), 400

        # ----------------------------------------------------
        # Calculate output dimensions
        # ----------------------------------------------------

        if ratio_width >= ratio_height:

            width = long_side

            height = round(
                long_side
                * ratio_height
                / ratio_width
            )

        else:

            height = long_side

            width = round(
                long_side
                * ratio_width
                / ratio_height
            )

        # ----------------------------------------------------
        # Final dimension safety check
        # ----------------------------------------------------

        if width <= 0 or height <= 0:

            return jsonify({
                "status": "ERROR",
                "error": (
                    "Custom specification produces "
                    "invalid dimensions."
                )
            }), 400

        if width * height > 20_000_000:

            return jsonify({
                "status": "ERROR",
                "error": (
                    "Requested image dimensions "
                    "are too large."
                )
            }), 400

        # ----------------------------------------------------
        # Create specification
        # ----------------------------------------------------

        spec = PhotoSpec(

            name=(
                f"Custom "
                f"{ratio_width:g}:"
                f"{ratio_height:g}"
            ),

            width_px=width,

            height_px=height,

            max_kb=max_kb,

            background="white",

            notes=(
                "Custom user-defined specification."
            )
        )

        output_name = (
            f"custom_"
            f"{uuid.uuid4().hex[:8]}"
            f".jpg"
        )

    # ========================================================
    # Preset specification
    # ========================================================

    else:

        if spec_key not in SPECS:

            return jsonify({
                "status": "ERROR",
                "error": (
                    f"Unknown specification: "
                    f"{spec_key}"
                )
            }), 400


        spec = SPECS[
            spec_key
        ]


        # ----------------------------------------------------
        # Prevent unsupported live-capture-only presets
        # ----------------------------------------------------

        if (
            not spec.width_px
            and not spec.height_px
            and not spec.min_width_px
        ):

            return jsonify({
                "status": "ERROR",
                "error": (
                    "This specification does not "
                    "define a generated image size."
                )
            }), 400


        output_name = (
            f"{spec_key}_"
            f"{uuid.uuid4().hex[:8]}"
            f".jpg"
        )


    # ========================================================
    # Temporary input file
    # ========================================================

    if input_path is None:

        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False
        )

        input_path = Path(
            temp_file.name
        )

        temp_file.close()

        uploaded_file.save(
            input_path
        )


    # ========================================================
    # Output path
    # ========================================================

    output_path = (
        OUTPUT_DIR
        / output_name
    )


    # ========================================================
    # Process image
    # ========================================================

    try:

        result = create_recruitment_photo(
            input_path,
            output_path,
            spec
        )


    except Exception as error:

        logger.exception(
            "REQUEST %s | Unexpected processing error",
            getattr(request, "request_id", "unknown")
        )

        return jsonify({
            "status": "ERROR",
            "error": "An unexpected error occurred while processing the photo."
        }), 500


    finally:

        # Delete temporary uploaded image
        try:

            input_path.unlink(
                missing_ok=True
            )

        except Exception:

            pass

    # ========================================================
    # Cleanup old generated outputs
    # ========================================================

    cleanup_old_outputs()


    # ========================================================
    # API response
    # ========================================================

    return jsonify({

        "status": result["status"],

        "specification": spec.name,

        "resolution": {
            "width": result[
                "resolution"
            ]["width"],

            "height": result[
                "resolution"
            ]["height"]
        },

        "file_size_kb":
            result["file_size_kb"],

        "resolution_ok":
            result["resolution_ok"],

        "file_size_ok":
            result["file_size_ok"],

        "filename":
            output_name,

        "download_url":
            url_for(
                "output_file",
                filename=output_name,
                _external=True
            )

    })


# ============================================================
# Serve generated images
# ============================================================

@app.route(
    "/output/<filename>"
)
def output_file(filename):

    return send_from_directory(
        OUTPUT_DIR,
        filename
    )


# ============================================================
# Open browser
# ============================================================

def open_browser():

    webbrowser.open(
        "http://127.0.0.1:5000"
    )


# ============================================================
# Start application
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )