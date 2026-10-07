from flask import request, jsonify, send_file
from analyzer import analyze_file
from cleaner import clean_file
from storage import (
    upload_file,
    download_file
)
import os
import uuid
import requests
import hmac
import hashlib
import time


QVAPAY_API_URL = "https://api.qvapay.com"

QVAPAY_WEBHOOK_URL = (
    "https://excelcleaner.onrender.com/"
    "api/qvapay/webhook"
)


def qvapay_headers(app_id, app_secret):
    return {
        "Content-Type": "application/json",
        "app-id": app_id,
        "app-secret": app_secret
    }


def verify_qvapay_webhook():
    app_secret = os.getenv("QVAPAY_APP_SECRET")

    if not app_secret:
        return False

    signature_header = request.headers.get(
        "x-qvapay-signature",
        ""
    )

    timestamp_header = request.headers.get(
        "x-qvapay-timestamp",
        ""
    )

    if not signature_header:
        return False

    if not timestamp_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    try:
        timestamp = int(timestamp_header)
    except ValueError:
        return False

    current_time = int(time.time())

    if abs(current_time - timestamp) > 300:
        return False

    raw_body = request.get_data(cache=True)

    expected_signature = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    provided_signature = signature_header[
        len("sha256="):
    ]

    if len(provided_signature) != len(expected_signature):
        return False

    return hmac.compare_digest(
        expected_signature,
        provided_signature
    )


def get_qvapay_transaction(transaction_uuid):
    app_id = os.getenv("QVAPAY_APP_ID")
    app_secret = os.getenv("QVAPAY_APP_SECRET")

    if not app_id or not app_secret:
        raise RuntimeError(
            "Faltan las credenciales de QvaPay."
        )

    response = requests.post(
        (
            f"{QVAPAY_API_URL}"
            f"/v2/transactions/"
            f"{transaction_uuid}"
        ),
        headers=qvapay_headers(
            app_id,
            app_secret
        ),
        timeout=20
    )

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            "QvaPay devolvió una respuesta que no es JSON."
        )

    if response.status_code != 200:
        raise RuntimeError(
            "No se pudo consultar la transacción "
            "en QvaPay."
        )

    transaction = data.get("transaction")

    if not transaction:
        raise RuntimeError(
            "QvaPay no devolvió los datos "
            "de la transacción."
        )

    return transaction


def find_original_file(upload_folder, file_id):
    for extension in [
        ".xlsx",
        ".xls",
        ".csv"
    ]:
        object_name = (
            f"original/"
            f"{file_id}"
            f"{extension}"
        )

        local_filename = (
            f"{file_id}"
            f"{extension}"
        )

        local_path = os.path.join(
            upload_folder,
            local_filename
        )

        try:
            download_file(
                object_name,
                local_path
            )

            return (
                extension,
                object_name,
                local_path
            )

        except Exception:
            if os.path.isfile(local_path):
                os.remove(local_path)

    return None


