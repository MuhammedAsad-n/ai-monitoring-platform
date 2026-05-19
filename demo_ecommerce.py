"""
============================================================
REAL WORLD DEMO 2 — ShopAI: E-Commerce AI Monitoring
============================================================

SCENARIO:
  You work at an e-commerce company called "ShopAI".
  They have 3 AI models:

    1. recommendation_engine  — "customers also bought" suggestions
    2. price_optimizer        — dynamic pricing every 5 minutes
    3. demand_forecaster      — predicts stock needed for next 7 days

  This script simulates Black Friday — the highest traffic
  day of the year. Models are pushed to their limits.

HOW TO RUN:
  python demo_ecommerce.py
"""

import requests
import random
import time

BASE_URL = "http://localhost:8000/api"


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


def check_server():
    try:
        r = requests.get(f"{BASE_URL}/health/ping", timeout=3)
        return r.status_code == 200
    except Exception:
        print(f"\n{C.RED}❌ Start the server first: python main.py{C.RESET}\n")
        return False


def register_ecommerce_models():
    header("Registering ShopAI e-commerce models")
    models = [
        {
            "model_id": "shopai_recommender_v3",
            "name": "ShopAI Recommendation Engine",
            "version": "3.2.0",
            "description": "Collaborative filtering + deep learning. Powers 'You may also like' section. Drives 35% of revenue.",
        },
        {
            "model_id": "shopai_price_optimizer",
            "name": "ShopAI Dynamic Price Optimizer",
            "version": "2.0.1",
            "description": "Adjusts prices every 5 minutes based on demand, competition, inventory. Trained on 3 years of sales data.",
        },
        {
            "model_id": "shopai_demand_forecaster",
            "name": "ShopAI Demand Forecaster",
            "version": "1.5.0",
            "description": "Predicts 7-day demand for 50,000 SKUs. Prevents stockouts and overstock. Uses LSTM neural network.",
        },
    ]
    for m in models:
        requests.post(f"{BASE_URL}/models/register", json=m)
        print(f"  {C.GREEN}✅ {m['name']} registered{C.RESET}")
        print(f"     {m['description']}")
        time.sleep(0.1)


def simulate_black_friday_traffic():
    header("BLACK FRIDAY — 12am Midnight Rush")
    print(f"  {C.CYAN}200,000 customers online simultaneously. Models under maximum load.{C.RESET}\n")

    products = [
        ("iPhone 15 Pro",        999,  "Electronics"),
        ("Samsung 4K TV 65\"",   799,  "Electronics"),
        ("Nike Air Max",          180,  "Footwear"),
        ("Dyson Vacuum",          450,  "Home Appliances"),
        ("AirPods Pro",           249,  "Electronics"),
        ("Instant Pot",            89,  "Kitchen"),
        ("LEGO Star Wars Set",    120,  "Toys"),
        ("MacBook Air M2",       1099,  "Electronics"),
        ("Kindle Paperwhite",      140,  "Electronics"),
        ("Coffee Maker Deluxe",    95,  "Kitchen"),
    ]

    print(f"  {C.CYAN}[Recommendation Engine] Generating product suggestions...{C.RESET}")
    for i in range(15):
        product, price, category = random.choice(products)
        recommended = [p[0] for p in random.sample(products, 3)]
        latency = random.uniform(28, 65)
        confidence = random.uniform(0.87, 0.97)

        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "shopai_recommender_v3",
            "request_id": f"REC{random.randint(1000000,9999999)}",
            "input_data":  {"viewed_product": product, "category": category, "user_segment": "high_value"},
            "output_data": {"recommendations": recommended, "click_probability": round(confidence, 3)},
            "confidence": confidence,
            "latency_ms": latency,
            "status": "success"
        })
        print(f"     User viewed: {product:<25} → recommended: {recommended[0]}")
        time.sleep(0.04)

    print()
    print(f"  {C.CYAN}[Price Optimizer] Adjusting prices dynamically...{C.RESET}")
    for product, base_price, category in products:
        demand_factor = random.uniform(1.05, 1.35)  # high demand on Black Friday
        new_price = round(base_price * demand_factor, 2)
        confidence = random.uniform(0.82, 0.95)
        latency = random.uniform(18, 42)

        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "shopai_price_optimizer",
            "request_id": f"PRICE{random.randint(100000,999999)}",
            "input_data":  {"product": product, "base_price": base_price, "demand_index": demand_factor},
            "output_data": {"optimized_price": new_price, "expected_margin": 0.23},
            "confidence": confidence,
            "latency_ms": latency,
            "status": "success"
        })
        change = new_price - base_price
        print(f"     {product:<28} ${base_price:>7.2f} → ${new_price:>7.2f}  (+${change:.2f})")
        time.sleep(0.04)

    print(f"\n  {C.GREEN}✅ Black Friday peak handled — all models healthy{C.RESET}")


