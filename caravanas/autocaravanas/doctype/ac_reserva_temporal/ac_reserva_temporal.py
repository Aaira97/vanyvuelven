import frappe
import uuid
import json
from datetime import datetime, timedelta
from frappe.utils import now_datetime, add_to_date

class ACReservaTemporal(frappe.model.document.Document):
    pass

@frappe.whitelist(allow_guest=True)
def crear_reserva_temporal():
    if frappe.request.method != "POST":
        frappe.throw("Este método solo acepta solicitudes POST.")

    try:
        data = json.loads(frappe.request.data)
    except Exception:
        frappe.throw("No se pudo interpretar el cuerpo JSON.")

    autocaravana_id = data.get("autocaravana_id")
    fecha_inicio = data.get("fecha_inicio")
    fecha_fin = data.get("fecha_fin")
    extras = data.get("extras", [])

    if not autocaravana_id or not fecha_inicio or not fecha_fin:
        frappe.throw("Faltan datos obligatorios para crear la reserva temporal.")

    now = now_datetime()

    # Eliminar reservas expiradas
    expiradas = frappe.get_all("AC Reserva Temporal", filters={"expira_en": ["<", now]})
    for r in expiradas:
        frappe.delete_doc("AC Reserva Temporal", r.name, ignore_permissions=True)

    # Validar conflictos con reservas temporales activas
    conflictos = frappe.get_all(
        "AC Reserva Temporal",
        filters={
            "autocaravana": autocaravana_id,
            "fecha_inicio": ["<", fecha_fin],
            "fecha_fin": [">", fecha_inicio],
            "estado": "Activo"
        }
    )

    if conflictos:
        frappe.throw("Las fechas seleccionadas ya están bloqueadas temporalmente.")

    # Construir la tabla hija
    extras_child_table = []
    for item in extras:
        if isinstance(item, dict) and item.get("extra"):
            extras_child_table.append({
                "doctype": "AC Extra Reserva",
                "extra": item["extra"],
                "precio_por_dia": item.get("precio_por_dia", 0),
                "cantidad": item.get("cantidad", 1),
                "total": item.get("total", 0)
            })

    # Crear la reserva
    reserva = frappe.get_doc({
        "doctype": "AC Reserva Temporal",
        "uuid": str(uuid.uuid4()),
        "autocaravana": autocaravana_id,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "estado": "Activo",
        "expira_en": now + timedelta(minutes=15),
        "extras": extras_child_table
    })

    reserva.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "uuid": reserva.uuid,
        "expira_en": reserva.expira_en
    }