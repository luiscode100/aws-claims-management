import os
import json
import psycopg2
import boto3
from fpdf import FPDF
from tempfile import NamedTemporaryFile

s3 = boto3.client('s3')
BUCKET_NAME = os.environ.get('BUCKET_NAME')
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASSWORD')
DB_PORT = int(os.environ.get("DB_PORT"))
DB_PORT = int(os.environ.get("DB_PORT"))

def lambda_handler(event, context):
    print("--- INICIANDO GENERACIÓN DE FACTURA ---")

    for record in event.get('Records', []):
        try:
            # 1. Parsear el mensaje que viene de Lambda 2
            data = json.loads(record.get('body', '{}'))
            
            siniestro_id = data.get('id_siniestro', 'SIN-DESCONOCIDO')
            cliente = data.get('datos_cliente', {})
            vehiculo = data.get('datos_vehiculo', {})
            detalle = data.get('detalle_economico', {})

            # 2. Configurar el PDF
            pdf = FPDF()
            pdf.add_page()
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, txt="INFORME DE TASACIÓN Y REPARACIÓN", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(190, 10, txt=f"Referencia: {siniestro_id}", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.cell(190, 8, txt=f"Asegurado: {cliente.get('nombre')}", ln=True)
            pdf.cell(190, 8, txt=f"DNI: {cliente.get('dni')}", ln=True)
            pdf.cell(190, 8, txt=f"Email: {cliente.get('email')}", ln=True)
            pdf.cell(190, 8, txt=f"Vehículo: {vehiculo.get('marca')} {vehiculo.get('modelo')} ({vehiculo.get('matricula')})", ln=True)
            pdf.ln(5)
            
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(190, 10, txt="  DESGLOSE DE COSTES", ln=True, fill=True) 
            
            pdf.set_font("Arial", size=11)
            pdf.cell(120, 8, txt="Base Imponible:", border=0)
            pdf.cell(70, 8, txt=f"{detalle.get('base_imponible')} EUR", border=0, ln=True, align='R')
            
            pdf.cell(120, 8, txt="IVA aplicado:", border=0)
            pdf.cell(70, 8, txt=f"{detalle.get('iva')} EUR", border=0, ln=True, align='R')
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(120, 10, txt="TOTAL REPARACIÓN:", border='T')
            pdf.cell(70, 10, txt=f"{detalle.get('total_siniestro')} EUR", border='T', ln=True, align='R')
            pdf.ln(5)

            pdf.set_text_color(50, 55, 112)
            pdf.cell(120, 8, txt="Abonado por Aseguradora:", border=0)
            pdf.cell(70, 8, txt=f"{detalle.get('pago_aseguradora')} EUR", border=0, ln=True, align='R')
            
            pdf.set_text_color(200, 0, 0)
            pdf.cell(120, 8, txt="A cargo del Cliente (Franquicia/Excesos):", border=0)
            pdf.cell(70, 8, txt=f"{detalle.get('pago_cliente')} EUR", border=0, ln=True, align='R')

            # 3. Guardar en archivo temporal y subir a S3
            with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf.output(tmp.name)
                file_name = f"factura_{siniestro_id}.pdf"
                with open(tmp.name, 'rb') as f:
                    s3.put_object(
                        Bucket=BUCKET_NAME,
                        Key=file_name,
                        Body=f,
                        ContentType='application/pdf',
                        ContentDisposition='inline'
                    )
                region = os.environ.get("AWS_REGION", "eu-west-1")
                pdf_url = f"https://{BUCKET_NAME}.s3.{region}.amazonaws.com/{file_name}"
            print(f"Documento {file_name} generado y subido a S3.")

            
            # 4. Actualización de base de datos
            try:
                conn = psycopg2.connect(
                    host=DB_HOST, database=DB_NAME, 
                    user=DB_USER, password=DB_PASS,
                    port=DB_PORT
                )
                cur = conn.cursor()

                cur.execute(
                    """
                    UPDATE siniestros
                    SET url_documento = %s
                    WHERE id_siniestro = %s
                    """,
                    (pdf_url, siniestro_id)
                )

                conn.commit()
                cur.close()
                conn.close()
                print(f"DB actualizada para siniestro {siniestro_id}")
            except Exception as e:
                print(f"Error DB: {str(e)}")
            

        except Exception as e:
            print(f"Error procesando el registro: {str(e)}")
            continue

    return {
        'statusCode': 200,
        'body': json.dumps('Generación de PDF completada')
    }