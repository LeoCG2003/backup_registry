from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from .auth import login_required
from . import get_db

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return redirect(url_for("main.dashboard" if "user_id" in session else "main.login"))

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute(
            "SELECT id, name, username, password_hash FROM users WHERE username = %s",
            (username,)
        )
        user = cur.fetchone()
        cur.close()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("main.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")

@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))

@bp.route("/dashboard")
@login_required
def dashboard():
    branch_id = request.args.get("branch_id", type=int)
    search = request.args.get("search", "").strip()

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("SELECT id, name FROM branches ORDER BY id")
    branches = cur.fetchall()

    query = (
        "SELECT b.id, b.description, b.created_at, "
        "br.name AS branch_name, u.name AS creator_name "
        "FROM backups b "
        "JOIN branches br ON br.id = b.branch_id "
        "JOIN users u ON u.id = b.created_by "
        "WHERE 1=1 "
    )

    params = []

    if branch_id:
        query += "AND b.branch_id = %s "
        params.append(branch_id)

    if search:
        query += "AND b.description LIKE %s "
        params.append(f"%{search}%")

    query += "ORDER BY b.created_at DESC, b.id DESC"

    cur.execute(query, tuple(params))
    backups = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        "dashboard.html",
        branches=branches,
        backups=backups,
        selected_branch=branch_id,
        search=search,
        user_name=session["user_name"]
    )

@bp.route("/backups/new", methods=["GET", "POST"])
@login_required
def new_backup():
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "POST":
        branch_id = request.form.get("branch_id", type=int)
        description = request.form.get("description", "").strip()

        if not branch_id or not description:
            flash("Branch and filename are required.", "error")
        elif len(description) > 255:
            flash("Filename/description must be 255 characters or fewer.", "error")
        else:
            cur.execute("SELECT id FROM branches WHERE id = %s", (branch_id,))
            if not cur.fetchone():
                flash("Invalid branch.", "error")
            else:
                cur.execute(
                    "INSERT INTO backups (branch_id, description, created_by) "
                    "VALUES (%s, %s, %s)",
                    (branch_id, description, session["user_id"])
                )
                db.commit()
                cur.close()
                db.close()
                flash("Backup registered successfully.", "success")
                return redirect(url_for("main.dashboard"))

    cur.execute("SELECT id, name FROM branches ORDER BY id")
    branches = cur.fetchall()
    cur.close()
    db.close()
    return render_template("new_backup.html", branches=branches)

@bp.route("/backups/<int:backup_id>/edit", methods=["GET", "POST"])
@login_required
def edit_backup(backup_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT id, branch_id, description FROM backups WHERE id = %s",
        (backup_id,)
    )
    backup = cur.fetchone()

    if not backup:
        cur.close()
        db.close()
        flash("Respaldo no encontrado.", "error")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        branch_id = request.form.get("branch_id", type=int)
        description = request.form.get("description", "").strip()

        if not branch_id or not description:
            flash("La sucursal y el nombre del archivo son obligatorios.", "error")
        elif len(description) > 255:
            flash("El nombre/descripción no puede superar los 255 caracteres.", "error")
        else:
            cur.execute(
                """
                UPDATE backups
                SET branch_id = %s, description = %s
                WHERE id = %s
                """,
                (branch_id, description, backup_id)
            )

            cur.execute(
                """
                INSERT INTO audit_log
                    (user_id, operation, table_name, record_id, details)
                VALUES
                    (%s, 'UPDATE', 'backups', %s, %s)
                """,
                (
                    session["user_id"],
                    backup_id,
                    f"Backup actualizado: {description}"
                )
            )

            db.commit()

            cur.close()
            db.close()

            flash("Respaldo actualizado correctamente.", "success")
            return redirect(url_for("main.dashboard"))

    cur.execute("SELECT id, name FROM branches ORDER BY id")
    branches = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        "edit_backup.html",
        backup=backup,
        branches=branches
    )


@bp.post("/backups/<int:backup_id>/delete")
@login_required
def delete_backup(backup_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT id, description FROM backups WHERE id = %s",
        (backup_id,)
    )
    backup = cur.fetchone()

    if not backup:
        cur.close()
        db.close()
        flash("Respaldo no encontrado.", "error")
        return redirect(url_for("main.dashboard"))

    cur.execute(
        """
        INSERT INTO audit_log
            (user_id, operation, table_name, record_id, details)
        VALUES
            (%s, 'DELETE', 'backups', %s, %s)
        """,
        (
            session["user_id"],
            backup_id,
            f"Backup eliminado: {backup['description']}"
        )
    )

    cur.execute(
        "DELETE FROM backups WHERE id = %s",
        (backup_id,)
    )

    db.commit()

    cur.close()
    db.close()

    flash("Respaldo eliminado correctamente.", "success")
    return redirect(url_for("main.dashboard"))

@bp.route("/audit")
@login_required
def audit():
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        """
        SELECT
            a.id,
            a.operation,
            a.table_name,
            a.record_id,
            a.details,
            a.created_at,
            u.username
        FROM audit_log a
        JOIN users u ON u.id = a.user_id
        ORDER BY a.created_at DESC, a.id DESC
        """
    )

    logs = cur.fetchall()

    cur.close()
    db.close()

    return render_template("audit.html", logs=logs)