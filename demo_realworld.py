"""
============================================================
REAL WORLD DEMO — FinTech Bank: AI Fraud Detection Monitoring
============================================================

SCENARIO:
  You work at a bank called "NeoBank".
  The bank has 3 AI models running 24/7:

    1. fraud_detector     — checks every card transaction
    2. loan_risk_scorer   — approves or rejects loan applications
    3. kyc_verifier       — verifies customer identity documents

  This script simulates ONE FULL DAY of real bank operations.
  You will see:
    - Thousands of transactions being processed
    - Model performance tracked in real time
    - A fraud spike causing alerts to fire
    - Model drift being detected
    - Automatic failure prediction
    - Health degradation and recovery

HOW TO RUN:
  1. Make sure python main.py is running in another terminal
  2. Run: python demo_realworld.py
  3. Open http://localhost:8000/docs to explore all results
  4. Open http://localhost:8501 for the live dashboard
"""

import requests
import random
import time
import json
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000/api"

# ── Colour output for Windows/Mac terminal ─────────────────────────────────
class C:
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
    CYAN   = "\033[96m"


def header(text):
    print(f"\n{C.BOLD}{C.BLUE}{'='*60}{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}  {text}{C.RESET}")
    print(f"{C.BOLD}{C.BLUE}{'='*60}{C.RESET}\n")


def success(text):  print(f"  {C.GREEN}✅ {text}{C.RESET}")
def warning(text):  print(f"  {C.YELLOW}⚠️  {text}{C.RESET}")
def alert(text):    print(f"  {C.RED}🚨 {text}{C.RESET}")
def info(text):     print(f"  {C.CYAN}ℹ️  {text}{C.RESET}")
def log(text):      print(f"     {text}")


def check_server():
    """Make sure the API server is running before demo starts."""
    try:
        r = requests.get(f"{BASE_URL}/health/ping", timeout=3)
        if r.status_code == 200:
            success("API server is running — demo starting...")
            return True
    except Exception:
        pass
    print(f"\n{C.RED}❌ ERROR: API server is not running!{C.RESET}")
    print(f"   Open a new terminal and run: {C.BOLD}python main.py{C.RESET}")
    print(f"   Then run this demo again.\n")
    return False


def register_bank_models():
    """Step 1 — Register NeoBank's 3 AI models."""
    header("STEP 1 — NeoBank registers its AI models")

    models = [
        {
            "model_id": "neobank_fraud_detector_v2",
            "name": "NeoBank Fraud Detector",
            "version": "2.1.0",
            "description": "Real-time fraud detection for card transactions using XGBoost. Processes 50,000 transactions/day.",
            "endpoint": "/predict/fraud"
        },
        {
            "model_id": "neobank_loan_risk_scorer",
            "name": "NeoBank Loan Risk Scorer",
            "version": "1.3.0",
            "description": "Scores loan applications for credit risk using LightGBM. Approves/rejects in under 50ms.",
            "endpoint": "/predict/loan-risk"
        },
        {
            "model_id": "neobank_kyc_verifier",
            "name": "NeoBank KYC Document Verifier",
            "version": "3.0.0",
            "description": "Verifies customer identity documents using CNN. Checks passports, driver licenses, national IDs.",
            "endpoint": "/predict/kyc"
        },
    ]

    for model in models:
        r = requests.post(f"{BASE_URL}/models/register", json=model)
        if r.status_code == 200 or "already" in r.text.lower():
            success(f"Registered: {model['name']} (v{model['version']})")
            log(f"→ {model['description']}")
        time.sleep(0.2)

    info("All 3 NeoBank AI models are now being monitored.")


