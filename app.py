import os
import secrets
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "maintenance.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{DB_PATH}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    resident_tickets = db.relationship(
        "Ticket", back_populates="resident", foreign_keys="Ticket.resident_id"
    )
    assigned_tickets = db.relationship(
        "Ticket", back_populates="staff", foreign_keys="Ticket.staff_id"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(20), nullable=False, unique=True, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Open")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    resident_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    resident = db.relationship(
        "User", back_populates="resident_tickets", foreign_keys=[resident_id]
    )
    staff = db.relationship(
        "User", back_populates="assigned_tickets", foreign_keys=[staff_id]
    )


def generate_tracking_id() -> str:
    while True:
        tracking_id = f"APT-{datetime.utcnow():%Y%m%d}-{secrets.token_hex(3).upper()}"
        if not Ticket.query.filter_by(tracking_id=tracking_id).first():
            return tracking_id


def seed_users() -> None:
    if User.query.count() > 0:
        return

    demo_users = [
        ("resident1", "resident1@example.com", "resident123", "Resident"),
        ("admin1", "admin1@example.com", "admin123", "Admin"),
        ("staff1", "staff1@example.com", "staff123", "Staff"),
        ("staff2", "staff2@example.com", "staff123", "Staff"),
    ]

    for username, email, password, role in demo_users:
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)

    db.session.commit()


