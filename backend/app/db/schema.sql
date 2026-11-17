-- SmartHome Script 1.0 / Etapa 5
-- Esquema idempotente: no borra datos ni reinicia estados al arrancar.
CREATE TABLE IF NOT EXISTS dispositivos (
    identificador VARCHAR(80) PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('LED', 'LUZ', 'VENTILADOR', 'ALARMA', 'PUERTA')),
    estado VARCHAR(20) NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT estado_compatible_tipo CHECK (
        (tipo IN ('LED', 'LUZ', 'VENTILADOR') AND estado IN ('ENCENDIDO', 'APAGADO'))
        OR (tipo = 'ALARMA' AND estado IN ('ACTIVADA', 'DESACTIVADA'))
        OR (tipo = 'PUERTA' AND estado IN ('ABIERTA', 'CERRADA'))
    )
);

CREATE TABLE IF NOT EXISTS historial (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    instruccion TEXT NOT NULL,
    resultado TEXT,
    estado_ejecucion VARCHAR(20) NOT NULL CHECK (
        estado_ejecucion IN ('EXITOSA', 'ERROR', 'OMITIDA')
    ),
    fecha TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_historial_fecha ON historial (fecha DESC);

CREATE TABLE IF NOT EXISTS notificaciones (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mensaje TEXT NOT NULL CHECK (length(trim(mensaje)) > 0),
    fecha TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ON CONFLICT DO NOTHING preserva los estados almacenados en reinicios posteriores.
INSERT INTO dispositivos (identificador, tipo, estado) VALUES
    ('led1', 'LED', 'APAGADO'),
    ('luz_sala', 'LUZ', 'APAGADO'),
    ('ventilador1', 'VENTILADOR', 'APAGADO'),
    ('alarma1', 'ALARMA', 'DESACTIVADA'),
    ('puerta_principal', 'PUERTA', 'CERRADA')
ON CONFLICT (identificador) DO NOTHING;

-- Suscripciones opt-in de navegadores para Web Push.
-- No contiene contraseñas ni claves privadas VAPID.
CREATE TABLE IF NOT EXISTS push_suscripciones (
    endpoint TEXT PRIMARY KEY,
    p256dh TEXT NOT NULL,
    auth TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
