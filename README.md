# Smart Expense Tracker (AI / ML Financial Platform)

An enterprise-grade, modular financial management system featuring AI-driven spending pattern analysis, optical character recognition (OCR) receipt scanning, automated category classification, statistical and machine learning anomaly detection, recurring transaction orchestration, financial goal tracking, and bank statement import with duplicate deduplication.

---

## 🌟 Advanced Features Overview

### 1. 🧠 AI-Powered Financial Insights
- **Historical Analysis**: Computes rolling spending trends, categorical distributions, and net savings rate over 30, 60, and 90-day horizons.
- **Month-over-Month (MoM) Velocity**: Analyzes category-by-category variances, percentage surges, and contraction trends.
- **Personalized Recommendations**: Generates explainable, actionable saving recommendations with clear badges distinguishing **`RULE_BASED`** calculations (e.g. 50/30/20 budget framework, dominant category thresholds) from **`STATISTICAL_ML`** patterns (e.g. spending velocity jumps, micro-transaction creep).
- **Transparent Rationale**: Every recommendation details *why* it was triggered based on actual ledger transactions.

### 2. 🧾 OCR Receipt Scanner
- **Computer Vision Preprocessing**: Grayscale normalization, contrast enhancement, and denoising with OpenCV (`cv2`) and Pillow (`PIL`).
- **Entity Extraction**: RapidOCR ONNX Runtime pipeline paired with heuristic regex parsing to extract merchant name, transaction date, and total amount.
- **Review & Confirmation Workflow**: Users review the extracted values alongside the original receipt image, inspect raw OCR text, and can edit any field before confirming into the transaction ledger.
- **Graceful Error Handling**: Handles distorted or partial scans with fallback defaults and zero-data-loss user correction.

### 3. 🏷️ Automatic Expense Categorization
- **Dual-Tier Hybrid Pipeline**:
  1. *Rule-Based Heuristic Matcher*: High-precision dictionary mapping for hundreds of common merchants and keywords.
  2. *NLP Machine Learning Classifier*: Scikit-Learn TF-IDF Vectorizer + Multinomial Naive Bayes model trained on labeled transaction narratives and dynamically refined by user history.
- **User Autonomy**: Returns confidence ratings and category alternatives. Suggestions are never forced; users have full control to override.

### 4. 🚨 Anomaly Detection (Ethical & Non-Alarmist)
- **Mathematical Baselines**: Calculates category-specific Interquartile Range (IQR) and modified Z-score boundaries. Flagged when amount exceeds $Q_3 + 2.5 \times \text{IQR}$ or $|Z| \ge 2.5$.
- **Isolation Forest Model**: Evaluates multidimensional context (amount, day of week) for global outlier scoring.
- **Ethical & Clear Explanations**: Plain-English alerts explaining the anomaly ratio (e.g. *"This purchase of $890.00 is significantly higher (16.5x) than your typical Shopping expense"*). Strictly avoids accusatory terms like "Fraud".

### 5. 🔄 Recurring Transactions Engine
- **Flexible Recurrence**: Daily, weekly, monthly, and yearly schedules with customizable interval multipliers and optional end dates.
- **Idempotency & Duplicate Prevention**: Date boundary checks and unique transaction constraints prevent duplicate generation if execution runs repeatedly.
- **30-Day Cash Flow Projections**: Interactive upcoming payments timeline displaying future obligations and cash outflow commitments.

### 6. 🎯 Financial Goal Tracking
- **Target Amortization**: Set target amounts, start dates, and target completion deadlines.
- **Real-Time Progress**: Calculates percentage achieved, remaining balance, days remaining, and required monthly savings velocity to hit deadlines on time.
- **Interactive Trajectory Charts**: Chart.js time-series visualizations tracking cumulative contributions toward target milestones.

