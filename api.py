from flask import request, jsonify, send_file
from analyzer import analyze_file
from cleaner import clean_file
from storage import upload_file, download_file, delete_file
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

        input_object = (
            f"uploads/{input_filename}"
        )

        output_object = (
            f"cleaned/{output_filename}"
        )

        try:

            file.save(input_path)

            upload_file(
                input_path,
                input_object
            )

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
                    output_object
                )

                result["download_id"] = file_id

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

            output_object = (
                f"cleaned/{output_filename}"
            )

            local_path = os.path.join(
                upload_folder,
                output_filename
            )

            try:

                download_file(
                    output_object,
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