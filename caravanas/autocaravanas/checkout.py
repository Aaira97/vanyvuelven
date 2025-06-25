import frappe
import json
import stripe

@frappe.whitelist(allow_guest=True)
def create_checkout_session(data):
    try:
        # Obtener clave de Stripe
        config = frappe.get_all("AC Configuracion", fields=["clave_api_stripe"], order_by="creation desc", limit=1)
        if not config or not config[0].get("clave_api_stripe"):
            frappe.log_error("No se encontró la clave API de Stripe", "❌ Configuración Stripe")
            frappe.local.response['http_status_code'] = 417
            return {"error": "Falta clave API", "clientSecret": None}

        stripe.api_key = config[0]["clave_api_stripe"]
        frappe.logger().info("✅ Clave Stripe cargada correctamente")

        payload = json.loads(data)
        email = payload.get('email')
        autocaravana = payload.get('autocaravana')
        precio = payload.get('precio')
        reserva_id = payload.get('reserva_id')

        if not all([email, autocaravana, precio, reserva_id]):
            frappe.logger().error(f"❌ Datos faltantes en payload: {payload}")
            frappe.local.response['http_status_code'] = 417
            return {"error": "Datos requeridos faltan", "clientSecret": None}

        try:
            precio_int = int(float(precio) * 100)
        except Exception as err:
            frappe.logger().error(f"❌ Precio no válido: {precio} -> {err}")
            frappe.local.response['http_status_code'] = 417
            return {"error": "Precio inválido", "clientSecret": None}

        # Crear sesión
        session = stripe.checkout.Session.create(
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": autocaravana},
                    "unit_amount": precio_int,
                },
                "quantity": 1,
            }],
            metadata={
                "email": email,
                "producto": autocaravana,
                "precio": precio,
                "reserva_id": reserva_id
            },
            mode="payment",
            ui_mode="embedded",
            redirect_on_completion="never"  
        )

        # Validación explícita
        if not session or not session.client_secret:
            frappe.logger().error(f"❌ Sesión de Stripe inválida o sin client_secret: {session}")
            frappe.local.response['http_status_code'] = 417
            return {"error": "Fallo al crear sesión de Stripe", "clientSecret": None}

        frappe.logger().info(f"✅ Sesión Stripe creada: {session.id}")
        return {"clientSecret": session.client_secret}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "❌ Stripe Error")
        frappe.local.response['http_status_code'] = 417
        return {"error": str(e), "clientSecret": None}
