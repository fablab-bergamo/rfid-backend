from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from rfid_backend_FABLAB_BG.database.models import Machine, MachineType
from .webapplication import DBSession, app


@app.route("/machines", methods=["GET"])
def view_machines():
    session = DBSession()
    machines = session.query(Machine).order_by(Machine.machine_id).all()
    return render_template("view_machines.html", machines=machines)


@app.route("/machines/add", methods=["GET"])
def add_machine():
    session = DBSession()
    machine_types = session.query(MachineType).order_by(MachineType.type_id).all()
    return render_template("add_machine.html", machine_types=machine_types)


@app.route("/machines/create", methods=["POST"])
def create_machine():
    session = DBSession()
    machine_data = request.form
    new_machine = Machine(
        machine_name=machine_data["machine_name"],
        machine_type_id=machine_data["machine_type_id"],
        machine_hours=float(machine_data["machine_hours"]),
        blocked=machine_data.get("blocked", "off") == "on",
    )
    session.add(new_machine)
    session.commit()
    return redirect(url_for("view_machines"))


@app.route("/machines/edit/<int:machine_id>", methods=["GET"])
def edit_machine(machine_id):
    session = DBSession()
    machine = session.query(Machine).filter_by(machine_id=machine_id).one()
    machine_types = session.query(MachineType).order_by(MachineType.type_id).all()
    if machine:
        return render_template("edit_machine.html", machine=machine, machine_types=machine_types)
    else:
        return "Machine not found", 404


@app.route("/machines/update", methods=["POST"])
def update_machine():
    session = DBSession()
    machine_data = request.form
    machine = session.query(Machine).filter_by(machine_id=machine_data["machine_id"]).one()
    if machine:
        machine.machine_name = machine_data["machine_name"]
        machine.machine_type_id = machine_data["machine_type_id"]
        machine.machine_hours = float(machine_data["machine_hours"])
        machine.blocked = machine_data.get("blocked", "off") == "on"
        session.commit()
        return redirect(url_for("view_machines"))
    else:
        return "Machine not found", 404


@app.route("/machines/delete/<int:machine_id>", methods=["GET", "POST"])
def delete_machine(machine_id):
    machine = Machine.query.get(machine_id)
    session = DBSession()
    if not machine:
        return "Machine not found", 404

    if request.method == "POST":
        session.delete(machine)
        session.commit()
        return redirect(url_for("view_machines"))

    return render_template("delete_machine.html", machine=machine)
