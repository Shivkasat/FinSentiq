"""
app.py — Sentix Intelligence Platform
---------------------------------------
Application factory and entry point.

Changes in this version:
  - Maintenance thread is Redis-aware (skips in-memory sweeps when Redis handles expiry)
  - Proactive cache pre-warm scheduler: refreshes news cache before it expires,
    so users never hit a cold cache miss (old behaviour: cold miss = 15-45s wait)
  - Hard fail on missing FLASK_SECRET_KEY in production (FLASK_ENV=production)
  - Background threads registered only once (gunicorn multi-worker safe via env flag)
"""

import os
import time
import logging
import threading
from datetime import datetime

from flask import Flask, render_template, session, redirect, url_for, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import json

# ---------------------------------------------------------------------------
# Structured logging — configure before importing service modules
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sentix.app")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    app = Flask(__name__)

    # ── Security configuration ────────────────────────────────────────
    secret_key = os.environ.get("FLASK_SECRET_KEY")
    flask_env  = os.environ.get("FLASK_ENV", "development")

    if not secret_key:
        if flask_env == "production":
            raise RuntimeError(
                "FLASK_SECRET_KEY must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        else:
            secret_key = "sentix-dev-key-NOT-for-production"
            logger.warning(
                "⚠️  Using insecure dev secret key. "
                "Set FLASK_SECRET_KEY before deploying to production."
            )

    app.secret_key = secret_key
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"]   = flask_env == "production"  # HTTPS only in prod
    app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24h session expiry

    # ── Directory setup ───────────────────────────────────────────────
    os.makedirs("user_data", exist_ok=True)
    os.makedirs("user_data/watchlists", exist_ok=True)

    # ── Blueprint registration ─────────────────────────────────────────
    from news_routes import news_bp
    app.register_blueprint(news_bp)

    # ── Context processor (inject auth state into all templates) ──────
    @app.context_processor
    def inject_user():
        return {
            "logged_in":    "user_id" in session,
            "current_user": session.get("username"),
        }

    # ── Static pages ─────────────────────────────────────────────────
    @app.route("/")
    def landing():
        return render_template("landing.html")

    @app.route("/products")
    def products():
        return render_template("products.html")

    # ── Auth routes ──────────────────────────────────────────────────
    _register_auth_routes(app)

    # ── Watchlist routes (auth-gated) ─────────────────────────────────
    _register_watchlist_routes(app)

    # ── Health check ──────────────────────────────────────────────────
    @app.route("/health")
    def health():
        from cache_service import cache
        from duplicate_service import dedup
        return jsonify({
            "status":    "healthy",
            "timestamp": datetime.now().isoformat(),
            "cache":     cache.get_stats(),
            "dedup":     dedup.get_stats(),
        })

    # ── Error handlers ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        try:
            return render_template("error.html", message="Page not found"), 404
        except Exception:
            return "<h2>404 — Page not found</h2>", 404

    @app.errorhandler(500)
    def server_error(e):
        try:
            return render_template("error.html", message="Internal server error"), 500
        except Exception:
            return "<h2>500 — Internal server error</h2>", 500

    logger.info("✅ Sentix Flask app created")
    return app


# ---------------------------------------------------------------------------
# Auth routes (self-contained, minimal)
# ---------------------------------------------------------------------------

def _load_users() -> dict:
    try:
        with open("user_data/users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_users(users: dict) -> None:
    with open("user_data/users.json", "w") as f:
        json.dump(users, f, indent=2)


def _register_auth_routes(app: Flask) -> None:

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            users = _load_users()

            if username in users and check_password_hash(users[username]["password"], password):
                session["user_id"]  = users[username]["id"]
                session["username"] = username
                session.permanent   = True
                flash("Login successful!", "success")
                next_page = request.args.get("next")
                return redirect(next_page or url_for("news.news_analyzer"))
            else:
                flash("Invalid credentials", "error")

        return render_template("login2.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            email    = request.form.get("email", "").strip()
            users    = _load_users()

            if username in users:
                flash("Username already exists", "error")
            elif len(password) < 8:
                flash("Password must be at least 8 characters", "error")
            else:
                user_id = str(uuid.uuid4())
                users[username] = {
                    "id":         user_id,
                    "password":   generate_password_hash(password),
                    "email":      email,
                    "created_at": datetime.now().isoformat(),
                }
                _save_users(users)
                from watchlist_service import _create_empty_watchlist as _wl_init
                _wl_init(user_id)
                flash("Account created! Please log in.", "success")
                return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out", "info")
        return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Watchlist routes (auth-gated, decoupled from news logic)
# ---------------------------------------------------------------------------

def _login_required(f):
    """Decorator for auth-gated routes."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def _register_watchlist_routes(app: Flask) -> None:

    @app.route("/watchlist")
    @_login_required
    def watchlist_page():
        from watchlist_service import get_watchlist_news_digest, get_stocks
        from news_routes import _get_sector_articles

        user_id  = session["user_id"]
        username = session.get("username")

        try:
            sector_articles = _get_sector_articles()
            digest = get_watchlist_news_digest(user_id, sector_articles)

            return render_template(
                "watchlist.html",
                stocks           = digest["stocks"],
                sector_tabs      = digest["sector_tabs"],
                per_stock        = digest["per_stock"],
                total_positive   = digest["total_positive"],
                total_negative   = digest["total_negative"],
                alert_count      = digest["alert_count"],
                username         = username,
                last_updated     = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as exc:
            logger.exception(f"Watchlist page error: {exc}")
            return render_template(
                "watchlist.html",
                stocks           = [],
                sector_tabs      = {},
                per_stock        = {},
                total_positive   = 0,
                total_negative   = 0,
                alert_count      = 0,
                error            = str(exc),
            )

    @app.route("/api/search_stocks")
    @_login_required
    def api_search_stocks():
        query = request.args.get("q", "").strip()
        if len(query) < 2:
            return jsonify({"results": []})

        try:
            import pandas as pd
            df = pd.read_csv("company.csv")
            df.columns = df.columns.str.strip()
            q = query.lower()

            exact    = df[df["SYMBOL"].str.lower() == q]
            starts   = df[df["SYMBOL"].str.lower().str.startswith(q) & ~(df["SYMBOL"].str.lower() == q)]
            contains = df[df["COMPANY_NAME"].str.lower().str.contains(q, na=False) & ~df["SYMBOL"].str.lower().str.startswith(q)]

            combined = pd.concat([exact, starts, contains]).drop_duplicates(subset=["SYMBOL"])
            results  = combined.head(15).apply(lambda r: {
                "symbol":   str(r.get("SYMBOL", "")).strip(),
                "name":     str(r.get("COMPANY_NAME", "")).strip(),
                "sector":   str(r.get("SECTOR", "")).strip(),
                "industry": str(r.get("INDUSTRY", "")).strip() if "INDUSTRY" in r else "",
            }, axis=1).tolist()

            return jsonify({"results": results})

        except Exception as exc:
            logger.exception(f"Stock search error: {exc}")
            return jsonify({"results": [], "error": str(exc)})

    @app.route("/api/add_to_watchlist", methods=["POST"])
    @_login_required
    def api_add_to_watchlist():
        from watchlist_service import add_stock
        data   = request.get_json(silent=True) or {}
        symbol = data.get("symbol", "").strip().upper()
        name   = data.get("name", "")
        sector = data.get("sector", "")

        if not symbol:
            return jsonify({"success": False, "error": "Symbol is required"}), 400

        success, message = add_stock(session["user_id"], symbol, name, sector)
        if success:
            from watchlist_service import get_watchlist_count
            total = get_watchlist_count(session["user_id"])
            return jsonify({"success": True, "message": message, "total_stocks": total})
        else:
            return jsonify({"success": False, "error": message}), 400

    @app.route("/api/remove_from_watchlist", methods=["POST"])
    @_login_required
    def api_remove_from_watchlist():
        from watchlist_service import remove_stock
        data   = request.get_json(silent=True) or {}
        symbol = data.get("symbol", "").strip().upper()

        if not symbol:
            return jsonify({"success": False, "error": "Symbol is required"}), 400

        success, message = remove_stock(session["user_id"], symbol)
        if success:
            from watchlist_service import get_watchlist_count
            total = get_watchlist_count(session["user_id"])
            return jsonify({"success": True, "message": message, "total_stocks": total})
        else:
            return jsonify({"success": False, "error": message}), 404

    @app.route("/api/get_watchlist")
    @_login_required
    def api_get_watchlist():
        from watchlist_service import get_watchlist_news_digest
        from news_routes import _get_sector_articles

        user_id = session["user_id"]
        try:
            sector_articles = _get_sector_articles()
            digest = get_watchlist_news_digest(user_id, sector_articles)
            return jsonify({
                "success":        True,
                "stocks":         digest["stocks"],
                "total_stocks":   len(digest["stocks"]),
                "total_positive": digest["total_positive"],
                "total_negative": digest["total_negative"],
                "alert_count":    digest["alert_count"],
                "username":       session.get("username"),
                "last_updated":   datetime.now().isoformat(),
            })
        except Exception as exc:
            logger.exception(f"get_watchlist API error: {exc}")
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/watchlist_news")
    @_login_required
    def api_watchlist_news():
        from watchlist_service import get_watchlist_news_digest
        from news_routes import _get_sector_articles

        user_id = session["user_id"]
        try:
            sector_articles = _get_sector_articles()
            digest = get_watchlist_news_digest(user_id, sector_articles)
            return jsonify({
                "success":        True,
                "sector_tabs":    digest["sector_tabs"],
                "per_stock":      digest["per_stock"],
                "total_positive": digest["total_positive"],
                "total_negative": digest["total_negative"],
                "alert_count":    digest["alert_count"],
                "last_updated":   datetime.now().isoformat(),
            })
        except Exception as exc:
            logger.exception(f"watchlist_news API error: {exc}")
            return jsonify({"success": False, "error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Background maintenance thread
# Redis-aware: skips manual expiry sweeps when Redis handles TTL natively.
# ---------------------------------------------------------------------------

def _start_maintenance_thread(interval_seconds: int = 300) -> None:
    """
    Periodic housekeeping every `interval_seconds` (default 5 min).

    For Redis backends:
      - Skips manual purge (Redis evicts expired keys automatically)
      - Still logs stats for observability
    For memory backends:
      - Sweeps expired cache entries
      - Sweeps expired dedup hashes
    """
    def _run():
        while True:
            time.sleep(interval_seconds)
            try:
                from cache_service import cache
                from duplicate_service import dedup

                # Only purge manually for memory backends
                cache_evicted = cache.purge_expired()   # no-op for Redis
                dedup_evicted = dedup.purge_expired()   # no-op for Redis
                cache_stats   = cache.get_stats()
                dedup_stats   = dedup.get_stats()

                logger.info(
                    f"🧹 Maintenance [{cache_stats.get('backend','?')}]: "
                    f"cache_evicted={cache_evicted} active_keys={cache_stats.get('active_keys','?')} | "
                    f"dedup_evicted={dedup_evicted} active_hashes={dedup_stats.get('active_hashes','?')} "
                    f"dup_rate={dedup_stats.get('duplicate_rate_pct','?')}%"
                )
            except Exception as exc:
                logger.error(f"Maintenance error: {exc}")

    t = threading.Thread(target=_run, daemon=True, name="sentix-maintenance")
    t.start()
    logger.info(f"🔧 Maintenance thread started (interval={interval_seconds}s)")


# ---------------------------------------------------------------------------
# Proactive cache pre-warm scheduler
#
# Problem with old reactive behaviour:
#   Cache expires after 10 min → next request triggers full 15-45s RSS fetch
#   User sees a 15-45s spinner every 10 minutes.
#
# Solution:
#   Refresh the cache in the background at 80% of TTL (8 min for 10 min TTL).
#   By the time the key expires, a fresh version is already loaded.
#   Users always hit a warm cache.
# ---------------------------------------------------------------------------

_CACHE_TTL      = 600    # Must match news_routes._CACHE_TTL
_PREWARM_FACTOR = 0.80   # Refresh at 80% of TTL = every 480s (8 min)
def _start_prewarm_scheduler() -> None:
    interval = int(_CACHE_TTL * _PREWARM_FACTOR)

    def _run():
        time.sleep(interval)

        while True:
            try:
                logger.info("🔥 Pre-warm refresh starting...")

                from rss_service import fetch_all_feeds
                from cache_service import cache

                fresh_data = fetch_all_feeds()

                cache.set("sector_articles_new", fresh_data or {}, ttl=_CACHE_TTL, namespace="news")
                cache.set("sector_articles_old", fresh_data or {}, ttl=_CACHE_TTL, namespace="news")
                cache.invalidate("sector_articles_new", namespace="news")
                cache.invalidate("gainers_losers", namespace="news")

                total_articles = sum(len(v) for v in (fresh_data or {}).values())
                logger.info(f"🔥 Pre-warm complete: {total_articles} articles")

            except Exception as exc:
                logger.error(f"Pre-warm error: {exc}")

            time.sleep(interval)

    t = threading.Thread(target=_run, daemon=True, name="sentix-prewarm")
    t.start()
    logger.info(f"🔥 Pre-warm scheduler started (every {interval}s)")

# ---------------------------------------------------------------------------
# Guard against double-starting background threads in Gunicorn multi-worker
# Gunicorn forks workers AFTER the master process runs create_app().
# We use an env flag set only in the master process to start threads once.
# ---------------------------------------------------------------------------

def _start_background_threads() -> None:
    """Start maintenance + pre-warm threads exactly once."""
    if os.environ.get("_SENTIX_THREADS_STARTED"):
        return
    os.environ["_SENTIX_THREADS_STARTED"] = "1"

    _start_maintenance_thread(interval_seconds=300)
    _start_prewarm_scheduler()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🇮🇳  SENTIX — Indian Stock Market Intelligence Platform")
    print("=" * 70)
    print("  📊  Dashboard  : http://localhost:5000")
    print("  📰  Analyzer   : http://localhost:5000/news-analyzer")
    print("  🔍  Health     : http://localhost:5000/health")
    print("  🔧  Feed Health: http://localhost:5000/api/feed-health")
    print("=" * 70 + "\n")

    # Log cache backend on startup
    from cache_service import cache
    from duplicate_service import dedup
    logger.info(
        f"Cache backend  : {'Redis ✅' if cache.is_redis else 'Memory ⚠️  (set REDIS_URL for production)'}"
    )
    logger.info(
        f"Dedup backend  : {'Redis ✅' if dedup.is_redis else 'Memory ⚠️  (set REDIS_URL for production)'}"
    )

    application = create_app()
    _start_background_threads()

    application.run(
        debug=False,
        use_reloader=False,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        threaded=True,
    )
