# HFQVAP: Hybrid Face–QR Authentication for Visitor Management Systems

## Abstract

Single-factor authentication at visitor management gates presents inherent trade-offs: QR-only schemes are vulnerable to credential theft and sharing, while face-only schemes cannot disambiguate visually similar individuals without a secondary factor. This repository implements a **Hybrid Face–QR Visitor Authentication Protocol (HFQVAP)** that binds a per-visit QR token to biometric face verification through a five-state QR lifecycle with automatic invalidation on misuse. The system is configurable across three protocol variants — hybrid, face-only, and QR-only — under the same deployment, enabling direct comparison of security properties. All gate events are logged with protocol metadata for post-hoc analysis. The evaluation targets replay resistance, impersonation detection, stolen-credential handling, and twin disambiguation across the three variants.

## Research Problem

Visitor management gates require identity verification that is both secure (only the registered visitor gains access) and operationally practical (low friction at the gate). The two common single-factor approaches each leave specific threats unaddressed:

- **QR-only:** Any holder of the QR image can authenticate. A credential stolen inside the premises can be reused at departure. The system has no mechanism to verify that the person presenting the QR is its intended holder.
- **Face-only:** Access is bound to biometric identity, but visually similar individuals (twins, look-alikes) produce ambiguous matches. Without a secondary factor, the system cannot resolve which visitor is present.

This work investigates whether a hybrid protocol — cross-verifying face and QR with a token state machine and invalidation rules — addresses the weaknesses of either single-factor approach, and characterizes the trade-offs involved.

## Contributions

- **Protocol specification.** A hybrid face–QR authentication protocol with a five-state QR lifecycle (UNUSED, CHECKIN_USED, ASSUMED_SCANNED, CHECKOUT_USED, INVALIDATED), defined transition rules, and six operational invariants. The protocol is specified in [docs/Hybrid_Face_QR_Protocol.md](docs/Hybrid_Face_QR_Protocol.md), including state and sequence diagrams.
- **Threat analysis.** A qualitative threat model covering six categories (QR theft, QR replay, face spoofing, no-departure, post-entry QR theft, twin ambiguity) with per-threat comparison across all three variants. Limitations — notably liveness detection and tailgating — are explicitly scoped out.
- **Comparative evaluation framework.** A single codebase supporting three authentication modes (`hybrid`, `face_only`, `qr_only`) switchable via environment variable, with structured event logging (`auth_mode`, `protocol_config`) for reproducible comparison.

## System Architecture

```
├── docs/                  # Protocol specification and threat model
│   └── Hybrid_Face_QR_Protocol.md
├── Register_App/          # Visitor registration, QR issuance, host approval
│   ├── app.py             # Flask (Port 5001)
│   ├── chatbot.py         # Visitor assistant (Streamlit / Gemini)
│   └── templates/
├── Admin/                 # Dashboard, analytics, access-control list
│   ├── app.py             # Flask (Port 5000)
│   └── templates/
└── Webcam/                # Gate — protocol engine (AUTH_MODE configurable)
    ├── app.py             # Flask (Port 5002)
    ├── qr_module.py       # QR generation, validation, state machine
    └── templates/
```

| Component | Responsibility |
|-----------|---------------|
| Register_App | Visitor pre-registration, face embedding capture (dlib ResNet, 128-D), per-visit QR token generation (`secrets.token_urlsafe(32)`, JSON-encoded, visit-bound), host approval workflow. |
| Admin | Visitor and employee management, blacklist enforcement, feedback sentiment analysis, visit analytics. |
| Webcam | Gate endpoint implementing the three protocol variants: face matching, QR parsing and state management, cross-verification, invalidation logic, and structured event logging. |

Data is persisted in Firebase Realtime Database. All three components share the same database instance.

## Protocol Variants

The gate supports three modes selected via `AUTH_MODE`:

| Variant | Value | Gate behavior | QR state machine |
|---------|-------|---------------|------------------|
| Hybrid | `hybrid` | Face match + QR validation; cross-verification that both identify the same visitor. | Active: full lifecycle with invalidation on mismatch and stolen-QR detection. |
| Face-only | `face_only` | Face match only; QR data ignored. | Inactive: no state updates. |
| QR-only | `qr_only` | Valid QR token only; face not required. | Partial: token validated (expiry, state) but no face cross-check. |

The hybrid variant enforces six invariants: dual binding (face and QR must agree), single use per phase, mismatch invalidation, stolen-QR detection (face-only departure after QR arrival), blacklist enforcement, and token expiry. These are specified with state and sequence diagrams in the [protocol document](docs/Hybrid_Face_QR_Protocol.md).

## Threat Model

Six threat categories are analyzed. Full descriptions and per-variant handling are in the [protocol document](docs/Hybrid_Face_QR_Protocol.md).

| Threat | Face-only | QR-only | Hybrid |
|--------|-----------|---------|--------|
| T1. QR theft / sharing | N/A | Vulnerable | Mitigated (face–QR binding) |
| T2. QR replay | N/A | Mitigated (expiry + state) | Mitigated (expiry + state) |
| T3. Face spoofing | Out of scope (liveness assumption) | N/A | Same as face-only |
| T4. No departure | Operational (audit only) | Operational (audit only) | Operational (audit only) |
| T5. Post-entry QR theft | N/A | Vulnerable | Mitigated (invalidation on face-only departure) |
| T6. Twin / ambiguous face | Vulnerable | N/A | Mitigated (QR disambiguation) |

