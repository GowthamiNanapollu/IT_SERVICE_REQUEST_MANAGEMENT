
CREATE TABLE IF NOT EXISTS employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS it_staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS sla_config (
    priority VARCHAR(20) PRIMARY KEY,
    sla_hours INT NOT NULL,
    CHECK (sla_hours > 0)
);

CREATE TABLE IF NOT EXISTS service_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    requester_id INT NOT NULL,
    category_id INT NOT NULL,
    assigned_to INT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
    status VARCHAR(20) NOT NULL DEFAULT 'New',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    sla_due_at DATETIME NOT NULL,
    resolution_details TEXT NULL,
    resolved_by_staff_id INT NULL,
    resolved_at DATETIME NULL,
    closed_at DATETIME NULL,

    CONSTRAINT fk_request_employee
        FOREIGN KEY (requester_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_request_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id),

    CONSTRAINT fk_request_assigned_staff
        FOREIGN KEY (assigned_to)
        REFERENCES it_staff(staff_id),

    CONSTRAINT fk_request_resolved_staff
        FOREIGN KEY (resolved_by_staff_id)
        REFERENCES it_staff(staff_id),

    CONSTRAINT fk_request_priority
        FOREIGN KEY (priority)
        REFERENCES sla_config(priority),

    CONSTRAINT chk_request_status
        CHECK (status IN (
            'New', 'Assigned', 'In Progress',
            'Resolved', 'Closed', 'On Hold'
        )),

    INDEX idx_request_status (status),
    INDEX idx_request_priority (priority),
    INDEX idx_request_assigned_to (assigned_to),
    INDEX idx_request_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS request_updates (
    update_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    employee_author_id INT NULL,
    staff_author_id INT NULL,
    update_type VARCHAR(30) NOT NULL DEFAULT 'Comment',
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_update_request
        FOREIGN KEY (request_id)
        REFERENCES service_requests(request_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_update_employee
        FOREIGN KEY (employee_author_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_update_staff
        FOREIGN KEY (staff_author_id)
        REFERENCES it_staff(staff_id),

    INDEX idx_update_request_time (request_id, created_at)
);

INSERT IGNORE INTO sla_config (priority, sla_hours)
VALUES
    ('Critical', 4),
    ('High', 8),
    ('Medium', 24),
    ('Low', 48);

INSERT IGNORE INTO categories (name)
VALUES
    ('Hardware'),
    ('Software'),
    ('Network'),
    ('Access / Permission'),
    ('Email'),
    ('Other');

INSERT IGNORE INTO employees (name, email)
VALUES ('Demo Employee', 'employee@example.com');

INSERT IGNORE INTO it_staff (name, email)
VALUES
    ('IT Support One', 'support1@example.com'),
    ('IT Support Two', 'support2@example.com');



CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('employee', 'it_staff') NOT NULL,
    employee_id INT NULL,
    staff_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_users_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id),

    CONSTRAINT fk_users_staff
        FOREIGN KEY (staff_id)
        REFERENCES it_staff(staff_id),

    CONSTRAINT chk_users_role_reference CHECK (
        (role = 'employee'
            AND employee_id IS NOT NULL
            AND staff_id IS NULL)
        OR
        (role = 'it_staff'
            AND staff_id IS NOT NULL
            AND employee_id IS NULL)
    )
);

