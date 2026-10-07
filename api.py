from flask import request, jsonify, send_file
from analyzer import analyze_file
from cleaner import clean_file
from storage import upload_file, download_file
import os
import uuid
import requests


QVAPAY_API_URL = "https://api.qvapay.com"


def register_api(app, upload_folder):

    @app.route("/api/analyze", methods=["POST"])
    def api_analyze():

        file = request.files.get("file")

        if not file or file.filename == "":
            return jsonify({
                "error": "No seleccionaste ningún archivo."
            }), 400

        extension = os.path.splitext(
            file.filename
        )[1].lower()

        if extension not in [".xlsx", ".xls", ".csv"]:
            return jsonify({
                "error": "Solo se permiten archivos CSV o Excel."
            }), 400

        file_id = str(uuid.uuid4())

        input_filename = (
            f"{file_id}{extension}"
        )

        input_path = os.path.join(
            upload_folder,
            input_filename
        )

        output_filename = (
            f"{file_id}_cleaned{extension}"
        )

        output_path = os.path.join(
            upload_folder,
            output_filename
        )

        original_object = (
            f"original/{input_filename}"
        )

        cleaned_object = (
            f"cleaned/{output_filename}"
        )

        try:

            file.save(input_path)

            result = analyze_file(
                input_path
            )

            if result["price"] == 0:

                clean_file(
                    input_path,
                    output_path
                )

                upload_file(
                    output_path,
                    cleaned_object
                )

                result["download_id"] = file_id

            else:

                upload_file(
                    input_path,
                    original_object
                )

                result["file_id"] = file_id

            return jsonify(result)

        except Exception as e:

            return jsonify({
                "error": str(e)
            }), 500

        finally:

            if os.path.isfile(input_path):
                os.remove(input_path)

            if os.path.isfile(output_path):
                os.remove(output_path)


    @app.route(
        "/api/download/<file_id>",
        methods=["GET"]
    )
    def api_download(file_id):

        if not file_id:
            return jsonify({
                "error": "Archivo no especificado."
            }), 400

        for extension in [".xlsx", ".xls", ".csv"]:

            output_filename = (
                f"{file_id}_cleaned{extension}"
            )

            cleaned_object = (
                f"cleaned/{output_filename}"
            )

            local_path = os.path.join(
                upload_folder,
                output_filename
            )

            try:

                download_file(
                    cleaned_object,
                    local_path
                )

                return send_file(
                    local_path,
                    as_attachment=True,
                    download_name=output_filename
                )

            except Exception:

                if os.path.isfile(local_path):
                    os.remove(local_path)

        return jsonify({
            "error": "Archivo no encontrado."
        }), 404


    @app.route(
        "/api/qvapay/create-invoice",
        methods=["POST"]
    )
    def qvapay_create_invoice():

        app_id = os.getenv("QVAPAY_APP_ID")
        app_secret = os.getenv("QVAPAY_APP_SECRET")

        if not app_id:
            return jsonify({
                "error": "Falta QVAPAY_APP_ID."
            }), 500

        if not app_secret:
            return jsonify({
                "error": "Falta QVAPAY_APP_SECRET."
            }), 500

        data = request.get_json(
            silent=True
        )

        if not data:
            return jsonify({
                "error": "Solicitud inválida."
            }), 400

        file_id = data.get("file_id")
        amount = data.get("amount")

        if not file_id:
            return jsonify({
                "error": "Falta file_id."
            }), 400

        try:
            amount = float(amount)
        except (TypeError, ValueError):

            return jsonify({
                "error": "El monto no es válido."
            }), 400

        if amount <= 0:
            return jsonify({
                "error": "El monto debe ser mayor que 0."
            }), 400

        remote_id = f"excelcleaner-{file_id}"

        payload = {
            "amount": amount,
            "description": "Limpieza de archivo Excel/CSV",
            "remote_id": remote_id,
            "webhook": (
                "https://excelcleaner.onrender.com/"
                "api/qvapay/webhook"
            ),
            "products": [
                {
                    "name": "Limpieza de archivo Excel/CSV",
                    "price": amount,
                    "quantity": 1
                }
            ]
        }

        try:

            response = requests.post(
                f"{QVAPAY_API_URL}/v2/create_invoice",
                headers={
                    "Content-Type": "application/json",
                    "app-id": app_id,
                    "app-secret": app_secret
                },
                json=payload,
                timeout=20
            )

            try:
                qvapay_data = response.json()
            except ValueError:

                return jsonify({
                    "error": (
                        "QvaPay devolvió una respuesta "
                        "que no es JSON."
                    )
                }), 502

            if response.status_code != 200:

                return jsonify({
                    "error": "QvaPay rechazó la factura.",
                    "qvapay": qvapay_data
                }), response.status_code

            return jsonify({
                "success": True,
                "file_id": file_id,
                "transaction_uuid": (
                    qvapay_data.get(
                        "transaction_uuid"
                    )
                ),
                "payment_url": (
                    qvapay_data.get("url")
                )
            }), 200

        except requests.RequestException as e:

            return jsonify({
                "error": (
                    "No se pudo conectar con QvaPay."
                ),
                "details": str(e)
            }), 502


    @app.route("/payment/success", methods=["GET"])
    def payment_success():

        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Pago completado</title>
        </head>
        <body>
            <h1>Pago completado</h1>
            <p>Tu pago fue recibido correctamente.</p>
            <p>Estamos preparando tu archivo.</p>
        </body>
        </html>
        """


    @app.route("/payment/cancel", methods=["GET"])
    def payment_cancel():

        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Pago cancelado</title>
        </head>
        <body>
            <h1>Pago cancelado</h1>
            <p>El pago no fue completado.</p>
            <p>Tu archivo original permanece guardado temporalmente.</p>
        </body>
        </html>
        """


    @app.route(
        "/api/qvapay/webhook",
        methods=["POST"]
    )
    def qvapay_webhook():

        data = request.get_json(
            silent=True
        )

        if not data:
            return jsonify({
                "error": "Solicitud inválida."
            }), 400

        return jsonify({
            "received": True
        }), 200