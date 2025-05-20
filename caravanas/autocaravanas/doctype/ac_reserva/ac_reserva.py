# Copyright (c) 2025, aaira and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now, add_days
import uuid
from frappe.model.document import Document

class ACReserva(Document):
    pass

# Método para consultar disponibilidad de un intervalo de fechas
@frappe.whitelist(allow_guest=True)
def consultar_disponibilidad(autocaravana_id, fecha_inicio, fecha_fin):
    reservas = frappe.get_all("Reserva", filters={
        "autocaravana": autocaravana_id,
        "fecha_recogida": ["<=", fecha_fin],
        "fecha_devolucion": [">=", fecha_inicio],
        "estado": ["!=", "Cancelada"]
    })
    return len(reservas) == 0


# Método para crear una reserva temporal
@frappe.whitelist()
def crear_reserva_temporal(autocaravana_id, fecha_inicio, fecha_fin, extras):
    reserva_id = str(uuid.uuid4())
    reserva_temp = frappe.get_doc({
        "doctype": "Reserva Temporal",
        "UUID": reserva_id,
        "autocaravana": autocaravana_id,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "estado": "Activo",
        "expira_en": add_days(now(), 1),
        "extras": extras
    })
    reserva_temp.insert()
    frappe.db.commit()
    return reserva_id

# Método para crear una nueva reserva con datos completos
@frappe.whitelist()
def crear_reserva_completa(data):
    cliente = frappe.get_doc({
        "doctype": "Cliente",
        **data.get("cliente")
    })
    cliente.insert(ignore_permissions=True)

    conductor = frappe.get_doc({
        "doctype": "Conductor",
        **data.get("conductor_principal")
    })
    conductor.insert(ignore_permissions=True)

    for conductor_data in data.get("conductores_adicionales", []):
        conductor_adicional = frappe.get_doc({
            "doctype": "Conductor",
            **conductor_data
        })
        conductor_adicional.insert(ignore_permissions=True)

    reserva = frappe.get_doc({
        "doctype": "Reserva",
        **data.get("reserva")
    })
    reserva.insert(ignore_permissions=True)
    frappe.db.commit()
    return reserva.name

# Método para cancelar una reserva existente
@frappe.whitelist()
def cancelar_reserva(reserva_id):
    reserva = frappe.get_doc("Reserva", reserva_id)
    reserva.estado = "Cancelada"
    reserva.save()
    frappe.db.commit()
    return "Reserva cancelada"

# Método para obtener una reserva por ID
@frappe.whitelist()
def get_reserva_por_id(reserva_id):
    return frappe.get_doc("Reserva", reserva_id)

# Método para obtener todas las reservas de un cliente
@frappe.whitelist()
def get_reservas_por_cliente(cliente_id):
    reservas = frappe.get_all("Reserva", filters={"cliente": cliente_id}, fields=["name", "autocaravana", "estado", "fecha_recogida", "fecha_devolucion"])
    return reservas

# Método para validar fechas elegidas
@frappe.whitelist()
def validar_fechas(fecha_inicio, fecha_fin):
    if fecha_inicio >= fecha_fin:
        return False, "La fecha de devolución debe ser posterior a la fecha de recogida."
    if fecha_inicio < now():
        return False, "La fecha de recogida no puede ser anterior a hoy."
    return True, "Fechas válidas"
