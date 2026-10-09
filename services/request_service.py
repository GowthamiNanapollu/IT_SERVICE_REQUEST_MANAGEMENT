from datetime import datetime, timedelta, timezone

from database import get_db_connection


SLA_HOURS = {
    "Critical": 4,
    "High": 8,
    "Medium": 24,
    "Low": 48,
}


def create_service_request(
    requester_id,
    category_id,
    subject,
    description,
    priority,
    created_by_user_id
):
    subject = subject.strip()
    description = description.strip()

    if not subject or not description:
        raise ValueError("Subject and description are required.")

    if priority not in SLA_HOURS:
        raise ValueError("Invalid priority.")

    if len(subject) > 200:
        raise ValueError("Subject cannot exceed 200 characters.")

    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    sla_due_at = created_at + timedelta(hours=SLA_HOURS[priority])

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:

            
            cursor.execute(
                    """
                    INSERT INTO service_requests (
                    requester_id,
                    created_by_user_id,
                    category_id,
                    subject,
                    description,
                    priority,
                    status,
                    created_at,
                    sla_due_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
            (
                requester_id,
                created_by_user_id,
                category_id,
                subject,
                description,
                priority,
                "New",
                created_at,
                sla_due_at,
            ),
            )


            request_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO request_updates (
                    request_id,
                    employee_author_id,
                    update_type,
                    message
                )
                VALUES (%s, %s, 'Created', %s)
                """,
                (
                    request_id,
                    requester_id,
                    "Service request created.",
                ),
            )

        connection.commit()
        return request_id

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
