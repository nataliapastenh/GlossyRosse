-- Creación de la base de datos (ejecutar si no existe)
-- CREATE DATABASE glossy_rosse_db;

-- Tabla de Administradores
CREATE TABLE administradores (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Encriptada con bcrypt
    banco_nombre VARCHAR(100),
    banco_tipo_cuenta VARCHAR(50),
    banco_numero_cuenta VARCHAR(50),
    banco_rut VARCHAR(20)
);

-- Tabla de Clientes
CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    rut VARCHAR(20) UNIQUE NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    telefono VARCHAR(25) NOT NULL,
    sancionado_hasta TIMESTAMP DEFAULT NULL -- Control RF10 (sanción 1 semana)
);

-- Tabla de Servicios
CREATE TABLE servicios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    precio INT NOT NULL,
    duracion_minutos INT NOT NULL DEFAULT 60
);

-- Tabla de Disponibilidad de Horarios del Administrador
CREATE TABLE disponibilidades (
    id SERIAL PRIMARY KEY,
    fecha_hora TIMESTAMP UNIQUE NOT NULL,
    disponible BOOLEAN DEFAULT TRUE
);

-- Tabla de Reservas
CREATE TABLE reservas (
    id SERIAL PRIMARY KEY,
    reserva_codigo VARCHAR(20) UNIQUE NOT NULL,
    cliente_id INT REFERENCES clientes(id) ON DELETE CASCADE,
    servicio_id INT REFERENCES servicios(id) ON DELETE RESTRICT,
    fecha_hora TIMESTAMP NOT NULL,
    estado VARCHAR(20) DEFAULT 'Confirmada', -- 'Confirmada', 'Modificada', 'Cancelada'
    contador_modificaciones INT DEFAULT 0, -- Control RF09 (máximo 3 modificaciones)
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar datos iniciales de ejemplo (Servicios y Administrador)
INSERT INTO servicios (nombre, precio, duracion_minutos) VALUES
('Esmaltado Permanente', 14000, 120),
('Nivelación/Kapping', 18000, 120),
('Soft Gel', 20000, 120),
('Pedicure', 17000, 90),
('Retiro', 4000, 20),
('Pestañas: Volumen Tecnológico 3D', 20000, 180),
('Pestañas: Volumen Tecnológico 4D', 22000, 180),
('Pestañas: Volumen Tecnológico 5D', 24000, 180),
('Pestañas: Volumen Tecnológico 6D', 26000, 180),
('Pestañas: Retiro', 4000, 20),
('Limpieza Facial Básica', 20000, 90),
('Limpieza Facial Peeling', 23000, 90),
('Limpieza Facial Ultrasonic Glow', 23000, 90),
('Limpieza Facial Peeling Enzimático', 23000, 90),
('Limpieza Facial Trilogía de Peeling', 25000, 90),
('Botox Capilar', 20000, 180),
('Alisado Progresivo Hakari', 25000, 180);

-- Contraseña inicial para 'martina' (contraseña de prueba: admin123)
INSERT INTO administradores (username, password_hash, banco_nombre, banco_tipo_cuenta, banco_numero_cuenta, banco_rut) 
VALUES ('martina', '$2b$12$LQv3c1yqSNWvwd8n35m3vuhQoD.c8UqM4e9g9mO6x0X4K3nE2FmO2', 'Banco Estado', 'CuentaRUT', '12345678-9', '12345678-9');

-- 1. Vincular disponibilidades con administradores
ALTER TABLE disponibilidades
ADD COLUMN administrador_id INT REFERENCES administradores(id) ON DELETE SET NULL;

-- 2. Vincular reservas con el bloque de disponibilidad tomado
ALTER TABLE reservas
ADD COLUMN disponibilidad_id INT REFERENCES disponibilidades(id) ON DELETE RESTRICT;

ALTER TABLE disponibilidades
ADD COLUMN IF NOT EXISTS administrador_id INT REFERENCES administradores(id) ON DELETE SET NULL;

ALTER TABLE reservas
ADD COLUMN IF NOT EXISTS disponibilidad_id INT REFERENCES disponibilidades(id) ON DELETE RESTRICT;