def init_database() -> None:
    with app.app_context():
        db.create_all()
        seed_users()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(role=None):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))

            if role and user.role != role:
                flash("You do not have access to that page.", "error")
                return redirect(url_for("dashboard"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def ticket_to_dict(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "tracking_id": ticket.tracking_id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "resident_id": ticket.resident_id,
        "resident_name": ticket.resident.username if ticket.resident else None,
        "staff_id": ticket.staff_id,
        "staff_name": ticket.staff.username if ticket.staff else None,
        "created_at": ticket.created_at.strftime("%Y-%m-%d %H:%M"),
    }


@app.route("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["role"] = user.role
            flash(f"Welcome back, {user.username}.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username/email or password.", "error")

    demo_users = User.query.order_by(User.role, User.username).all()
    return render_template("login.html", demo_users=demo_users)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([username, email, password, confirm_password]):
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("That username or email is already in use.", "error")
            return render_template("register.html")

        user = User(username=username, email=email, role="Resident")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Resident account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required()
def dashboard():
    user = current_user()

    if user.role == "Resident":
        tickets = (
            Ticket.query.filter_by(resident_id=user.id)
            .order_by(Ticket.created_at.desc())
            .all()
        )
        return render_template("resident_dashboard.html", user=user, tickets=tickets)

    if user.role == "Admin":
        tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
        staff_members = User.query.filter_by(role="Staff").order_by(User.username).all()
        analytics = {
            "total": Ticket.query.count(),
            "open": Ticket.query.filter_by(status="Open").count(),
            "in_progress": Ticket.query.filter_by(status="In-Progress").count(),
            "resolved": Ticket.query.filter_by(status="Resolved").count(),
        }
        return render_template(
            "admin_dashboard.html",
            user=user,
            tickets=tickets,
            staff_members=staff_members,
            analytics=analytics,
        )

    assigned_tickets = (
        Ticket.query.filter_by(staff_id=user.id).order_by(Ticket.created_at.desc()).all()
    )
    return render_template("staff_dashboard.html", user=user, tickets=assigned_tickets)


@app.route("/tickets", methods=["POST"])
@app.route("/api/tickets", methods=["POST"])
@login_required(role="Resident")
def create_ticket():
    user = current_user()
    payload = request.get_json(silent=True) or request.form

    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    category = (payload.get("category") or "").strip()
    priority = (payload.get("priority") or "").strip()

    if not all([title, description, category, priority]):
        message = "All ticket fields are required."
        if request.is_json:
            return jsonify({"error": message}), 400
        flash(message, "error")
        return redirect(url_for("dashboard"))

    ticket = Ticket(
        tracking_id=generate_tracking_id(),
        title=title,
        description=description,
        category=category,
        priority=priority,
        status="Open",
        resident_id=user.id,
    )
    db.session.add(ticket)
    db.session.commit()

    if request.is_json:
        return jsonify({"message": "Ticket created.", "ticket": ticket_to_dict(ticket)}), 201

    flash(f"Ticket submitted successfully. Tracking ID: {ticket.tracking_id}", "success")
    return redirect(url_for("dashboard"))


@app.route("/tickets/user/<int:user_id>", methods=["GET"])
@app.route("/api/tickets/user/<int:user_id>", methods=["GET"])
@login_required()
def get_user_tickets(user_id):
    user = current_user()

    if user.role == "Resident" and user.id != user_id:
        return jsonify({"error": "Residents can only view their own tickets."}), 403

    target_user = User.query.get_or_404(user_id)
    tickets = (
        Ticket.query.filter_by(resident_id=target_user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return jsonify([ticket_to_dict(ticket) for ticket in tickets])


@app.route("/tickets/assign", methods=["PATCH"])
@app.route("/api/tickets/assign", methods=["PATCH"])
@login_required(role="Admin")
def assign_ticket():
    payload = request.get_json(silent=True) or request.form

    ticket_id = payload.get("ticket_id")
    staff_id = payload.get("staff_id")

    if not ticket_id or not staff_id:
        return jsonify({"error": "ticket_id and staff_id are required."}), 400

    ticket = Ticket.query.get_or_404(ticket_id)
    staff_member = User.query.filter_by(id=staff_id, role="Staff").first()
    if not staff_member:
        return jsonify({"error": "Staff member not found."}), 404

    ticket.staff_id = staff_member.id
    if ticket.status == "Open":
        ticket.status = "In-Progress"
    db.session.commit()

    return jsonify(
        {
            "message": f"Ticket {ticket.tracking_id} assigned to {staff_member.username}.",
            "ticket": ticket_to_dict(ticket),
        }
    )


@app.route("/tickets/status", methods=["PATCH"])
@app.route("/api/tickets/status", methods=["PATCH"])
@login_required()
def update_ticket_status():
    user = current_user()
    payload = request.get_json(silent=True) or request.form

    ticket_id = payload.get("ticket_id")
    status = (payload.get("status") or "").strip()
    allowed_statuses = {"Open", "In-Progress", "Resolved"}

    if not ticket_id or status not in allowed_statuses:
        return jsonify({"error": "Valid ticket_id and status are required."}), 400

    ticket = Ticket.query.get_or_404(ticket_id)

    if user.role == "Staff":
        if ticket.staff_id != user.id:
            return jsonify({"error": "You can only update your assigned tasks."}), 403
        if status != "Resolved":
            return jsonify({"error": "Staff can only mark tickets as Resolved."}), 403
    elif user.role != "Admin":
        return jsonify({"error": "You do not have permission to update ticket status."}), 403

    ticket.status = status
    db.session.commit()

    return jsonify({"message": "Ticket status updated.", "ticket": ticket_to_dict(ticket)})


@app.route("/api/analytics", methods=["GET"])
@login_required(role="Admin")
def analytics():
    category_summary = (
        db.session.query(Ticket.category, func.count(Ticket.id))
        .group_by(Ticket.category)
        .order_by(func.count(Ticket.id).desc())
        .all()
    )
    return jsonify(
        {
            "counts": {
                "total": Ticket.query.count(),
                "open": Ticket.query.filter_by(status="Open").count(),
                "in_progress": Ticket.query.filter_by(status="In-Progress").count(),
                "resolved": Ticket.query.filter_by(status="Resolved").count(),
            },
            "categories": [
                {"category": category, "count": count}
                for category, count in category_summary
            ],
        }
    )


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


init_database()


if __name__ == "__main__":
    app.run(debug=True)
