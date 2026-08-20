# Backup Registry

Flask + MySQL application for registering backup filenames for four branches.

## Install

    cd backup_registry
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Copy `.env.example` to `.env` and set the MySQL password and a strong SECRET_KEY.

Create the application database user as MySQL root using `create_app_user.sql`.
The password in that SQL file must match `DB_PASSWORD`.

Your existing `backup_registry` schema is already compatible. If needed, run:

    mysql -u root -p < schema.sql

## Create first login

Generate a password hash:

    python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('ChangeMe123!'))"

Then:

    sudo mysql
    USE backup_registry;
    INSERT INTO users (name, username, password_hash)
    VALUES ('Administrator', 'admin', 'PASTE_HASH_HERE');

## Run

    source .venv/bin/activate
    python3 run.py

Open http://127.0.0.1:5000

The application records `created_by` from the authenticated session and `created_at` from MySQL.


## Database

USE backup_registry;

CREATE TABLE IF NOT EXISTS branches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS backups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    branch_id INT NOT NULL,
    description VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    CONSTRAINT fk_backup_branch FOREIGN KEY (branch_id) REFERENCES branches(id),
    CONSTRAINT fk_backup_user FOREIGN KEY (created_by) REFERENCES users(id)
);

INSERT IGNORE INTO branches (name) VALUES
('RESPALDOS SEPE'),      ('RESPALDOS WEB'),      ('RESPALDOS USET'),      ('HISTORIALES SEPE USET');

## actions registry 

USE backup_registry;

CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    operation ENUM('CREATE', 'READ', 'UPDATE', 'DELETE') NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    record_id INT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_user
        FOREIGN KEY (user_id) REFERENCES users(id)
);

## User creation
CREATE USER 'backup_app'@'localhost'
 IDENTIFIED BY 'password';

GRANT SELECT, INSERT, UPDATE, DELETE
ON backup_registry.* TO 'backup_app'@'localhost';

FLUSH PRIVILEGES;

USE backup_registry;

INSERT INTO users (name, username, password_hash)
VALUES (
    'Leonel',
    'leonel',
    'Hash -> scrypt:32768:8:123...'
);

USE backup_registry;

SELECT id, name, username, password_hash
FROM users;

