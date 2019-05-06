drop table if exists item;

create table item (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 Kilometraje NUMERIC,
 Latitud NUMERIC,
 Longitud NUMERIC,
 TanqueConductor NUMERIC,
 TanquePasajero NUMERIC,
 Velocidad NUMERIC,
 Altitud NUMERIC,
 Fecha TEXT,
 Hora TEXT,
 Enviado INTEGER
);
