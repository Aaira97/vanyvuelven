import frappe
import json
from frappe.utils import now_datetime, add_to_date

@frappe.whitelist(allow_guest=True)
def consultar_disponibilidad(autocaravana_id, fecha_inicio, fecha_fin):
    disponibilidad = frappe.get_all(
        'Disponibilidad Horaria',
        filters={
            'autocaravana': autocaravana_id,
            'fecha_inicio': ['<=', fecha_fin],
            'fecha_fin': ['>=', fecha_inicio],
            'estado': 'Libre'
        },
        fields=['name']
    )
    return disponibilidad
 
@frappe.whitelist(allow_guest=True)
def consultar_fechas_disponibles(autocaravana_id):
    fechas = frappe.get_all(
        'Disponibilidad Horaria',
        filters={'autocaravana': autocaravana_id, 'estado': 'Libre'},
        fields=['fecha_inicio', 'fecha_fin']
    )
    return fechas

@frappe.whitelist(allow_guest=True)
def obtener_detalles_autocaravana(autocaravana_id):
    detalles = frappe.get_doc('Autocaravana', autocaravana_id)
    return detalles.as_dict()

@frappe.whitelist(allow_guest=True)
def consultar_extras(autocaravana_id):
    extras = frappe.get_all(
        'Extras',
        filters={'autocaravana': autocaravana_id},
        fields=['nombre', 'descripcion', 'precio']
    )
    return extras

@frappe.whitelist(allow_guest=True)
def calcular_valor_estimado(autocaravana_id, dias, extras):
    autocaravana = frappe.get_doc('Autocaravana', autocaravana_id)
    precio_total = autocaravana.precio_por_dia * dias
    for extra in extras:
        extra_doc = frappe.get_doc('Extras', extra)
        precio_total += extra_doc.precio
    return precio_total

@frappe.whitelist(allow_guest=True)

def validar_fecha(fecha_inicio, fecha_fin):
    if fecha_inicio >= fecha_fin:
        return {'status': 'error', 'message': 'La fecha de inicio debe ser anterior a la fecha de fin.'}
    return {'status': 'success', 'message': 'Fechas válidas'}