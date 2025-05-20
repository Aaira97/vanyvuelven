# Copyright (c) 2025, aaira and contributors
# For license information, please see license.txt

from frappe.model.document import Document
import frappe
from frappe.model import DisplayField
from datetime import datetime

class ACReservaTemporal(Document):
    def before_insert(self):
        """Validar que el UUID no esté vacío"""
        if not self.uuid:
            frappe.throw("El UUID es obligatorio para la reserva temporal.")

    def calcular_importe_estimado(self):
        """Método para calcular el importe estimado de la reserva temporal"""
        importe_estimado = 0

        # Obtener la autocaravana
        autocaravana = frappe.get_doc("AC Autocaravana", self.autocaravana)
        precio_por_dia = autocaravana.precio_por_dia
        dias_reserva = (self.fechas_fin - self.fechas_inicio).days

        # Calcular el precio base de la autocaravana
        importe_estimado += precio_por_dia * dias_reserva

        # Calcular los extras
        for extra in self.extras:
            extra_doc = frappe.get_doc("AC Extras", extra.extra)
            if extra_doc.precio_fijo_o_por_dia == "Por Día":
                importe_estimado += extra_doc.precio * dias_reserva * extra.cantidad
            else:
                importe_estimado += extra_doc.precio * extra.cantidad

        return importe_estimado

    def after_insert(self):
        """Acciones después de la creación de la reserva temporal"""
        # Calcular el importe estimado y guardar en el campo
        self.importe_estimado = self.calcular_importe_estimado()
        self.save()
        
    # Campos adicionales en la clase
    cliente = frappe.Field('Link', 'AC Cliente', allow_null=True, label="Cliente", required=False)
    uuid = frappe.Field('Data', allow_null=True, label="UUID")
    extras = frappe.Field('Table', 'AC Extras', allow_null=True, label="Extras")
    fechas_inicio = frappe.Field('Date', required=True)
    fechas_fin = frappe.Field('Date', required=True)
    expira_en = frappe.Field('Datetime', default=datetime.now())
    estado = frappe.Field('Select', choices=["Activa", "Expirada"], default="Activa")
    importe_estimado = frappe.Field('Currency', precision=2, default=0)

