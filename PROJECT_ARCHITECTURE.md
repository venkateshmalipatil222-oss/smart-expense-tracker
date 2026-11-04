# Project Architecture & Engineering Specification

## 1. High-Level Architectural Pattern

The Smart Expense Tracker follows a **Clean Modular Service-Oriented Architecture** built on Flask, SQLAlchemy, and Scikit-Learn. Business logic is strictly isolated from presentation and HTTP route handlers.

```
+-------------------------------------------------------------------------------+
|                            Presentation Layer                                 |
|  - Jinja2 Templates styled with Tailwind CSS (Responsive Desktop & Mobile)     |
|  - Chart.js Visualizations (MoM trends, category doughnut, goal trajectories)  |
|  - Asynchronous Client Utilities (Live Categorization, Instant Anomaly Alert) |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                             Route Blueprints                                  |
|  - auth_bp:        User Login, Registration, Logout, Session State            |
|  - core_bp:        Dashboard, Ledger Table, Transaction CRUD, Live APIs       |
|  - insights_bp:    Financial MoM Trends, Forecast, PDF Statement Export       |
|  - receipts_bp:    Receipt Upload, Extraction Review, Confirmation Flow       |
|  - recurring_bp:   Recurring Rules Engine, Due Date Processing, Projections   |
|  - goals_bp:       Milestone Savings Goals, Contributions, Trajectories       |
|  - import_bp:      Bank Statement File Parsing, Column Mapper, Deduplication  |
|  - splits_bp:      Group Expense Sharing, Itemized Splits, Debt Settlements   |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                              Service Layer                                    |
|  - InsightService:           MoM analytics, 50/30/20 & micro-spend patterns   |
|  - ForecastService:          Time-Series polynomial velocity ML & 95% CI      |
|  - CopilotService:           Natural language query engine & affordability    |
|  - ReportService:            ReportLab executive PDF statement & tax export   |
|  - CurrencyService:          Multi-currency FX engine & localized formatting  |
|  - SplitService:             Itemized multi-category & group sharing (IOU)    |
|  - ReceiptScannerService:    OpenCV image preprocessing, RapidOCR parsing     |
|  - CategorizerService:       Hybrid Keyword + TF-IDF Naive Bayes NLP          |
|  - AnomalyDetectionService:  IQR/Z-Score mathematical outlier + Isolation     |
|                              Forest pattern evaluation (non-alarmist)         |
|  - RecurringService:         Schedule advancement & duplicate prevention      |
|  - GoalService:              Amortized target pacing & contribution logs      |
|  - ImportService:            CSV/Excel reader, header detector, deduplication |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                            Persistence Layer                                  |
|  - SQLAlchemy 2.0 ORM with relational SQLite (pluggable PostgreSQL support)   |
|  - Models: User, Category, Transaction, TransactionSplit, ExpenseShare,       |
|            RecurringRule, FinancialGoal, GoalContribution, ReceiptScan,       |
|            ImportBatch                                                        |
+-------------------------------------------------------------------------------+
```

---

## 2. AI / ML Implementation Details

### A. Automatic Categorization Pipeline
- **Tier 1 (Rule-Based Matcher)**:
  - Exact & regex token boundary matching over a high-precision keyword dictionary mapping merchants (e.g., Starbucks, Uber, Shell, Netflix, CVS, Amazon) directly to categories.
  - Confidence: `0.95 - 1.0`. Provenance: `RULE_BASED`.
- **Tier 2 (NLP & Machine Learning Classifier)**:
  - Scikit-Learn `Pipeline` composed of:
    1. `TfidfVectorizer(ngram_range=(1, 2), lowercase=True, max_features=1000)`
    2. `MultinomialNB(alpha=0.1)`
  - Pre-trained on a diverse corpus of financial transaction strings and augmented at runtime with historical user transactions.
  - Generates top predicted category with probability confidence and secondary alternative categories.
  - User retains full autonomy to accept or override the suggestion.

### B. Anomaly Detection Engine
- **Category-Specific Statistical Baseline**:
  - Calculates $Q_1$, Median ($Q_2$), $Q_3$, and Interquartile Range ($\text{IQR} = Q_3 - Q_1$), alongside Mean ($\mu$) and Standard Deviation ($\sigma$) for transactions in the target category.
  - Flagged when:
    $$\text{Amount} > Q_3 + 2.5 \times \text{IQR} \quad \text{or} \quad \frac{\text{Amount} - \mu}{\sigma} \ge 2.5$$
- **Isolation Forest Model**:
  - Employs `sklearn.ensemble.IsolationForest(contamination=0.04, random_state=42)` across multidimensional feature space `[Amount, DayOfWeek]`.
- **Ethical Explainability**:
  - Strict compliance rule: **Never flag transactions as "Fraud"**.
  - All alerts are labeled `"Unusual Expense"` with contextual, plain-English justifications (e.g. *"This purchase of $890.00 is 16.5x higher than your typical Shopping median of $54.00"*).

