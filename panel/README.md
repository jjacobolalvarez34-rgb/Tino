# panel

El panel web para dueños, encargadas y finanzas. Next.js con TypeScript, en Vercel.

Estado: vacía. El proyecto de Next.js todavía no se ha creado.

## Reglas

- Solo tokens y componentes de `docs/DESIGN.md`.
- Antes de construir una pantalla, se abre en `docs/pantallas/demo.html` y se lee
  lo que no puede faltar en `docs/pantallas/README.md`.
- Lee las vistas `v_*`, con la sesión del usuario, para que RLS aplique. La llave
  de servicio nunca llega al navegador.
- Ninguna pantalla carga más datos de los que muestra. Meta: abre en menos de 2
  segundos en un celular.
- "Copiar como números" entrega enteros sin `$` ni puntos, separados por tabulación.

## Leer antes

`docs/DESIGN.md`, `docs/pantallas/README.md` y `docs/MODELO_DATOS.md` (roles y
permisos).