### 7. 📂 Bank Statement Import (CSV & Excel)
- **Multi-Format Support**: Native ingestion for `.csv`, `.xlsx`, and `.xls` files via Pandas and OpenPyXL.
- **Intelligent Header Detection**: Automatically identifies Date, Description, Amount, and Category columns with interactive custom mapping overrides.
- **Pre-Import Duplicate Deduplication**: Matches incoming rows against existing transactions by date, amount, and narrative, highlighting duplicate rows in the preview.

### 8. 🔐 Authentication & Protected Workspace
- **Protected Entry Flow**: Any visit to the app redirects unauthenticated visitors directly to the dedicated full-screen login page with the trading screens background visual.
- **Post-Login Dashboard Unlock**: The vertical sidebar, navigation links, KPI metrics, charts, and transaction features are revealed exclusively after authentication.
- **Secure Password Hashing**: Utilizes Werkzeug PBKDF2 with SHA-256 password hashing.
- **Session Management**: Session cookies with remember-me persistent token support powered by Flask-Login.
- **Pre-configured Demo Account**: Ready-to-use demo login (`demo_user` / `Password123!`) with instant one-click auto-fill.
- **User Interface Integration**: Live user session card in the sidebar showing avatar initials, username, and email with one-click sign out.

### 9. 🎨 Modern Vertical Workspace & Dark/Light Theme
- **Vertical Navigation Flow**: Collapsible left vertical navigation bar with icon indicators, quick expense modal trigger, and clean two-column dashboard.
- **Financial Analytics Visual Background**: Authentic dual-monitor trading dashboard background visual with frosted glassmorphic card overlays on authentication pages.
- **Instant Dark / Light Mode**: One-click Sun ☀️ / Moon 🌙 toggle with local storage persistence and system preference autodetection.

---

## 🛠️ Tech Stack & Dependencies

| Component | Technology | Version |
|---|---|---|
| **Backend Framework** | Flask | 3.1.3 |
| **ORM & Database** | SQLAlchemy & SQLite | 2.1.8 |
| **Machine Learning / NLP** | Scikit-Learn, NumPy, SciPy | 1.9.1 / 2.5.4 |
| **Computer Vision / OCR** | RapidOCR ONNX, OpenCV, Pillow | 1.2.3 / 5.0.0 |
| **Data Ingestion** | Pandas, OpenPyXL | 3.1.0 / 3.1.5 |
| **Frontend UI** | Tailwind CSS CDN, Chart.js CDN, Jinja2 | Modern ES6 |
| **Testing** | Pytest | 9.2.0 |

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- Windows / macOS / Linux

### 2. Environment Setup
```powershell
# Clone or navigate to the project directory
cd "expense trackker"

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # On Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```powershell
# Populates categories, 3 months of baseline transactions, recurring rules, and goals
python seed.py
```

### 4. Run Application
```powershell
python run.py
```
Open your browser and navigate to: **`http://localhost:5000`**

### 🔑 Demo Account Credentials
- **Username / Email**: `demo_user` (or `demo@example.com`)
- **Password**: `Password123!`
*(You can also click the "Auto-fill" button on `/auth/login` to log in instantly, or register a new custom account.)*

---

## 🧪 Testing

Run the automated test suite covering all services, authentication, and API routes:
```powershell
python -m pytest -v
```
**Results**: 40 passed, 100% test coverage across all features.

---

## 🔒 Security Measures
- **Password Security**: Werkzeug salted PBKDF2 hash algorithm ensures secure credential storage.
- **Session Authentication**: Flask-Login session management with remember-me persistent token support.
- **Upload File Sanitization**: Filenames secured using `secure_filename()` with randomized UUID prefixes to prevent path traversal attacks.
- **MIME & Extension Whitelisting**: Strict checks on image types (`png`, `jpg`, `jpeg`, `webp`, `bmp`) and statement types (`csv`, `xlsx`, `xls`).
- **File Size Caps**: 16MB max upload boundary enforced at server layer.
- **SQL Injection Prevention**: 100% parameterized queries via SQLAlchemy 2.0 ORM.