### C. Receipt OCR Pipeline
- **Computer Vision Preprocessing (`cv2`)**:
  - Automatic aspect scaling (bounded to max 2000px)
  - Grayscale conversion
  - Non-local means denoising (`fastNlMeansDenoising`) to optimize OCR text boundary detection
- **Text Recognition & Entity Parsing**:
  - `RapidOCR`: Lightweight ONNX Runtime inference extracting text lines and bounding boxes.
  - Post-processing regex extractors:
    - Merchant: Top-5 lines filtering out noise tokens (RECEIPT, INVOICE, TEL, STORE).
    - Date: Multi-format matcher (`YYYY-MM-DD`, `MM/DD/YYYY`, `DD/MM/YYYY`, `Mon DD YYYY`).
    - Total Amount: Keyword-anchored matcher (`TOTAL`, `BALANCE DUE`, `AMOUNT DUE`, `NET`, currency symbols).
  - Confidence scoring calculated from entity presence (0.0 to 1.0).

---

## 3. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET/POST`| `/auth/login` | User login screen & authentication handler |
| `GET/POST`| `/auth/register` | User account registration with validation |
| `GET` | `/auth/logout` | Session invalidation and logout |
| `GET` | `/` | Main financial dashboard with overview cards, charts, and alerts |
| `GET` | `/transactions` | Filterable, searchable transaction ledger |
| `GET/POST`| `/transactions/new` | Transaction creation form with live auto-categorization |
| `GET/POST`| `/transactions/<id>/edit` | Edit transaction details |
| `POST` | `/transactions/<id>/delete` | Delete transaction |
| `GET` | `/api/categorize` | JSON API: Live category suggestion for description string |
| `GET` | `/api/check-anomaly` | JSON API: Live anomaly evaluation preview for candidate amount |
| `GET` | `/api/currency/convert` | JSON API: Live multi-currency conversion and exchange rates |
| `POST`| `/api/copilot/chat` | JSON API: AI Financial Copilot conversational query engine |
| `GET` | `/insights/` | Deep financial insights, forecasts & recommendations view |
| `GET` | `/insights/api/chart-data` | JSON API: 6-month historical trend & category breakdown |
| `GET` | `/insights/api/forecast` | JSON API: 30-day time-series cash flow velocity forecast & 95% CI |
| `GET` | `/insights/export/pdf` | Publication-ready executive financial statement PDF export |
| `GET` | `/splits/` | Group expense sharing dashboard & itemized splits |
| `POST`| `/splits/settle/<id>` | Mark a shared expense IOU as settled |
| `POST`| `/splits/unsettle/<id>` | Revert a settled expense IOU back to pending |
| `POST`| `/splits/api/transaction/<id>/splits` | Save multi-category itemized splits for a transaction |
| `POST`| `/splits/api/transaction/<id>/shares` | Save group expense shares and IOUs for a transaction |
| `GET` | `/splits/api/summary` | JSON API: Aggregated debt summary per person and totals |
| `GET` | `/receipts/` | Scanned receipts history & image upload dropzone |
| `POST` | `/receipts/upload` | Process image upload with OCR and entity extraction |
| `GET/POST`| `/receipts/<id>/confirm`| Review extracted receipt data and confirm into transaction |
| `POST` | `/receipts/<id>/discard`| Discard receipt scan |
| `GET` | `/recurring/` | Recurring transaction rules & upcoming payments timeline |
| `GET/POST`| `/recurring/new` | Create recurring schedule (daily, weekly, monthly, yearly) |
| `POST` | `/recurring/<id>/toggle`| Pause or resume recurring schedule |
| `POST` | `/recurring/process-due` | Trigger idempotent execution of due recurring transactions |
| `GET` | `/goals/` | Savings goals portfolio summary & progress bars |
| `GET/POST`| `/goals/new` | Create financial savings goal |
| `GET` | `/goals/<id>` | Goal milestone trajectory chart & contribution log |
| `POST` | `/goals/<id>/contribute`| Add contribution deposit to savings goal |
| `GET` | `/import/` | Bank statement upload screen & past import history |
| `POST` | `/import/upload` | Parse uploaded CSV/Excel file and launch column mapping |
| `POST` | `/import/preview` | Preview mapped rows with duplicate record detection |
| `POST` | `/import/commit` | Bulk commit transactions with duplicate skipping |

---

## 4. Testing Results

Independent test suite executed via `pytest`:

