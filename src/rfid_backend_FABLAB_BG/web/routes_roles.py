from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from rfid_backend_FABLAB_BG.database.models import Role
from rfid_backend_FABLAB_BG.database.repositories import RoleRepository
from .webapplication import DBSession, app


@app.route("/roles")
def roles():
    session = DBSession()
    roles = session.query(Role).all()
    return render_template("view_roles.html", roles=roles)


@app.route("/roles/add", methods=["GET", "POST"])
def add_role():
    if request.method == "POST":
        session = DBSession()
        role_name = request.form["role_name"]
        authorize_all = request.form.get("authorize_all", "off") == "on"
        maintenance = request.form.get("maintenance", "off") == "on"
        role = Role(role_name=role_name, authorize_all=authorize_all, maintenance=maintenance, reserved=False)
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))
    else:
        return render_template("add_role.html")


@app.route("/roles/edit/<int:role_id>", methods=["GET", "POST"])
def edit_role(role_id):
    session = DBSession()
    role = session.query(Role).filter_by(role_id=role_id).one()

    # Block editing of reserved roles
    if not role:
        return "Role not found", 404

    if role.reserved:
        return "Cannot edit reserved role", 403

    if request.method == "POST":
        role.role_name = request.form["role_name"]
        role.authorize_all = request.form.get("authorize_all", "off") == "on"
        role.maintenance = request.form.get("maintenance", "off") == "on"
        session.add(role)
        session.commit()
        return redirect(url_for("roles"))

    return render_template("edit_role.html", role_id=role.role_id, role=role)


@app.route("/roles/delete/<int:role_id>", methods=["GET", "POST"])
def delete_role(role_id):
    session = DBSession()
    role_repo = RoleRepository(session)
    role = role_repo.get_by_id(role_id)
    if not role:
        return "Role not found", 404
    if role.reserved:
        return "Cannot delete reserved role", 403

    if request.method == "POST":
        role_repo.delete(role)
        flash("Role deleted successfully.")
        return redirect(url_for("roles"))

    return render_template("delete_role.html", role=role)
