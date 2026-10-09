from flask import Blueprint, jsonify, current_app, session
from database import get_db_connection

report_bp = Blueprint("reports", __name__)


@report_bp.route("/api/reports/summary", methods=["GET"])
def report_summary():
    # Require an authenticated manager or IT staff member.
    if "user_id" not in session:
        return jsonify({"error": "Please log in"}), 401

    role = session.get("role")

    if role == "it_staff":
        staff_id = session.get("staff_id")
        if staff_id is None:
            return jsonify({
                "error": "IT staff account is not configured"
            }), 403
        where_clause = "WHERE assigned_to = %s"
        query_params = (staff_id,)

    elif role == "manager":
        # Managers see organization-wide reports.
        where_clause = ""
        query_params = ()

    else:
        return jsonify({
            "error": "Only managers and IT staff can view reports"
        }), 403

    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    COUNT(*) AS total_requests,
                    COALESCE(SUM(status NOT IN ('Resolved', 'Closed')), 0)
                        AS open_requests,
                    COALESCE(SUM(status = 'Resolved'), 0)
                        AS resolved_requests,
                    COALESCE(SUM(status = 'Closed'), 0)
                        AS closed_requests,
                    COALESCE(SUM(
                        sla_due_at < UTC_TIMESTAMP()
                        AND status NOT IN ('Resolved', 'Closed')
                    ), 0) AS overdue_requests
                FROM service_requests
                {where_clause}
                """,
                query_params,
            )

            row = cursor.fetchone()

            summary = {
                "total_requests": row[0] or 0,
                "open_requests": row[1] or 0,
                "resolved_requests": row[2] or 0,
                "closed_requests": row[3] or 0,
                "overdue_requests": row[4] or 0,
            }

            cursor.execute(
                f"""
                SELECT status, COUNT(*)
                FROM service_requests
                {where_clause}
                GROUP BY status
                ORDER BY status
                """,
                query_params,
            )
            status_counts = {
                status: count for status, count in cursor.fetchall()
            }

            cursor.execute(
                f"""
                SELECT priority, COUNT(*)
                FROM service_requests
                {where_clause}
                GROUP BY priority
                ORDER BY FIELD(
                    priority, 'Critical', 'High', 'Medium', 'Low'
                )
                """,
                query_params,
            )
            priority_counts = {
                priority: count
                for priority, count in cursor.fetchall()
            }

        return jsonify({
            "summary": summary,
            "by_status": status_counts,
            "by_priority": priority_counts,
        }), 200

    except Exception:
        current_app.logger.exception("Report generation failed")
        return jsonify({"error": "Unable to generate reports"}), 500

    finally:
        if connection:
            connection.close()
