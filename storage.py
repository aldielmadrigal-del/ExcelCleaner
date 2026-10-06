import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError


B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
B2_ENDPOINT = os.getenv("B2_ENDPOINT")


def get_s3_client():
    if not B2_KEY_ID:
        raise RuntimeError("Falta la variable B2_KEY_ID.")

    if not B2_APPLICATION_KEY:
        raise RuntimeError(
            "Falta la variable B2_APPLICATION_KEY."
        )

    if not B2_ENDPOINT:
        raise RuntimeError("Falta la variable B2_ENDPOINT.")

    return boto3.client(
        "s3",
        endpoint_url=B2_ENDPOINT,
        aws_access_key_id=B2_KEY_ID,
        aws_secret_access_key=B2_APPLICATION_KEY,
        region_name="us-east-005"
    )


def upload_file(local_path, object_name):
    client = get_s3_client()

    try:
        client.upload_file(
            local_path,
            B2_BUCKET_NAME,
            object_name
        )

    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(
            f"No se pudo subir el archivo a Backblaze: {e}"
        )


def download_file(object_name, local_path):
    client = get_s3_client()

    try:
        client.download_file(
            B2_BUCKET_NAME,
            object_name,
            local_path
        )

    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(
            f"No se pudo descargar el archivo desde Backblaze: {e}"
        )


def delete_file(object_name):
    client = get_s3_client()

    try:
        client.delete_object(
            Bucket=B2_BUCKET_NAME,
            Key=object_name
        )

    except (BotoCoreError, ClientError) as e:
        raise RuntimeError(
            f"No se pudo eliminar el archivo de Backblaze: {e}"
        )