def cleaned_file_exists(upload_folder, file_id):
    for extension in [
        ".xlsx",
        ".xls",
        ".csv"
    ]:
        output_filename = (
            f"{file_id}"
            f"_cleaned"
            f"{extension}"
        )

        cleaned_object = (
            f"cleaned/"
            f"{output_filename}"
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

            if os.path.isfile(local_path):
                os.remove(local_path)

            return True

        except Exception:
            if os.path.isfile(local_path):
                os.remove(local_path)

    return False


def process_paid_file(file_id, upload_folder):
    if cleaned_file_exists(
        upload_folder,
        file_id
    ):
        return {
            "file_id": file_id,
            "download_ready": True
        }

    original_result = find_original_file(
        upload_folder,
        file_id
    )

    if not original_result:
        raise FileNotFoundError(
            "No se encontró el archivo original "
            "del pedido."
        )

    (
        extension,
        original_object,
        input_path
    ) = original_result

    output_filename = (
        f"{file_id}"
        f"_cleaned"
        f"{extension}"
    )

    output_path = os.path.join(
        upload_folder,
        output_filename
    )

    cleaned_object = (
        f"cleaned/"
        f"{output_filename}"
    )

    try:
        clean_file(
            input_path,
            output_path
        )

        upload_file(
            output_path,
            cleaned_object
        )

        return {
            "file_id": file_id,
            "download_ready": True
        }

    finally:
        if os.path.isfile(input_path):
            os.remove(input_path)

        if os.path.isfile(output_path):
            os.remove(output_path)


def calculate_order_price(upload_folder, file_id):
    original_result = find_original_file(
        upload_folder,
        file_id
    )

    if not original_result:
        raise FileNotFoundError(
            "No se encontró el archivo original "
            "del pedido."
        )

    (
        extension,
        original_object,
        input_path
    ) = original_result

    try:
        result = analyze_file(input_path)

        return result["price"]

    finally:
        if os.path.isfile(input_path):
            os.remove(input_path)


def register_api(app, upload_folder):

    @app.route(
        "/api/analyze",
        methods=["POST"]
    )
    def api_analyze():

        file = request.files.get("file")

        if not file or file.filename == "":
            return jsonify({
                "error":
                    "No seleccionaste ningún archivo."
            }), 400

        extension = os.path.splitext(
            file.filename
        )[1].lower()

        if extension not in [
            ".xlsx",
            ".xls",
            ".csv"
        ]:
            return jsonify({
                "error":
                    "Solo se permiten archivos CSV o Excel."
            }), 400

        file_id = str(uuid.uuid4())

        input_filename = (
            f"{file_id}"
            f"{extension}"
        )

        input_path = os.path.join(
            upload_folder,
            input_filename
        )

        output_filename = (
            f"{file_id}"
            f"_cleaned"
            f"{extension}"
        )

        output_path = os.path.join(
            upload_folder,
            output_filename
        )

        original_object = (
            f"original/"
            f"{input_filename}"
        )

        cleaned_object = (
            f"cleaned/"
            f"{output_filename}"
        )

        try:
            file.save(input_path)

            result = analyze_file(input_path)

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
                "error":
                    "Archivo no especificado."
            }), 400

        for extension in [
            ".xlsx",
            ".xls",
            ".csv"
        ]:
            output_filename = (
                f"{file_id}"
                f"_cleaned"
                f"{extension}"
            )

            cleaned_object = (
                f"cleaned/"
                f"{output_filename}"
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
            "error":
                "Archivo no encontrado."
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
                "error":
                    "Falta QVAPAY_APP_ID."
            }), 500

        if not app_secret:
            return jsonify({
                "error":
                    "Falta QVAPAY_APP_SECRET."
            }), 500

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "error":
                    "Solicitud inválida."
            }), 400

        file_id = data.get("file_id")

        if not file_id:
            return jsonify({
                "error":
                    "Falta file_id."
            }), 400

        try:
            amount = calculate_order_price(
                upload_folder,
                file_id
            )

        except FileNotFoundError as e:
            return jsonify({
                "error": str(e)
            }), 404

        except Exception as e:
            return jsonify({
                "error":
                    f"No se pudo calcular el precio real: {e}"
            }), 500

        if amount <= 0:
            return jsonify({
                "error":
                    "Este archivo no requiere pago."
            }), 400

        remote_id = (
            f"excelcleaner-"
            f"{file_id}"
        )

        payload = {
            "amount": amount,

            "description":
                "Limpieza de archivo Excel/CSV",

            "remote_id":
                remote_id,

            "webhook":
                QVAPAY_WEBHOOK_URL,

            "products": [
                {
                    "name":
                        "Limpieza de archivo Excel/CSV",

                    "price":
                        amount,

                    "quantity":
                        1
                }
            ]
        }

        try:
            response = requests.post(
                (
                    f"{QVAPAY_API_URL}"
                    "/v2/create_invoice"
                ),
                headers=qvapay_headers(
                    app_id,
                    app_secret
                ),
                json=payload,
                timeout=20
            )

            try:
                qvapay_data = response.json()
            except ValueError:
                return jsonify({
                    "error":
                        "QvaPay devolvió una respuesta "
                        "que no es JSON."
                }), 502

            if response.status_code != 200:
                return jsonify({
                    "error":
                        "QvaPay rechazó la factura.",

                    "qvapay":
                        qvapay_data
                }), response.status_code

            transaction_uuid = (
                qvapay_data.get(
                    "transaction_uuid"
                )
            )

            payment_url = (
                qvapay_data.get(
                    "url"
                )
            )

            if not transaction_uuid:
                return jsonify({
                    "error":
                        "QvaPay no devolvió el UUID "
                        "de la transacción."
                }), 502

            if not payment_url:
                return jsonify({
                    "error":
                        "QvaPay no devolvió la URL "
                        "de pago."
                }), 502

            return jsonify({
                "success": True,

                "file_id":
                    file_id,

                "transaction_uuid":
                    transaction_uuid,

                "payment_url":
                    payment_url
            }), 200

        except requests.RequestException:
            return jsonify({
                "error":
                    "No se pudo conectar con QvaPay."
            }), 502


    @app.route(
        "/api/qvapay/status/<transaction_uuid>",
        methods=["GET"]
    )
    def qvapay_status(transaction_uuid):

        if not transaction_uuid:
            return jsonify({
                "error":
                    "Falta el UUID de la transacción."
            }), 400

        try:
            transaction = get_qvapay_transaction(
                transaction_uuid
            )

            remote_id = transaction.get(
                "remote_id"
            )

            expected_prefix = "excelcleaner-"

            if not isinstance(remote_id, str):
                return jsonify({
                    "error":
                        "La transacción no pertenece "
                        "a Excel Cleaner."
                }), 403

            if not remote_id.startswith(
                expected_prefix
            ):
                return jsonify({
                    "error":
                        "La transacción no pertenece "
                        "a Excel Cleaner."
                }), 403

            file_id = remote_id[
                len(expected_prefix):
            ]

            status = transaction.get("status")

            if status == "paid":

                result = process_paid_file(
                    file_id,
                    upload_folder
                )

                return jsonify({
                    "status":
                        "paid",

                    "file_id":
                        file_id,

                    "download_ready":
                        result["download_ready"]
                }), 200

            return jsonify({
                "status":
                    status,

                "file_id":
                    file_id,

                "download_ready":
                    False
            }), 200

        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 502


    @app.route(
        "/api/qvapay/webhook",
        methods=["POST"]
    )
    def qvapay_webhook():

        if not verify_qvapay_webhook():
            return jsonify({
                "error":
                    "Firma de QvaPay inválida."
            }), 401

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "error":
                    "Solicitud inválida."
            }), 400

        transaction_uuid = data.get("uuid")

        if not transaction_uuid:
            return jsonify({
                "error":
                    "Falta el UUID de la transacción."
            }), 400

        try:
            transaction = get_qvapay_transaction(
                transaction_uuid
            )

            remote_id = transaction.get(
                "remote_id"
            )

            expected_prefix = "excelcleaner-"

            if not isinstance(remote_id, str):
                return jsonify({
                    "error":
                        "Transacción inválida."
                }), 400

            if not remote_id.startswith(
                expected_prefix
            ):
                return jsonify({
                    "error":
                        "La transacción no pertenece "
                        "a Excel Cleaner."
                }), 403

            if transaction.get("status") != "paid":
                return jsonify({
                    "received": True,
                    "processed": False
                }), 200

            file_id = remote_id[
                len(expected_prefix):
            ]

            result = process_paid_file(
                file_id,
                upload_folder
            )

            return jsonify({
                "received": True,

                "processed": True,

                "file_id":
                    file_id,

                "download_ready":
                    result["download_ready"]
            }), 200

        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500


    @app.route(
        "/payment/success",
        methods=["GET"]
    )
    def payment_success():

        return """
        <!DOCTYPE html>
        <html lang="es">

        <head>
            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>
                Pago completado
            </title>
        </head>

        <body>

            <h1>
                Pago completado
            </h1>

            <p>
                Tu pago fue recibido correctamente.
            </p>

            <p>
                Puedes volver a Excel Cleaner
                para descargar tu archivo.
            </p>

        </body>

        </html>
        """


    @app.route(
        "/payment/cancel",
        methods=["GET"]
    )
    def payment_cancel():

        return """
        <!DOCTYPE html>
        <html lang="es">

        <head>
            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>
                Pago cancelado
            </title>
        </head>

        <body>

            <h1>
                Pago cancelado
            </h1>

            <p>
                El pago no fue completado.
            </p>

            <p>
                Tu archivo permanece guardado
                temporalmente.
            </p>

        </body>

        </html>
        """