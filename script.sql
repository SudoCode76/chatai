drop database chatai;
CREATE DATABASE chatai;

USE chatai;


CREATE TABLE informacion (
    id INT AUTO_INCREMENT PRIMARY KEY, -- Clave primaria autoincremental
    nombre VARCHAR(100),               -- Longitud especificada
    nombreLargo VARCHAR(255),          -- Longitud especificada
    caedec INT,                          -- Nombre de columna corregido
    descripcion TEXT                   -- Usar TEXT para descripciones largas es a menudo mejor
);


select * from informacion;