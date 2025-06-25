import frappe
import json
from frappe.utils import now_datetime, add_to_date
import random
import string

# ──────────────────────────────────────────────────────────────
# DISPONIBILIDAD
# ──────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def consultar_disponibilidad(autocaravana_id, fecha_inicio, fecha_fin):
    disponibilidad = frappe.get_all(
        'AC Disponibilidad Horaria',
        filters={
            'autocaravana': autocaravana_id,
            'fecha_inicio': ['<=', fecha_fin],
            'fecha_fin': ['>=', fecha_inicio],
            'estado': 'Libre' 
        },
    )

    tiene_registros = frappe.db.exists('AC Disponibilidad Horaria', {'autocaravana': autocaravana_id})
    if not tiene_registros:
        return {"disponible": True}

    return {"disponible": len(disponibilidad) > 0}


@frappe.whitelist(allow_guest=True)
def consultar_fechas_disponibles(autocaravana_id):
    return frappe.get_all(
        'AC Disponibilidad Horaria',
        filters={'autocaravana': autocaravana_id, 'estado': 'Libre'},
        fields=['fecha_inicio', 'fecha_fin']
    )


@frappe.whitelist(allow_guest=True)
def calendario_completo(autocaravana_id):
    def expandir_rangos(doctype, estado):
        rangos = frappe.get_all(
            doctype,
            filters={'autocaravana': autocaravana_id, 'estado': estado},
            fields=['fecha_inicio', 'fecha_fin']
        )
        fechas = []
        for r in rangos:
            inicio = r.fecha_inicio
            fin = r.fecha_fin
            while inicio <= fin:
                fechas.append(str(inicio))
                inicio = add_to_date(inicio, days=1)
        return fechas

    return {
        "ocupadas": expandir_rangos("AC Disponibilidad Horaria", "Ocupada"),
        "temporales": expandir_rangos("AC Reserva Temporal", "Activo")
    }

# ──────────────────────────────────────────────────────────────
# AUTOCARAVANAS
# ──────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def obtener_detalles_autocaravana(autocaravana_id):
    detalles = frappe.get_doc('AC Autocaravana', autocaravana_id)
    return detalles.as_dict()

# ──────────────────────────────────────────────────────────────
# EXTRAS
# ──────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def consultar_extras(autocaravana_id):
    return frappe.get_all(
        'AC Extras',
        filters={'autocaravana': autocaravana_id},
        fields=['nombre', 'descripcion', 'precio_por_dia']
    )

# ──────────────────────────────────────────────────────────────
# RESERVAS Y COSTES
# ──────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True) 
def calcular_valor_estimado(autocaravana_id, dias, extras):
    autocaravana = frappe.get_doc('AC Autocaravana', autocaravana_id)
    precio_total = autocaravana.precio_por_dia * int(dias)

    for extra_id in extras:
        extra_doc = frappe.get_doc('AC Extras', extra_id)
        precio_total += extra_doc.precio

    return precio_total