```
tests/test_anomaly_detection.py::test_anomaly_detection_with_outlier PASSED
tests/test_auth.py::test_user_password_hashing PASSED
tests/test_auth.py::test_login_page_renders PASSED
tests/test_auth.py::test_login_successful_with_username PASSED
tests/test_auth.py::test_login_successful_with_email PASSED
tests/test_auth.py::test_login_invalid_password PASSED
tests/test_auth.py::test_login_nonexistent_user PASSED
tests/test_auth.py::test_login_missing_fields PASSED
tests/test_auth.py::test_register_page_renders PASSED
tests/test_auth.py::test_register_successful PASSED
tests/test_auth.py::test_register_password_mismatch PASSED
tests/test_auth.py::test_register_duplicate_username PASSED
tests/test_auth.py::test_register_duplicate_email PASSED
tests/test_auth.py::test_logout PASSED
tests/test_auth.py::test_unauthenticated_user_redirected_to_login PASSED
tests/test_categorizer.py::test_rule_based_keyword_matching PASSED
tests/test_categorizer.py::test_ml_nlp_classification PASSED
tests/test_categorizer.py::test_fallback_on_unrecognized_text PASSED
tests/test_goals.py::test_goal_creation_and_progress PASSED
tests/test_goals.py::test_goals_overview_analytics PASSED
tests/test_import.py::test_auto_detect_column_mapping PASSED
tests/test_import.py::test_import_with_duplicate_detection PASSED
tests/test_insights.py::test_spending_overview PASSED
tests/test_insights.py::test_month_over_month_comparison PASSED
tests/test_insights.py::test_personalized_recommendations_provenance PASSED
tests/test_receipt_scanner.py::test_parse_entities_standard_receipt PASSED
tests/test_receipt_scanner.py::test_parse_entities_alternate_date_format PASSED
tests/test_receipt_scanner.py::test_parse_entities_incomplete_ocr_fallback PASSED
tests/test_recurring.py::test_due_date_advancement PASSED
tests/test_recurring.py::test_recurring_execution_and_duplicate_prevention PASSED
tests/test_recurring.py::test_upcoming_payments_projection PASSED
tests/test_routes.py::test_dashboard_route PASSED
tests/test_routes.py::test_transactions_route PASSED
tests/test_routes.py::test_add_transaction_route PASSED
tests/test_routes.py::test_api_categorize_route PASSED
tests/test_insights.py::test_insights_routes PASSED
tests/test_receipts.py::test_receipts_route PASSED
tests/test_recurring.py::test_recurring_routes PASSED
tests/test_goals.py::test_goals_routes PASSED
tests/test_import.py::test_import_route PASSED
tests/test_currency.py::test_currency_service_supported_currencies PASSED
tests/test_currency.py::test_currency_conversion_rates PASSED
tests/test_currency.py::test_currency_formatting PASSED
tests/test_currency.py::test_add_transaction_with_foreign_currency PASSED
tests/test_currency.py::test_api_currency_convert_endpoint PASSED
tests/test_forecast.py::test_forecast_calculation_and_confidence_bounds PASSED
tests/test_forecast.py::test_api_forecast_endpoint PASSED
tests/test_copilot.py::test_copilot_affordability_safe PASSED
tests/test_copilot.py::test_copilot_affordability_insufficient_funds PASSED
tests/test_copilot.py::test_copilot_recurring_audit PASSED
tests/test_copilot.py::test_copilot_category_spending PASSED
tests/test_copilot.py::test_copilot_api_endpoint PASSED
tests/test_reports.py::test_report_service_pdf_generation_empty PASSED
tests/test_reports.py::test_report_service_with_transactions PASSED
tests/test_reports.py::test_export_pdf_route_month PASSED
tests/test_reports.py::test_export_pdf_route_ytd PASSED
tests/test_reports.py::test_export_pdf_route_custom PASSED
tests/test_splits.py::test_itemized_splits_success PASSED
tests/test_splits.py::test_itemized_splits_sum_mismatch PASSED
tests/test_splits.py::test_expense_shares_creation_and_exceed_limit PASSED
tests/test_splits.py::test_settle_and_unsettle_share PASSED
tests/test_splits.py::test_splits_routes_and_api PASSED

======================= 62 passed in 23.05s =======================
```

---

## 5. Architectural Accomplishments
1. **Multi-Currency Normalization**: Fully integrated FX Engine (`CurrencyService`) converting and tracking original currencies against base USD ledger metrics.
2. **Predictive Cash Flow Simulation**: Polynomial velocity ML regression combining historical run rates with scheduled obligations and 95% confidence intervals.
3. **AI Financial Copilot**: In-app conversational drawer with intent parsing and transparent, data-backed affordability and spending audits.
4. **Vectorized Statement PDF Generation**: Publication-quality executive PDF generation engine (`ReportService`) with KPI summaries, category distributions, and tax preparation highlights.
5. **Itemized Splits & Group Expense Sharing**: Comprehensive splitting engine (`SplitService`) supporting both line-item category distributions and group debt IOU management.
6. **Pluggable Database Dialects**: Uses SQLite for local simplicity and zero-configuration portability; easily switched to PostgreSQL by setting the `DATABASE_URL` environment variable.

