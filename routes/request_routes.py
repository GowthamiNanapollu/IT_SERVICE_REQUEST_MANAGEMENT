from flask import Blueprint, jsonify, request, current_app, session

from database import get_db_connection
from services.request_service import create_service_request

request_bp = Blueprint("requests", __name__)


ALLOWED_PRIORITIES = {"Critical", "High", "Medium", "Low"}
ALLOWED_STATUSES = {"New", "Assigned", "In Progress", "On Hold", "Resolved", "Closed"}
ALLOWED_TRANSITIONS = {
    "New": {"Assigned", "On Hold"},
    "Assigned": {"In Progress", "On Hold"},
    "In Progress": {"Resolved", "On Hold"},
    "On Hold": {"Assigned", "In Progress"},
    "Resolved": {"Closed"},
    "Closed": set(),
}


def _logged_in():
    return "user_id" in session


def _request_access(cursor, request_id):
    """Return (ticket row, error response). Ticket row has requester and assignee IDs."""
    cursor.execute(
        """
        SELECT request_id, requester_id, created_by_user_id, assigned_to, status
        FROM service_requests
        WHERE request_id = %s
        """,
        (request_id,),
    )
    ticket = cursor.fetchone()
    if not ticket:
        return None, (jsonify({"error": "Request not found"}), 404)

    role = session.get("role")
    if role == "manager":
        return ticket, None
    if role == "employee" and ticket[2] == session.get("user_id"):
        return ticket, None
    if role == "it_staff" and ticket[3] == session.get("staff_id"):
        return ticket, None

    return None, (jsonify({"error": "Access denied"}), 403)


@request_bp.route("/api/requests", methods=["POST"])
def create_request():
    if not _logged_in():
        return jsonify({"error": "Please log in"}), 401
    if session.get("role") != "employee":
        return jsonify({"error": "Only employees can raise service requests"}), 403

    employee_id = session.get("employee_id")
    if employee_id is None:
        return jsonify({"error": "Employee account is not configured"}), 403

    data = request.get_json(silent=True) or {}
    required_fields = ["category_id", "subject", "description", "priority"]
    missing_fields = [field for field in required_fields if data.get(field) is None or data.get(field) == ""]
    if missing_fields:
        return jsonify({"error": "Missing required fields", "fields": missing_fields}), 400

    if data.get("priority") not in ALLOWED_PRIORITIES:
        return jsonify({"error": "Invalid priority"}), 400

    subject = data.get("subject")
    description = data.get("description")
    if not isinstance(subject, str) or not subject.strip():
        return jsonify({"error": "Subject cannot be empty"}), 400
    if not isinstance(description, str) or not description.strip():
        return jsonify({"error": "Description cannot be empty"}), 400

    try:
        category_id = int(data["category_id"])
        if category_id < 1:
            raise ValueError
        request_id = create_service_request(
            requester_id=int(employee_id),
            category_id=category_id,
            subject=subject.strip(),
            description=description.strip(),
            priority=data["priority"],
            created_by_user_id=int(session["user_id"]),
        )
        return jsonify({"message": "Service request created successfully", "request_id": request_id}), 201
    except ValueError as error:
        return jsonify({"error": str(error) or "Invalid category_id"}), 400
    except Exception:
        current_app.logger.exception("Unable to create service request")
        return jsonify({"error": "Unable to create service request"}), 500