# ──────────────────────────────────────────────────────────────
# CLIENTE, CONDUCTOR, CONDUCTORES ADICIONALES
# ──────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def guardar_datos_reserva(data_json):
    try:
        data = json.loads(data_json)

        cliente_data = data.get("cliente")
        adicionales_data = data.get("conductores_adicionales", [])
        es_conductor = cliente_data.get("es_conductor", False)
        reserva_uuid = data.get("reserva_uuid")

        if not reserva_uuid:
            frappe.throw("Falta el UUID de la reserva temporal.")

        reserva_temp = frappe.get_doc("AC Reserva Temporal", {"uuid": reserva_uuid})

        def extraer_email(d):
            return d.get("correo_electronico") or d.get("email") or ""

        # Log datos crudos
        frappe.logger().info(f"[RESERVA] Datos del cliente recibidos: {json.dumps(cliente_data, indent=2)}")

        # Crear cliente con campos permitidos
        cliente_doc = frappe.new_doc("AC Cliente")
        cliente_doc.nombre = cliente_data.get("nombre", "")
        cliente_doc.apellidos = cliente_data.get("apellidos", "")
        cliente_doc.tipo_de_identificacion = cliente_data.get("tipo_de_identificacion", "")
        cliente_doc.nifcifpasaporte = cliente_data.get("nifcifpasaporte", "")
        cliente_doc.correo_electronico = extraer_email(cliente_data)
        cliente_doc.telefono = cliente_data.get("telefono", "")
        cliente_doc.direccion = cliente_data.get("direccion", "")
        cliente_doc.usuario = cliente_data.get("usuario") if "usuario" in cliente_data else None
        cliente_doc.es_conductor = 1 if cliente_data.get("es_conductor") else 0

        frappe.logger().info(f"[RESERVA] Cliente a insertar: {cliente_doc.as_dict()}")
        cliente_doc.insert()

        # Determinar datos del conductor
        conductor_data = cliente_data if es_conductor else data.get("conductor")
        frappe.logger().info(f"[RESERVA] Datos del conductor: {json.dumps(conductor_data, indent=2)}")

        conductor_doc = frappe.new_doc("AC Conductor")
        conductor_doc.nombre = conductor_data.get("nombre", "")
        conductor_doc.apellidos = conductor_data.get("apellidos", "")
        conductor_doc.tipo_de_identificacion = conductor_data.get("tipo_de_identificacion", "")
        conductor_doc.nifcifpasaporte = conductor_data.get("nifcifpasaporte", "")
        conductor_doc.email = extraer_email(conductor_data)
        conductor_doc.telefono = conductor_data.get("telefono", "")
        conductor_doc.direccion = conductor_data.get("direccion", "")
        conductor_doc.fecha_de_nacimiento = conductor_data.get("fecha_de_nacimiento")
        conductor_doc.nacionalidad = conductor_data.get("nacionalidad")
        conductor_doc.permiso_de_conducir = conductor_data.get("permiso_de_conducir")
        conductor_doc.validez_de_permiso = conductor_data.get("validez_de_permiso")

        conductor_doc.insert()

        # Insertar adicionales
        adicionales_ids = []
        for adicional in adicionales_data:
            adicional_doc = frappe.new_doc("AC Conductor")
            adicional_doc.nombre = adicional.get("nombre", "")
            adicional_doc.apellidos = adicional.get("apellidos", "")
            adicional_doc.tipo_de_identificacion = adicional.get("tipo_de_identificacion", "")
            adicional_doc.nifcifpasaporte = adicional.get("nifcifpasaporte", "")
            adicional_doc.email = extraer_email(adicional)
            adicional_doc.telefono = adicional.get("telefono", "")
            adicional_doc.direccion = adicional.get("direccion", "")
            adicional_doc.fecha_de_nacimiento = adicional.get("fecha_de_nacimiento")
            adicional_doc.nacionalidad = adicional.get("nacionalidad")
            adicional_doc.permiso_de_conducir = adicional.get("permiso_de_conducir")
            adicional_doc.validez_de_permiso = adicional.get("validez_de_permiso")

            adicional_doc.insert()
            adicionales_ids.append(adicional_doc.name)

        # Extras y cálculo
        extras = []
        if reserva_temp.get("extras"):
            for e in reserva_temp.extras:
                extras.append({
                    "extra": e.extra,
                    "precio_por_dia": e.precio,
                    "cantidad": e.cantidad,
                    "total": e.total
                })

        dias = (reserva_temp.fecha_fin - reserva_temp.fecha_inicio).days or 1
        precio_dia = frappe.get_value("AC Autocaravana", reserva_temp.autocaravana, "precio_por_dia") or 0
        importe_extras = sum(e["total"] for e in extras)
        importe_total = (dias * precio_dia) + importe_extras

        reserva_def = frappe.new_doc("AC Reserva")
        reserva_def.update({
            "cliente": cliente_doc.name,
            "conductor": conductor_doc.name,
            "autocaravana": reserva_temp.autocaravana,
            "fecha_recogida": reserva_temp.fecha_inicio,
            "fecha_devolucion": reserva_temp.fecha_fin,
            "extras": extras,
            "importe_pagado": round(importe_total, 2),
            "estado": "Pendiente"
        })
        reserva_def.insert()

        for adicional_id in adicionales_ids:
            reserva_def.append("conductor_adicional", {
                "conductor": adicional_id
            })
        reserva_def.save()

        return {
            "status": "success",
            "reserva_id": reserva_def.name,
            "cliente": cliente_doc.name,
            "conductor": conductor_doc.name,
            "adicionales": adicionales_ids,
            "precio_total": round(importe_total, 2),
            "autocaravana_nombre": frappe.get_value("AC Autocaravana", reserva_temp.autocaravana, "nombre")
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error en guardar_datos_reserva")
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def obtener_datos_reserva(reserva_id):
    try:
        reserva = frappe.get_doc("AC Reserva", reserva_id)

        return {
            "codigo": reserva.name,
            "fecha_inicio": frappe.utils.formatdate(reserva.fecha_recogida),
            "fecha_fin": frappe.utils.formatdate(reserva.fecha_devolucion),
            "duracion": f"{(reserva.fecha_devolucion - reserva.fecha_recogida).days} días",
            "extras": [e.extra for e in reserva.extras] if reserva.extras else [],
            "total": float(reserva.importe_pagado or 0)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "❌ Error obteniendo datos reserva")
        frappe.local.response['http_status_code'] = 500
        return {"error": str(e)}


# ───────────────────────────────────────────────────
# FUNCION AUXILIAR: VALIDAR FECHAS OCUPADAS
# ───────────────────────────────────────────────────

def validar_fechas_ocupadas(autocaravana_id, fecha_inicio, fecha_fin):
    conflicto = frappe.get_all(
        "AC Reserva",
        filters={
            "autocaravana": autocaravana_id,
            "estado": "Confirmada",
            "fecha_recogida": ["<=", fecha_fin],
            "fecha_devolucion": [">=", fecha_inicio]
        },
        fields=["name"]
    )
    if conflicto:
        frappe.throw("❌ Ya existe una reserva confirmada que se solapa con las fechas indicadas.")


# ───────────────────────────────────────────────────
# STRIPE WEBHOOK ACTUALIZADO
# ───────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def stripe_webhook():
    try:
        event = frappe.request.get_json()
        frappe.logger().info(f"[Webhook] Stripe payload: {json.dumps(event, indent=2)}")

        if event.get("type") != "checkout.session.completed":
            return "Event ignored", 200

        session = event.get("data", {}).get("object", {})
        metadata = session.get("metadata", {})
        reserva_id = metadata.get("reserva_id")

        if not reserva_id:
            frappe.log_error("Falta 'reserva_id' en metadata", "❌ Webhook Stripe")
            return "Missing metadata", 400

        try:
            reserva = frappe.get_doc("AC Reserva", reserva_id)
            reserva.estado = "Confirmada"
            reserva.metodo_de_pago = "Stripe"
            reserva.importe_pagado = session.get("amount_total", 0) / 100
            reserva.save()
            frappe.db.commit()
            frappe.logger().info(f"✅ Reserva {reserva_id} confirmada")

            reserva_temp = frappe.get_doc("AC Reserva Temporal", {"uuid": reserva_id})
            reserva_temp.estado = "Inactivo"
            reserva_temp.save()
            frappe.db.commit()

            fechas_bloqueadas = frappe.new_doc("AC Disponibilidad Horaria")
            fechas_bloqueadas.update({
                "autocaravana": reserva.autocaravana,
                "fecha_inicio": reserva.fecha_recogida,
                "fecha_fin": reserva.fecha_devolucion,
                "estado": "Ocupada"
            })
            fechas_bloqueadas.insert()
            frappe.db.commit()

            return "OK", 200

        except Exception:
            frappe.log_error(frappe.get_traceback(), f"❌ Error procesando reserva {reserva_id}")
            return "Error interno", 500

    except Exception:
        frappe.log_error(frappe.get_traceback(), "❌ Error en webhook Stripe")
        return "Invalid payload", 400
     