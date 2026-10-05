from flask import request, jsonify, send_file
from analyzer import analyze_file
from cleaner import clean_file
import os
import uuid


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

                result["download_id"] = file_id

            return jsonify(result)

        except Exception as e:

            return jsonify({
                "error": str(e)
            }), 500


    @app.route(
        "/api/download/<file_id>",
        methods=["GET"]
    )
    def api_download(file_id):

        if not file_id:
            return jsonify({
                "error": "Archivo no especificado."
            }), 400

        filename = (
            f"{file_id}_cleaned.xlsx"
        )

        file_path = os.path.join(
            upload_folder,
            filename
        )

        if not os.path.isfile(file_path):

            csv_path = os.path.join(
                upload_folder,
                f"{file_id}_cleaned.csv"
            )

            if os.path.isfile(csv_path):
                file_path = csv_path
            else:
                return jsonify({
                    "error": "Archivo no encontrado."
                }), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(
                file_path
            )
        )