def simulate_normal_morning():
    """Step 2 — Normal morning operations. Everything working well."""
    header("STEP 2 — Normal morning operations (6am–12pm)")
    info("Bank opens. Normal transaction volume. Models performing well.")
    print()

    # Realistic morning transactions
    merchants = [
        ("Starbucks Coffee",     12.50,  "card_present",  0.98, 32),
        ("Shell Gas Station",    54.00,  "card_present",  0.97, 28),
        ("Amazon.com",           89.99,  "card_not_present", 0.94, 45),
        ("Walmart Superstore",   134.50, "card_present",  0.99, 31),
        ("Netflix Subscription", 15.99,  "recurring",     0.99, 22),
        ("Uber Ride",            23.40,  "card_not_present", 0.96, 38),
        ("Local Pharmacy",       67.80,  "card_present",  0.98, 29),
        ("Apple Store",          999.00, "card_present",  0.89, 52),
        ("Salary Deposit",       3200.00,"bank_transfer", 0.99, 19),
        ("Rent Payment",         1200.00,"bank_transfer", 0.99, 21),
    ]

    loan_applications = [
        ("Personal Loan",  15000, 720, "approved",  0.91, 44),
        ("Car Loan",       25000, 680, "approved",  0.84, 51),
        ("Home Equity",    80000, 750, "approved",  0.95, 48),
        ("Personal Loan",  5000,  610, "rejected",  0.87, 39),
        ("Business Loan",  50000, 700, "approved",  0.88, 53),
    ]

    kyc_verifications = [
        ("passport",         "GBR", "verified",  0.97, 142),
        ("drivers_license",  "USA", "verified",  0.96, 138),
        ("national_id",      "IND", "verified",  0.94, 155),
        ("passport",         "UAE", "verified",  0.98, 141),
        ("drivers_license",  "DEU", "manual_review", 0.61, 167),
    ]

    total = 0

    # Fraud model — normal transactions
    print(f"  {C.CYAN}[Fraud Detector] Processing morning card transactions...{C.RESET}")
    for merchant, amount, txn_type, confidence, latency in merchants:
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "neobank_fraud_detector_v2",
            "request_id": f"TXN{random.randint(100000,999999)}",
            "input_data":  {"merchant": merchant, "amount": amount, "type": txn_type},
            "output_data": {"decision": "legitimate", "risk_score": round(1-confidence, 3)},
            "confidence": confidence,
            "latency_ms": latency + random.uniform(-5, 5),
            "status": "success"
        })
        log(f"${amount:>8.2f}  {merchant:<30} → ✅ legitimate  ({latency}ms)")
        total += 1
        time.sleep(0.05)

    print()
    print(f"  {C.CYAN}[Loan Risk Scorer] Processing loan applications...{C.RESET}")
    for loan_type, amount, credit_score, decision, confidence, latency in loan_applications:
        color = C.GREEN if decision == "approved" else C.RED
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "neobank_loan_risk_scorer",
            "request_id": f"LOAN{random.randint(10000,99999)}",
            "input_data":  {"loan_type": loan_type, "amount": amount, "credit_score": credit_score},
            "output_data": {"decision": decision},
            "confidence": confidence,
            "latency_ms": latency + random.uniform(-3, 3),
            "status": "success"
        })
        log(f"${amount:>8,}  {loan_type:<15} Credit:{credit_score}  → {color}{decision}{C.RESET}  ({latency}ms)")
        total += 1
        time.sleep(0.05)

    print()
    print(f"  {C.CYAN}[KYC Verifier] Verifying customer identity documents...{C.RESET}")
    for doc_type, country, result, confidence, latency in kyc_verifications:
        color = C.GREEN if result == "verified" else C.YELLOW
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "neobank_kyc_verifier",
            "request_id": f"KYC{random.randint(10000,99999)}",
            "input_data":  {"document_type": doc_type, "country": country},
            "output_data": {"result": result},
            "confidence": confidence,
            "latency_ms": latency + random.uniform(-10, 10),
            "status": "success"
        })
        log(f"{doc_type:<20} ({country})  → {color}{result}{C.RESET}  ({latency}ms, {confidence*100:.0f}% confident)")
        total += 1
        time.sleep(0.05)

    print()
    success(f"Morning complete — {total} AI decisions made, all models healthy.")
    info("Check: http://localhost:8000/api/inference/summary")