@request_bp.route("/api/requests", methods=["GET"])
def get_requests():
    if not _logged_in():
        return jsonify({"message": "Please log in"}), 401

    role = session.get("role")
    if role not in {"employee", "it_staff", "manager"}:
        return jsonify({"message": "Access denied"}), 403

    priority = request.args.get("priority", "").strip()
    status = request.args.get("status", "").strip()
    overdue = request.args.get("overdue", "").strip()
    employee_id = request.args.get("employee_id", "").strip()

    if priority and priority not in ALLOWED_PRIORITIES:
        return jsonify({"message": "Invalid priority"}), 400
    if status and status not in ALLOWED_STATUSES:
        return jsonify({"message": "Invalid status"}), 400
    if overdue and overdue not in {"0", "1"}:
        return jsonify({"message": "Invalid overdue filter"}), 400
    if employee_id and role != "manager":
        return jsonify({"message": "Only managers can filter by employee ID"}), 403
    if employee_id:
        try:
            employee_id = int(employee_id)
            if employee_id < 1:
                raise ValueError
        except ValueError:
            return jsonify({"message": "Invalid employee ID"}), 400

    connection = None
    try:
        connection = get_db_connection()
        query = """
            SELECT
                sr.request_id, sr.subject, sr.description, sr.priority,
                sr.status, sr.created_at, sr.updated_at, sr.sla_due_at,
                sr.resolution_details, sr.assigned_to, sr.requester_id,
                c.name AS category, e.name AS requester, s.name AS assigned_staff
            FROM service_requests sr
            JOIN categories c ON sr.category_id = c.category_id
            JOIN employees e ON sr.requester_id = e.employee_id
            LEFT JOIN it_staff s ON sr.assigned_to = s.staff_id
        """
        conditions = []
        params = []

        if role == "employee":
            conditions.append("sr.created_by_user_id = %s")
            params.append(session["user_id"])
        elif role == "it_staff":
            # Staff can see only tickets assigned to their own staff profile.
            staff_id = session.get("staff_id")
            if staff_id is None:
                return jsonify({"message": "IT staff account is not configured"}), 403
            conditions.append("sr.assigned_to = %s")
            params.append(staff_id)
            if priority:
                conditions.append("sr.priority = %s")
                params.append(priority)
            if status:
                conditions.append("sr.status = %s")
                params.append(status)
            if overdue == "1":
                conditions.append("sr.sla_due_at < NOW() AND sr.status NOT IN ('Resolved', 'Closed')")
        else:  # manager
            if employee_id:
                conditions.append("sr.requester_id = %s")
                params.append(employee_id)
            if priority:
                conditions.append("sr.priority = %s")
                params.append(priority)
            if status:
                conditions.append("sr.status = %s")
                params.append(status)
            if overdue == "1":
                conditions.append("sr.sla_due_at < NOW() AND sr.status NOT IN ('Resolved', 'Closed')")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY sr.created_at DESC"

        with connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]

        results = []
        for row in rows:
            item = dict(zip(columns, row))
            for key, value in item.items():
                if hasattr(value, "isoformat"):
                    item[key] = value.isoformat(sep=" ")
            results.append(item)
        return jsonify(results), 200
    except Exception:
        current_app.logger.exception("Failed to fetch requests")
        return jsonify({"message": "Unable to fetch requests"}), 500
    finally:
        if connection:
            connection.close()


@request_bp.route("/api/requests/<int:request_id>/assign", methods=["PUT"])
def assign_request(request_id):
    if not _logged_in():
        return jsonify({"error": "Please log in"}), 401
    if session.get("role") != "manager":
        return jsonify({"error": "Only managers can assign or reassign tickets"}), 403

    data = request.get_json(silent=True) or {}
    staff_id = data.get("staff_id")
    try:
        staff_id = int(staff_id)
        if staff_id < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "A valid staff_id is required"}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT staff_id FROM it_staff WHERE staff_id = %s AND is_available = TRUE", (staff_id,))
            if not cursor.fetchone():
                return jsonify({"error": "Available IT staff member not found"}), 404

            cursor.execute(
                "SELECT status, assigned_to FROM service_requests WHERE request_id = %s FOR UPDATE",
                (request_id,),
            )
            existing = cursor.fetchone()
            if not existing:
                return jsonify({"error": "Request not found"}), 404
            old_status, old_assignee = existing
            if old_status in {"Resolved", "Closed"}:
                return jsonify({"error": "Resolved or closed requests cannot be reassigned"}), 409

            cursor.execute(
                """
                UPDATE service_requests
                SET assigned_to = %s,
                    status = CASE WHEN status = 'New' THEN 'Assigned' ELSE status END
                WHERE request_id = %s
                """,
                (staff_id, request_id),
            )
            assignment_message = f"Manager assigned request to IT staff ID {staff_id}."
            if old_assignee is not None and old_assignee != staff_id:
                assignment_message = f"Manager reassigned request from IT staff ID {old_assignee} to IT staff ID {staff_id}."
            cursor.execute(
                """
                INSERT INTO request_updates (request_id, update_type, message)
                VALUES (%s, 'Assignment', %s)
                """,
                (request_id, assignment_message),
            )
        connection.commit()
        return jsonify({"message": "Request assigned successfully", "request_id": request_id, "staff_id": staff_id}), 200
    except Exception:
        if connection:
            connection.rollback()
        current_app.logger.exception("Request assignment failed")
        return jsonify({"error": "Unable to assign request"}), 500
    finally:
        if connection:
            connection.close()


