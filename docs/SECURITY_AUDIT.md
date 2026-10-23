# UEHIS — Security Audit & Secret Quarantine Report

**Audit Mode:** Automated Pattern Matching & Manual Tracked-Diff Review
**Target Directory:** `C:\Users\adity\Desktop\UEHIS-AWS-Recovery`
**Status:** **No matching credentials were detected in the scanned files using the documented checks**

---

## 1. Secret Scanning Results

The entire staged diff and all newly created files in `C:\Users\adity\Desktop\UEHIS-AWS-Recovery` were scanned for sensitive patterns under the documented detection rules:

| Pattern Category | Search Regex | Matches Found | Action Taken |
| :--- | :--- | :---: | :--- |
| **RSA / EC Private Keys** | `-----BEGIN [A-Z ]+PRIVATE KEY-----` | **0** | Quarantined via `*.pem` ignore rule |
| **JSON Web Tokens / Supabase Keys** | `eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}` | **0** | Quarantined via `.env` ignore rule |
| **AWS Access Key IDs** | `AKIA[0-9A-Z]{16}` | **0** | Quarantined |
| **GitHub Personal Access Tokens** | `ghp_[A-Za-z0-9]{36}` | **0** | Quarantined |
| **Database Connection Strings** | Standard URI Pattern | **0** | Quarantined via `.env` ignore rule |
| **Google Cloud Service Account JSON** | GCP Key Identifier Patterns | **0** | Quarantined via `*-project-*.json` ignore rule |

---

## 2. Hardened `.gitignore` Specification

The root `.gitignore` in `UEHIS-AWS-Recovery` includes explicit exclusion patterns:
```gitignore
# --- Credentials & local config ---
.env
.env.*
*.pem
*.crt
*-project-*.json
*service-account*.json
*credentials*.json
uehis-*-key*.json
```

---

## 3. Quarantined Production Files on Local Workstation

The following file patterns exist exclusively on local development machines and are **strictly excluded** from the Git index:
- Google Cloud GEE Service Account Key JSON files (`*-project-*.json`, `*service-account*.json`).
- SSH Private Key PEM files (`*.pem`).
- Environment configuration files containing tokens and connection strings (`.env`, `frontend/.env`).