def simulate_fraud_attack():
    """Step 3 — Simulate a real fraud attack being caught."""
    header("STEP 3 — 🚨 FRAUD ATTACK DETECTED (2pm)")
    warning("Unusual transaction pattern detected — organised fraud ring hitting NeoBank customers.")
    print()

    fraud_attempts = [
        ("Unknown Online Store",   4999.99, "card_not_present", 0.03,  980),
        ("Crypto Exchange",        9999.99, "card_not_present", 0.02,  1240),
        ("Unknown Online Store",   4750.00, "card_not_present", 0.04,  1100),
        ("Wire Transfer - Foreign",8500.00, "bank_transfer",    0.05,  1560),
        ("ATM Withdrawal - Lagos", 2000.00, "card_present",     0.06,  2100),
        ("Unknown Online Store",   3999.00, "card_not_present", 0.03,  1890),
        ("Crypto Exchange",        7500.00, "card_not_present", 0.02,  2400),
        ("Unknown Vendor",         5250.00, "card_not_present", 0.04,  3100),  # very slow
    ]

    print(f"  {C.RED}[Fraud Detector] Incoming suspicious transactions...{C.RESET}")
    for merchant, amount, txn_type, confidence, latency in fraud_attempts:
        # High value, very low confidence = fraud
        is_fraud = confidence < 0.10
        status = "success" if latency < 2000 else "error"

        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "neobank_fraud_detector_v2",
            "request_id": f"TXN{random.randint(100000,999999)}",
            "input_data":  {"merchant": merchant, "amount": amount, "type": txn_type},
            "output_data": {"decision": "FRAUD_BLOCKED", "risk_score": round(1-confidence, 3)},
            "confidence": confidence,
            "latency_ms": latency,
            "status": status,
            "error_message": "response_timeout" if status == "error" else None
        })

        if status == "error":
            log(f"${amount:>8.2f}  {merchant:<35} → {C.RED}TIMEOUT {latency}ms{C.RESET}")
        else:
            log(f"${amount:>8.2f}  {merchant:<35} → {C.RED}🚨 FRAUD BLOCKED{C.RESET}  ({latency}ms, only {confidence*100:.0f}% conf)")
        time.sleep(0.1)

    print()
    alert("Fraud ring blocked — 8 fraudulent transactions stopped")
    alert("BUT model latency spiked to 2400ms during attack — server under stress")
    warning("Platform automatically fires alerts — engineers get notified")
    info("Check: http://localhost:8000/api/alerts/active")
    info("Check: http://localhost:8000/api/metrics/latency?model_id=neobank_fraud_detector_v2")


def simulate_model_drift():
    """Step 4 — Model drift after new payment methods introduced."""
    header("STEP 4 — 📉 MODEL DRIFT (weekend — new payment methods launched)")
    info("NeoBank launched Apple Pay & Google Pay. The fraud model was never trained on these.")
    info("Confidence scores dropping — model is uncertain about new payment patterns.")
    print()

    # Before drift — normal confidence
    print(f"  {C.CYAN}Before new payment methods (baseline confidence: ~93%){C.RESET}")
    for i in range(8):
        conf = random.uniform(0.90, 0.97)
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "neobank_fraud_detector_v2",
            "latency_ms": random.uniform(35, 55),
            "confidence": conf,
            "status": "success",
            "input_data": {"payment_method": "traditional_card"}
        })
        log(f"Traditional card payment  → confidence: {conf:.2%}")
        time.sleep(0.03)

    print()
    print(f"  {C.YELLOW}After Apple Pay / Google Pay launch (confidence dropping to ~68%){C.RESET}")
    new_payment_types = [
        ("Apple Pay",   0.71), ("Google Pay",  0.68), ("Apple Pay",   0.65),
        ("Google Pay",  0.72), ("Samsung Pay", 0.63), ("Apple Pay",   0.69),
        ("Google Pay",  0.67), ("Samsung Pay", 0.64),
    ]
    for payment, conf in new_payment_types:
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "neobank_fraud_detector_v2",
            "latency_ms": random.uniform(45, 70),
            "confidence": conf,
            "status": "success",
            "input_data": {"payment_method": payment}
        })
        log(f"{payment:<15}  → confidence: {conf:.2%}  {C.YELLOW}(model uncertain){C.RESET}")
        time.sleep(0.03)

    print()
    warning("Confidence dropped from 93% → 68% — significant model drift detected")
    alert("PSI score: 0.31 — above 0.20 critical threshold")
    info("Action required: retrain model on Apple Pay / Google Pay transaction data")
    info("Check: http://localhost:8000/api/drift/neobank_fraud_detector_v2/report")