def simulate_recommender_crash():
    header("⚠️  RECOMMENDATION ENGINE CRASHES (3am)")
    print(f"  {C.RED}Database connection pool exhausted under load. Model failing.{C.RESET}\n")

    crash_sequence = [
        (45,   0.93, "success"),  (120,  0.88, "success"),
        (450,  0.75, "success"),  (980,  0.61, "success"),
        (2100, 0.42, "error"),    (3400, 0.31, "error"),
        (5000, 0.22, "error"),    (5000, 0.18, "error"),
        (5000, 0.15, "error"),    (5000, 0.12, "error"),
    ]

    for latency, confidence, status in crash_sequence:
        color = C.GREEN if status == "success" else C.RED
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "shopai_recommender_v3",
            "latency_ms": latency,
            "confidence": confidence,
            "status": status,
            "error_message": "db_pool_exhausted" if status == "error" else None
        })
        bar = "█" * min(int(latency / 200), 25)
        print(f"     Latency {latency:>5}ms  {color}{status:<8}{C.RESET}  {bar}")
        time.sleep(0.07)

    print(f"\n  {C.RED}🚨 CRITICAL: Recommendation engine down{C.RESET}")
    print(f"  {C.YELLOW}⚠️  Revenue impact: ~$50,000/minute in lost recommendations{C.RESET}")
    print(f"  {C.CYAN}ℹ️  Platform auto-triggered rollback evaluation{C.RESET}")
    print(f"  {C.CYAN}ℹ️  Check: http://localhost:8000/api/alerts/active{C.RESET}")


def simulate_demand_forecast_drift():
    header("📉 DEMAND FORECASTER DRIFT (Post Black Friday)")
    print(f"  {C.CYAN}Black Friday created unusual buying patterns model was never trained on.{C.RESET}")
    print(f"  {C.CYAN}Demand forecasts are now unreliable — could cause stockouts or overstock.{C.RESET}\n")

    print(f"  Normal week (pre-Black Friday) — high confidence forecasts:")
    for i in range(6):
        conf = random.uniform(0.91, 0.96)
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "shopai_demand_forecaster",
            "latency_ms": random.uniform(85, 115),
            "confidence": conf,
            "status": "success",
            "input_data": {"period": "normal_week"}
        })
        print(f"     Forecast {i+1}: confidence {conf:.1%}  {C.GREEN}✅ reliable{C.RESET}")
        time.sleep(0.04)

    print(f"\n  Post-Black-Friday — confidence collapsing:")
    for i in range(8):
        conf = random.uniform(0.52, 0.67)
        requests.post(f"{BASE_URL}/inference/log", json={
            "model_id": "shopai_demand_forecaster",
            "latency_ms": random.uniform(95, 130),
            "confidence": conf,
            "status": "success",
            "input_data": {"period": "post_black_friday"}
        })
        print(f"     Forecast {i+1}: confidence {conf:.1%}  {C.YELLOW}⚠️  unreliable{C.RESET}")
        time.sleep(0.04)

    print(f"\n  {C.RED}🚨 Drift score: 0.38 — critical level{C.RESET}")
    print(f"  {C.YELLOW}⚠️  Purchasing team alerted — do not rely on forecasts this week{C.RESET}")
    print(f"  {C.CYAN}ℹ️  Action: retrain model on Black Friday + post-BF data{C.RESET}")
    print(f"  {C.CYAN}ℹ️  Check: http://localhost:8000/api/drift/shopai_demand_forecaster/report{C.RESET}")


def show_business_impact():
    header("BUSINESS IMPACT SUMMARY")

    print(f"  {C.BOLD}What the monitoring platform caught today:{C.RESET}\n")

    impacts = [
        ("Recommendation engine crash",    "Caught in 45 seconds",    "Prevented ~$2.5M revenue loss"),
        ("Demand forecaster drift",         "Caught before next run",  "Prevented $800K in overstock"),
        ("Price optimizer confidence drop", "Caught in real time",     "Prevented margin erosion"),
        ("Black Friday load spike",         "Handled automatically",   "No customer impact"),
    ]

    for event, detection, impact in impacts:
        print(f"  {C.CYAN}●{C.RESET} {event}")
        print(f"      Detection : {C.GREEN}{detection}{C.RESET}")
        print(f"      Impact    : {C.YELLOW}{impact}{C.RESET}")
        print()

    print(f"  {C.BOLD}Without this monitoring platform:{C.RESET}")
    print(f"     ❌ Crash discovered by angry customers complaining")
    print(f"     ❌ Drift discovered when stockouts cause revenue loss")
    print(f"     ❌ Engineers manually checking dashboards at 3am")
    print()
    print(f"  {C.BOLD}With this monitoring platform:{C.RESET}")
    print(f"     ✅ Automatic detection in seconds")
    print(f"     ✅ Slack/email alert fires immediately")
    print(f"     ✅ Auto-rollback prevents full outage")
    print(f"     ✅ Engineers sleep — platform watches")
    print()
    print(f"  {C.BOLD}Explore all results:{C.RESET}")
    print(f"     📊 http://localhost:8501         ← live dashboard")
    print(f"     🔌 http://localhost:8000/docs    ← all 30+ API endpoints")
    print(f"     🚨 http://localhost:8000/api/alerts/active")
    print(f"     📉 http://localhost:8000/api/drift/shopai_recommender_v3/report")
    print()


def main():
    print(f"\n{C.BOLD}{C.CYAN}  ShopAI — E-Commerce AI Monitoring Demo{C.RESET}\n")

    if not check_server():
        return

    steps = [
        register_ecommerce_models,
        simulate_black_friday_traffic,
        simulate_recommender_crash,
        simulate_demand_forecast_drift,
        show_business_impact,
    ]

    for i, fn in enumerate(steps, 1):
        fn()
        if i < len(steps):
            print(f"\n  {C.CYAN}Press ENTER to continue...{C.RESET}", end="")
            input()

    print(f"\n{C.BOLD}{C.GREEN}  Demo complete!{C.RESET}\n")


if __name__ == "__main__":
    main()
