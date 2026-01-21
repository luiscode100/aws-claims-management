import boto3
import os
import json
from datetime import datetime
import psycopg2  # librería para Conectarte a PostgreSQL y ejecutar SQL
from psycopg2.extras import RealDictCursor

# Configuración de Clientes AWS
sqs = boto3.client('sqs')

# Configuración Global
QUEUE_2_URL = os.environ.get('QUEUE_2_URL')
IVA_PORCENTAJE = 0.21


# Variables de entorno de la DB
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASSWORD')
DB_PORT = int(os.environ.get("DB_PORT", 5432))


def lambda_handler(event, context):
    print("--- INICIANDO CÁLCULO DE COSTES ---")
    
    # 1. PROCESAMIENTO DE MENSAJES DESDE SQS (Queue1)
    for record in event.get('Records', []):
        cliente = vehiculo = poliza = reparacion = None
        base_imponible = impuestos = total_reparacion = 0
        pago_aseguradora = pago_cliente = 0
        antiguedad = 0
        try:
            data = json.loads(record.get("body", "{}"))
            id_siniestro = data.get("id_siniestro")
            if not id_siniestro:
                print("Mensaje SQS inválido, falta 'id_siniestro'")
                continue

            id_siniestro = int(id_siniestro)

            try:
                conn = psycopg2.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASS
                )
                cur = conn.cursor(cursor_factory=RealDictCursor)# Crea un cursor que devuelve los resultados como diccionarios
                cur.execute("SELECT * FROM siniestros WHERE id_siniestro = %s", (id_siniestro,))# Ejecuta la consulta
                fila = cur.fetchone()  # {"id_siniestro": 5, "nombre": "pepito, "dni": "12345678X", ...}
                cur.close() # Cierra el cursor
                conn.close() # Cierra la conexión con la base de datos

                if not fila:
                    print(f"Siniestro {id_siniestro} no encontrado en la DB")
                    continue
                cliente = {
                    "nombre": fila["nombre"],
                    "dni": fila["dni"],
                    "email": fila["email"]
                }

                vehiculo = {
                    "matricula": fila["matricula"],
                    "marca": fila["marca"],
                    "modelo": fila["modelo"],
                    "anio": fila["anio"]
                }

                poliza = {
                    "tipo": fila["informacion_poliza"],
                    "franquicia": fila["franquicia"],
                    "limite_cobertura": fila["limite"]
                }

                reparacion = {
                    "coste_mano_obra": fila["mano_obra"],
                    "coste_piezas": fila["piezas"],
                    "taller": fila["taller"],
                    "estado": fila["estado_reparacion"],
                    "url_documento": fila["url_documento"]
                }

                # 2. CÁLCULOS DE DEPRECIACIÓN POR ANTIGÜEDAD
                mano_obra = float(reparacion.get('coste_mano_obra', 0))
                piezas = float(reparacion.get('coste_piezas', 0))
                
                anio_coche = int(fila["anio"])
                antiguedad = datetime.now().year - anio_coche
                
                depreciacion_piezas = 0.0
                if antiguedad > 10:
                    depreciacion_piezas = piezas * 0.20

                piezas_final = piezas - depreciacion_piezas
                base_imponible = mano_obra + piezas_final
                impuestos = base_imponible * IVA_PORCENTAJE
                total_reparacion = base_imponible + impuestos

                # 3. LÓGICA DE SEGURO (TERCEROS / TODO RIESGO / FRANQUICIA)
                tipo_seguro = poliza.get('tipo', 'TERCEROS').upper()
                franquicia = float(poliza.get('franquicia', 0))
                limite = float(poliza.get('limite_cobertura', 0))

                pago_aseguradora = 0.0
                pago_cliente = 0.0

                if tipo_seguro == 'TERCEROS':
                    pago_cliente = total_reparacion
                elif tipo_seguro == 'TODO_RIESGO':
                    if total_reparacion > limite:
                        pago_aseguradora = limite
                        pago_cliente = total_reparacion - limite
                    else:
                        pago_aseguradora = total_reparacion
                elif 'FRANQUICIA' in tipo_seguro: #  si la palabra'FRANQUICIA' esta contenida en cualquier parte del string
                    if total_reparacion <= franquicia:
                        pago_cliente = total_reparacion
                    else:
                        pago_cliente = franquicia
                        resto = total_reparacion - franquicia
                        if resto > limite:
                            pago_aseguradora = limite
                            pago_cliente += (resto - limite)
                        else:
                            pago_aseguradora = resto

                conn = psycopg2.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASS
                )
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE siniestros 
                    SET total_coste = %s, pago_aseguradora = %s, pago_cliente = %s, estado_reparacion = 'Estimacion realizada'
                    WHERE id_siniestro = %s
                    """,
                    (
                        round(total_reparacion, 2),
                        round(pago_aseguradora, 2),
                        round(pago_cliente, 2),
                        id_siniestro
                    )
                )
                
                conn.commit() #guarda el update
                cur.close() # Cierra el cursor
                conn.close() # Cierra la conexión
                print(f"Base de datos actualizada para siniestro: {id_siniestro}")
            except Exception as db_e:
                print(f"Error en DB: {str(db_e)}")


            # 5. PREPARAR DATOS (PDF/Email)
            resultado_calculo = {
                "id_siniestro": id_siniestro,
                "datos_cliente": cliente,
                "datos_vehiculo": vehiculo,
                "detalle_economico": {
                    "base_imponible": round(base_imponible, 2),
                    "iva": round(impuestos, 2),
                    "total_siniestro": round(total_reparacion, 2),
                    "pago_aseguradora": round(pago_aseguradora, 2),
                    "pago_cliente": round(pago_cliente, 2),
                    "antiguedad_aplicada": antiguedad
                }
            }

            # 6. ENVIAR A LA SIGUIENTE COLA (Queue2)
            sqs.send_message(
                QueueUrl=QUEUE_2_URL, 
                MessageBody=json.dumps(resultado_calculo) #convierte el diccionario a string de json
            )
            print(f"Cálculo enviado a Queue2 para siniestro: {id_siniestro}")

        except Exception as e:
            print(f"Error procesando record: {str(e)}")
            continue

    return {'statusCode': 200, 'body': 'Cálculos completados y enviados'}