# 008 · Publicar la web en Vercel

Estado: código listo en `web/` (13 nov 2026); falta publicar.

## Objetivo

Que Jacobo y la dueña abran Tino desde el navegador o el celular, con las mismas
pantallas y la misma base que el `.exe`.

## Alcance

- Crear el proyecto en Vercel con raíz `web/` y las dos variables públicas de Supabase
  (ver `web/README.md`).
- Poner la dirección de Vercel como Site URL en Supabase y apagar el registro abierto.
- Después: subir archivos desde la web. Dos caminos: llevar los lectores a TypeScript, o
  una función de servidor en Python (Vercel lo permite) que reuse `ingesta/`.

## Hecho cuando

- Con el usuario de Milagros, la web muestra en septiembre las mismas transferencias que no
  llegaron y los mismos descuadres que el `.exe`.
- Asignar un pago sin origen en la web lo deja asignado también en el `.exe`.

## Cómo lo reviso yo (Jacobo)

Abro la dirección de Vercel en el celular, entro y comparo Inicio con el `.exe`.