@request_bp.route("/api/requests/<int:request_id>/status", methods=["PUT"])
def update_request_status(request_id):
    if not _logged_in():
        return jsonify({"error": "Please log in"}), 401
    if session.get("role") != "it_staff":
        return jsonify({"error": "Only assigned IT staff can update ticket status"}), 403

    staff_id = session.get("staff_id")
    if staff_id is None:
        return jsonify({"error": "IT staff account is not configured"}), 403

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    resolution_details = (data.get("resolution_details") or "").strip()
    if new_status not in ALLOWED_STATUSES:
        return jsonify({"error": "Invalid status"}), 400
    if new_status == "Resolved" and not resolution_details:
        return jsonify({"error": "Resolution details are required"}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, assigned_to FROM service_requests WHERE request_id = %s FOR UPDATE",
                (request_id,),
            )
            existing = cursor.fetchone()
            if not existing:
                return jsonify({"error": "Request not found"}), 404

            old_status, assigned_to = existing
            if assigned_to != staff_id:
                return jsonify({"error": "You can update only tickets assigned to you"}), 403
            if new_status not in ALLOWED_TRANSITIONS[old_status]:
                return jsonify({"error": f"Cannot transition from {old_status} to {new_status}"}), 409
            if new_status in {"Resolved", "Closed"} and assigned_to is None:
                return jsonify({"error": "Request must be assigned before resolving or closing"}), 409

            cursor.execute(
                """
                UPDATE service_requests
                SET status = %s,
                    resolution_details = CASE WHEN %s = 'Resolved' THEN %s ELSE resolution_details END,
                    resolved_by_staff_id = CASE WHEN %s = 'Resolved' THEN assigned_to ELSE resolved_by_staff_id END,
                    resolved_at = CASE WHEN %s = 'Resolved' THEN NOW() ELSE resolved_at END,
                    closed_at = CASE WHEN %s = 'Closed' THEN NOW() ELSE closed_at END
                WHERE request_id = %s
                """,
                (new_status, new_status, resolution_details, new_status, new_status, new_status, request_id),
            )
            cursor.execute(
                """
                INSERT INTO request_updates (request_id, staff_author_id, update_type, message)
                VALUES (%s, %s, 'Status Change', %s)
                """,
                (request_id, staff_id, f"Status changed from {old_status} to {new_status}."),
            )
        connection.commit()
        return jsonify({"message": "Status updated successfully", "request_id": request_id, "old_status": old_status, "new_status": new_status}), 200
    except Exception:
        if connection:
            connection.rollback()
        current_app.logger.exception("Status update failed")
        return jsonify({"error": "Unable to update request status"}), 500
    finally:
        if connection:
            connection.close()


@request_bp.route("/api/requests/<int:request_id>/history", methods=["GET"])
def get_request_history(request_id):
    if not _logged_in():
        return jsonify({"error": "Please log in"}), 401
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            _, error_response = _request_access(cursor, request_id)
            if error_response:
                return error_response
            cursor.execute(
                """
                SELECT update_id, update_type, message, employee_author_id,
                       staff_author_id, created_at
                FROM request_updates
                WHERE request_id = %s
                ORDER BY created_at ASC, update_id ASC
                """,
                (request_id,),
            )
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
        history = []
        for row in rows:
            item = dict(zip(columns, row))
            for key, value in item.items():
                if hasattr(value, "isoformat"):
                    item[key] = value.isoformat(sep=" ")
            history.append(item)
        return jsonify(history), 200
    except Exception:
        current_app.logger.exception("Failed to retrieve request history")
        return jsonify({"error": "Unable to retrieve history"}), 500
    finally:
        if connection:
            connection.close()


@request_bp.route("/api/requests/<int:request_id>/comments", methods=["POST"])
def add_request_comment(request_id):
    if not _logged_in():
        return jsonify({"error": "Please log in"}), 401
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Comment cannot be empty"}), 400
    message = message.strip()
    if len(message) > 5000:
        return jsonify({"error": "Comment is too long"}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            _, error_response = _request_access(cursor, request_id)
            if error_response:
                return error_response
            cursor.execute(
                "INSERT INTO request_updates (request_id, update_type, message) VALUES (%s, 'Comment', %s)",
                (request_id, message),
            )
        connection.commit()
        return jsonify({"message": "Comment added successfully", "request_id": request_id}), 201
    except Exception:
        if connection:
            connection.rollback()
        current_app.logger.exception("Failed to add comment")
        return jsonify({"error": "Unable to add comment"}), 500
    finally:
        if connection:
            connection.close()


@request_bp.route("/api/categories", methods=["GET"])
def get_categories():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT category_id, name FROM categories WHERE is_active = TRUE ORDER BY name"
            )
            rows = cursor.fetchall()
        return jsonify([{"category_id": row[0], "name": row[1]} for row in rows]), 200
    except Exception:
        current_app.logger.exception("Failed to load categories")
        return jsonify({"error": "Unable to load categories"}), 500
    finally:
        if connection:
            connection.close()


@request_bp.route("/api/staff", methods=["GET"])
def list_it_staff():
    if not _logged_in():
        return jsonify({"message": "Please log in"}), 401
    if session.get("role") != "manager":
        return jsonify({"message": "Only managers can view the assignable IT staff list"}), 403

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT staff_id, name FROM it_staff WHERE is_available = TRUE ORDER BY name"
            )
            rows = cursor.fetchall()
        return jsonify([{"staff_id": row[0], "name": row[1]} for row in rows]), 200
    except Exception:
        current_app.logger.exception("Unable to load IT staff")
        return jsonify({"message": "Unable to load IT staff"}), 500
    finally:
        if connection:
            connection.close()