The hybrid variant addresses T1, T5, and T6 relative to the single-factor baselines. T3 (face spoofing) is an explicit non-goal: liveness detection is orthogonal to the protocol and is noted as an assumption. T4 (no departure) is operational and not mitigated by any variant.

## Evaluation

### Measured properties

| Property | Procedure | Applicable variants |
|----------|-----------|---------------------|
| Replay resistance | Resubmit a previously used QR; verify state-machine rejection. | QR-only, hybrid |
| Impersonation detection | Present a valid QR with a non-matching face; verify denial and QR invalidation. | Hybrid |
| Stolen-credential detection | Use QR at arrival, face-only at departure; verify QR invalidation and security alert. | Hybrid |
| Twin disambiguation | Present two visitors within the face-distance ambiguity threshold; verify QR-based resolution. | Face-only vs. hybrid |
| Gate response time | Measure time from HTTP request to response under each variant. | All |

### Event logs

| Firebase path | Contents |
|---------------|----------|
| `research_protocol_events/` | Arrival, departure, and invalidation events with `auth_mode`, `protocol_config`, `timestamp`, `visitor_id`, `visit_id`. |
| `visitors/{id}/visits/{id}/qr_state` | QR state snapshot: `status`, `scan_count`, `auth_method`, `invalidated_at`, `invalidated_reason`. |
| `visitors/{id}/visits/{id}/qr_scan_log/` | Chronological scan events: `scan_type`, `auth_mode`, `ip`, `face_distance`. |
| `visitors/{id}/transactions/` | Per-action log: `action`, `auth_mode`, `face_distance`, `timestamp`. |
| `security_alerts/` | Alert records: `alert_type` (QR_FACE_MISMATCH, QR_POSSIBLY_STOLEN, TWIN_DETECTED). |

### Comparison method

1. Deploy the gate under each `AUTH_MODE` in sequence or on parallel instances.
2. Execute a fixed set of scenarios: normal visit, QR reuse, QR presented by wrong person, face-only departure after QR arrival, twin presentation.
3. Export `research_protocol_events` and `security_alerts` from Firebase (console, REST API, or SDK).
4. Compare across variants: (a) threat detection coverage, (b) false rejection of legitimate visitors, (c) response latency.

## Reproducibility

### Switching modes

```bash
AUTH_MODE=hybrid    python Webcam/app.py   # default
AUTH_MODE=face_only python Webcam/app.py   # baseline A
AUTH_MODE=qr_only   python Webcam/app.py   # baseline B
```

Alternatively, set `AUTH_MODE` in `Webcam/.env`. The active mode is validated and logged at startup.

### Log locations

- **Protocol events:** `research_protocol_events/` — each record includes `protocol_config` (which mode was active).
- **QR state:** `visitors/{id}/visits/{id}/qr_state` and `qr_scan_log/`.
- **Security alerts:** `security_alerts/` at database root.

---

## Setup

### Prerequisites

- Python 3.8+
- Firebase Realtime Database credentials (`firebase_credentials.json`)
- Webcam or uploaded images for face registration
- Pre-trained models (included): `shape_predictor_68_face_landmarks.dat`, `dlib_face_recognition_resnet_model_v1.dat`, `sentiment_analysis.pkl`, `genderage.onnx`

### Installation

```bash
python3 -m venv venv && source venv/bin/activate

pip install -r Register_App/requirements.txt
pip install -r Admin/requirements.txt
pip install -r Webcam/requirements.txt
```

dlib requires CMake and platform libraries (`sudo apt-get install cmake libopenblas-dev liblapack-dev` on Debian/Ubuntu). See [dlib.net](http://dlib.net/compile.html) or use `conda install -c conda-forge dlib`.

### Configuration

Create `.env` in each component directory:

**Register_App/.env:**
```
SECRET_KEY=<secret>
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=<email>
EMAIL_PASS=<app_password>
GEMINI_API_KEY=<key>
```

**Admin/.env:**
```
SECRET_KEY=<secret>
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=<email>
EMAIL_PASS=<app_password>
REGISTRATION_APP_URL=http://localhost:5001
```

**Webcam/.env:**
```
SECRET_KEY=<secret>
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=<email>
EMAIL_PASS=<app_password>
COMPANY_IP=127.0.0.1
AUTH_MODE=hybrid
```

### Running

```bash
cd Register_App && python app.py   # Port 5001
cd Admin && python app.py          # Port 5000
cd Webcam && python app.py         # Port 5002
```

Place `firebase_credentials.json` in each component directory before starting.

## Scope and Limitations

- **Liveness detection** is not implemented. The threat model assumes face spoofing is handled by an orthogonal mechanism and explicitly scopes it out (T3).
- **Tailgating / no-departure** (T4) is an operational concern not addressed by any of the three protocol variants; the system provides audit logs but no automatic mitigation.
- **Face recognition accuracy** depends on dlib's pre-trained ResNet model and the quality of registered embeddings. The protocol evaluation focuses on the authentication logic, not on the underlying biometric performance.
- **QR token security** relies on `secrets.token_urlsafe(32)` for generation and HTTPS for transport in deployment. The protocol does not introduce novel cryptographic constructions.
- **Scale.** The system was tested in a single-gate, single-database configuration. Multi-gate or federated deployments are not evaluated.

## Security Notes

- Replace default `SECRET_KEY` values before any non-local deployment.
- Do not commit `firebase_credentials.json` to version control.
- Use HTTPS in production to protect QR tokens in transit.

## License

This project is provided for academic and research purposes.
