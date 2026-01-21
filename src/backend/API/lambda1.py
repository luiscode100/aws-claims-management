import os
import json
import psycopg2
import boto3

# Configuración
QUEUE_URL = os.environ.get("QUEUE_URL")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "clase")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
id_siniestro = None

sqs = boto3.client("sqs")

def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    method = event.get("httpMethod", "")

    if method == "OPTIONS":
        return build_response(200, "")

    if method == "POST":
        raw_body = event.get("body")
        if not raw_body:
            return build_response(400, {"error": "Body vacío"})

        try:
            body = json.loads(raw_body)
        except Exception as e:
            return build_response(400, {"error": f"Body inválido: {str(e)}"})

        try:
            cliente = body["cliente"]
            vehiculo = body["vehiculo"]
            poliza = body["poliza"]
            reparacion = body["reparacion"]
        except KeyError as e:
            return build_response(400, {"error": f"Campo requerido ausente: {str(e)}"})

        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO siniestros (
                    nombre,
                    dni,
                    email,
                    matricula,
                    marca,
                    modelo,
                    anio,
                    informacion_poliza,
                    limite,
                    franquicia,
                    taller,
                    mano_obra,
                    piezas
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_siniestro
                """,
                (
                    cliente["nombre"],
                    cliente["dni"],
                    cliente["email"],
                    vehiculo["matricula"],
                    vehiculo["marca"],
                    vehiculo["modelo"],
                    vehiculo.get("anio"),
                    poliza["tipo"],
                    poliza.get("limite"),
                    poliza.get("franquicia"),
                    reparacion.get("taller"),
                    reparacion.get("mo"),
                    reparacion.get("piezas")
                )
            )

            id_siniestro = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            return build_response(500, {"error": f"No se pudo guardar en DB: {str(e)}"})

        # Enviar mensaje a SQS
        try:
            sqs.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps({
                    "id_siniestro": id_siniestro
                })
            )
        except Exception as e:
            return build_response(500, {"error": f"No se pudo enviar a SQS: {str(e)}"})

        # Respuesta HTTP
        return build_response(200, {"message": "Datos recibidos, guardados en DB y enviados a SQS"})
    
    elif method == "GET":
        params = event.get("queryStringParameters") or {}
        search = params.get("search", "").strip()
        if not search:
            return build_response(400, {"error": "Falta parámetro 'search'"})

        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            cur = conn.cursor()
            # Buscar por ID o DNI
            cur.execute(
                """
                SELECT id_siniestro, nombre, dni, email, matricula, marca, modelo, anio,
                       informacion_poliza, limite, franquicia, taller, mano_obra, piezas, url_documento
                FROM siniestros
                WHERE id_siniestro::text = %s OR dni = %s
                """,
                (search, search)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

            if not row:
                return build_response(404, {"error": "No se encontró el siniestro"})

            result = {
                "id_siniestro": row[0],
                "cliente": {"nombre": row[1], "dni": row[2], "email": row[3]},
                "vehiculo": {"matricula": row[4], "marca": row[5], "modelo": row[6], "anio": row[7]},
                "poliza": {"tipo": row[8], "limite": float(row[9] or 0), "franquicia": float(row[10] or 0)},
                "reparacion": {"taller": row[11], "mo": float(row[12] or 0), "piezas": float(row[13] or 0)},
                "url_documento": row[14]
            }

            return build_response(200, result)

        except Exception as e:
            return build_response(500, {"error": f"Error al consultar DB: {str(e)}"})
    else:
        return build_response(405, {"error": f"Método HTTP {method} no permitido"})
