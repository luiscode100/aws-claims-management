-- CREATE USER admingestor WITH PASSWORD 'admingestor';

CREATE TABLE siniestros (
    id_siniestro SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    dni VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    matricula VARCHAR(20) NOT NULL,
    marca VARCHAR(50) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    anio INT,
    informacion_poliza VARCHAR(50) NOT NULL,
    limite DECIMAL(10,2),
    franquicia DECIMAL(10,2),
    taller VARCHAR(100),
    mano_obra DECIMAL(10,2),
    piezas DECIMAL(10,2),
    estado_reparacion VARCHAR(50) DEFAULT 'Pendiente de estimación',
    url_documento VARCHAR(255),
    total_coste DECIMAL(10,2),
    pago_aseguradora DECIMAL(10,2),
    pago_cliente DECIMAL(10,2)
);

-- INSERT INTO siniestros (
-- 	nombre, dni, email, matricula, marca, modelo, anio, informacion_poliza, limite, franquicia, taller, mano_obra, piezas, estado_reparacion
-- )
-- VALUES
-- ('Juan', '2343454D', 'angel@mail.com', '4859NNF', 'toyota', 'avensis', 1996, 'basica', 20.0, 10.0, 'taller', 20.1, 0.0, 'pendiente');
