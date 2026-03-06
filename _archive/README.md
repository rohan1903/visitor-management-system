# Archived / redundant files

These files were moved here during project organisation. They are **not used** by the running apps. You can delete this folder after review.

| File | Original location | Reason |
|------|-------------------|--------|
| Register_App_generate_qr.py | Register_App/generate_qr.py | Standalone script with hardcoded URL; real QR is in app.py |
| Webcam_generate_qr.py | Webcam/generate_qr.py | Same; real QR logic is in qr_module.py |
| Admin_template_admin_dashboard.html | Admin/templates/admin_dashboard.html | Dashboard is inlined in Admin/app.py; this template is never loaded |
| Admin_template_feedback_analysis.html | Admin/templates/feedback_analysis.html | Feedback UI is inlined in app.py; not used |
| Admin_template_visitor.html | Admin/templates/visitor.html | Mostly commented out; not referenced by app.py |

See **docs/PROJECT_STRUCTURE.md** for full details.