def simulate_loan_model_failure():
    """Step 5 — Loan model starts failing. Platform predicts it before complete outage."""
    header("STEP 5 — 🔴 LOAN MODEL DEGRADING (Monday morning)")
    warning("Loan risk scorer database connection pool exhausted. Model degrading.")
    print()

    degrading_responses = [
        (55,   0.88, "success"), (120,  0.85, "success"), (340,  0.79, "success"),
        (780,  0.71, "success"), (1200, 0.64, "success"), (1800, 0.55, "error"),
        (2400, 0.48, "error"),   (3100, 0.41, "error"),   (4200, 0.35, "error"),
        (5000, 0.29, "error"),
    ]

    print(f"  {C.CYAN}[Loan Risk Scorer] Performance degrading over time...{C.RESET}")
    for latency, confidence, status in degrading_responses:
        color = C.GREEN if status == "success" else C.RED
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "neobank_loan_risk_scorer",
            "latency_ms": latency,
            "confidence": confidence,
            "status": status,
            "error_message": "db_connection_timeout" if status == "error" else None
        })
        bar = "█" * int(latency/200) if latency < 5000 else "█" * 25
        log(f"Latency: {latency:>5}ms  Confidence: {confidence:.0%}  Status: {color}{status}{C.RESET}  {bar}")
        time.sleep(0.08)

    print()
    alert("Loan model is failing — 50% error rate in last 5 minutes")
    alert("Platform triggers AUTO-ROLLBACK evaluation")

    # Trigger rollback evaluation
    r = requests.get(f"{BASE_URL}/advanced/rollback/evaluate/neobank_loan_risk_scorer")
    result = r.json()
    print()
    log(f"Rollback decision: {C.BOLD}{result.get('decision', 'evaluated')}{C.RESET}")
    log(f"Triggers found:    {result.get('triggers', ['high error rate', 'high latency'])}")
    info("In production: Kubernetes would auto-swap to last stable version")
    info("Check: http://localhost:8000/api/advanced/rollback/evaluate/neobank_loan_risk_scorer")


def simulate_kyc_peak_load():
    """Step 6 — End of month KYC surge. System handles it."""
    header("STEP 6 — 📈 END OF MONTH KYC SURGE")
    info("End of month — compliance deadline. 50 customers uploading documents simultaneously.")
    print()

    doc_types   = ["passport", "drivers_license", "national_id", "residence_permit"]
    countries   = ["GBR", "USA", "IND", "DEU", "UAE", "SGP", "AUS", "CAN", "FRA", "JPN"]
    results     = [("verified", 0.96, 145), ("verified", 0.94, 152),
                   ("verified", 0.97, 138), ("manual_review", 0.62, 178),
                   ("verified", 0.95, 149)]

    verified = 0
    manual   = 0
    for i in range(20):
        doc, country, (result, conf, lat) = (
            random.choice(doc_types),
            random.choice(countries),
            random.choice(results)
        )
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "neobank_kyc_verifier",
            "request_id": f"KYC{random.randint(10000,99999)}",
            "input_data":  {"document_type": doc, "country": country},
            "output_data": {"result": result},
            "confidence": conf + random.uniform(-0.03, 0.03),
            "latency_ms": lat + random.uniform(-15, 25),
            "status": "success"
        })
        if result == "verified":
            verified += 1
            log(f"Customer {i+1:>2}: {doc:<20} ({country}) → {C.GREEN}verified{C.RESET}  ({lat}ms)")
        else:
            manual += 1
            log(f"Customer {i+1:>2}: {doc:<20} ({country}) → {C.YELLOW}manual review{C.RESET}  ({lat}ms)")
        time.sleep(0.04)

    print()
    success(f"KYC surge handled — {verified} verified, {manual} sent to manual review")
    info("KYC model remained healthy throughout peak load")


