
from flask import Flask, jsonify, render_template
from database import get_db_connection
from routes.request_routes import request_bp
from routes.report_routes import report_bp
from flask import session, redirect, url_for, request, flash
from werkzeug.security import check_password_hash
from config import Config
from functools import wraps



app = Flask(__name__)

app.config.from_object(Config)
# Register each blueprint exactly once
app.register_blueprint(request_bp)
app.register_blueprint(report_bp)




def login_required(role=None):
    def decorator(view_function):

        @wraps(view_function)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                return "Access denied", 403

            return view_function(*args, **kwargs)

        return wrapped

    return decorator




@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/requests")
@login_required()
def requests_page():
    if session.get("role") not in ("it_staff", "manager"):
        return "Access denied", 403

    return render_template("requests.html")

@app.route("/dashboard")
@login_required("it_staff")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/manager")
@login_required("manager")
def manager_page():
    return render_template("manager.html")

@app.route("/employee")
@login_required("employee")
def employee_page():
    return render_template("employee.html")

@app.route("/raise-request")
@login_required("employee")
def raise_request_page():
    return render_template("raise_request.html")


@app.route("/api/health")
def health_check():
    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            database_name = cursor.fetchone()[0]

        return jsonify({
            "status": "success",
            "message": "Flask is connected to MariaDB",
            "database": database_name
        })

    except Exception:
        app.logger.exception("Database health check failed")
        return jsonify({
            "status": "error",
            "message": "Database connection failed"
        }), 500

    finally:
        if connection:
            connection.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = None

        try:
            connection = get_db_connection()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id, email, password_hash, role,
                           employee_id, staff_id
                    FROM users
                    WHERE email = %s
                    """,
                    (email,),
                )
                user = cursor.fetchone()

            if user and check_password_hash(user[2], password):
                session.clear()
                session["user_id"] = user[0]
                session["email"] = user[1]
                session["role"] = user[3]
                session["employee_id"] = user[4]
                session["staff_id"] = user[5]

                if user[3] == "employee":
                    return redirect(url_for("employee_page"))

                elif user[3] == "it_staff":
                    return redirect(url_for("dashboard_page"))

                elif user[3] == "manager":
                    return redirect(url_for("manager_page"))

                else:
                    session.clear()
                    flash("Invalid user role.", "danger")
                    return redirect(url_for("login"))

        except Exception:
            app.logger.exception("Login failed")
            flash("Unable to log in. Please try again.", "danger")

        finally:
            if connection:
                connection.close()

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