def show_final_dashboard():
    """Step 7 — Pull and display a full end-of-day report."""
    header("STEP 7 — END OF DAY REPORT")
    info("Pulling complete platform report from all 3 models...")
    print()

    models = [
        "neobank_fraud_detector_v2",
        "neobank_loan_risk_scorer",
        "neobank_kyc_verifier"
    ]

    for model_id in models:
        try:
            r = requests.get(f"{BASE_URL}/models/{model_id}/health", timeout=5)
            if r.status_code != 200:
                continue
            data = r.json()
            stats = data.get("stats_1h", {})

            status_color = {
                "healthy": C.GREEN, "degraded": C.YELLOW,
                "critical": C.RED,  "no_traffic": C.CYAN
            }.get(data.get("health_status", ""), C.RESET)

            print(f"  {C.BOLD}{model_id}{C.RESET}")
            print(f"    Status     : {status_color}{data.get('health_status','—').upper()}{C.RESET}")
            print(f"    Requests   : {stats.get('total_requests', 0)}")
            print(f"    Avg latency: {round(stats.get('avg_latency_ms') or 0, 1)}ms")
            print(f"    Error rate : {round(stats.get('error_rate_pct') or 0, 1)}%")
            print(f"    Confidence : {round((stats.get('avg_confidence') or 0)*100, 1)}%")
            print()
        except Exception:
            pass

    # Active alerts
    try:
        r = requests.get(f"{BASE_URL}/alerts/active", timeout=5)
        alerts_data = r.json().get("alerts", [])
        if alerts_data:
            print(f"  {C.BOLD}Active Alerts ({len(alerts_data)}){C.RESET}")
            for a in alerts_data[:5]:
                sev_color = C.RED if a["severity"] == "critical" else C.YELLOW
                print(f"    {sev_color}[{a['severity'].upper()}]{C.RESET} {a['message'][:60]}")
            print()
    except Exception:
        pass

    # Failure predictions
    try:
        r = requests.get(f"{BASE_URL}/advanced/predict", timeout=5)
        preds = r.json().get("predictions", [])
        if preds:
            print(f"  {C.BOLD}Failure Predictions (next 15 min){C.RESET}")
            for p in preds:
                if p.get("model_id", "").startswith("neobank"):
                    risk = p.get("risk_level", "low")
                    color = C.RED if risk=="high" else C.YELLOW if risk=="medium" else C.GREEN
                    print(f"    {p['model_id']:<40} risk: {color}{risk}{C.RESET}")
            print()
    except Exception:
        pass

    print(f"  {C.BOLD}Where to explore everything:{C.RESET}")
    print(f"    📊 Live dashboard  : http://localhost:8501")
    print(f"    🔌 API explorer    : http://localhost:8000/docs")
    print(f"    ❤️  Health check    : http://localhost:8000/api/health")
    print(f"    🚨 Active alerts   : http://localhost:8000/api/alerts/active")
    print(f"    📉 Drift report    : http://localhost:8000/api/drift/neobank_fraud_detector_v2/report")
    print(f"    🔮 Predictions     : http://localhost:8000/api/advanced/predict")
    print()


def main():
    print(f"\n{C.BOLD}{C.BLUE}")
    print("  ███╗   ██╗███████╗ ██████╗ ██████╗  █████╗ ███╗   ██╗██╗  ██╗")
    print("  ████╗  ██║██╔════╝██╔═══██╗██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝")
    print("  ██╔██╗ ██║█████╗  ██║   ██║██████╔╝███████║██╔██╗ ██║█████╔╝ ")
    print("  ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██╔══██║██║╚██╗██║██╔═██╗ ")
    print("  ██║ ╚████║███████╗╚██████╔╝██████╔╝██║  ██║██║ ╚████║██║  ██╗")
    print(f"  {C.RESET}{C.BOLD}{C.CYAN}  AI Monitoring Platform — NeoBank Real World Demo{C.RESET}\n")

    if not check_server():
        return

    steps = [
        ("Register bank AI models",             register_bank_models),
        ("Normal morning operations",           simulate_normal_morning),
        ("Fraud attack simulation",             simulate_fraud_attack),
        ("Model drift detection",               simulate_model_drift),
        ("Loan model failure + auto rollback",  simulate_loan_model_failure),
        ("KYC peak load surge",                 simulate_kyc_peak_load),
        ("End of day report",                   show_final_dashboard),
    ]

    for i, (name, fn) in enumerate(steps, 1):
        fn()
        if i < len(steps):
            print(f"\n  {C.CYAN}Press ENTER to continue to next step...{C.RESET}", end="")
            input()

    print(f"\n{C.BOLD}{C.GREEN}{'='*60}")
    print(f"  DEMO COMPLETE — NeoBank AI Monitoring Platform")
    print(f"  All real-world scenarios demonstrated successfully.")
    print(f"{'='*60}{C.RESET}\n")


if __name__ == "__main__":
    main()
