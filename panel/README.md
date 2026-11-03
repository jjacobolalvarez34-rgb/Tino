# panel

Las pantallas para dueños, encargadas y finanzas. Primero dentro del `.exe`, con
HTML, CSS y JavaScript sobre Python (D-023). Después en la web, con Next.js y
TypeScript en Vercel.

Estado: `revision/` arma la revisión de la mañana de un día: transferencias y tarjetas
anotadas contra el banco y los datáfonos, y el descuadre con su causa. `tablero/` arma el tablero de ventas con tarjeta en un solo HTML, desde los
reportes de Bold y Redeban. El HTML lleva datos del cliente: se guarda fuera del
repositorio. Las demás pantallas se construyen cuando exista `tino-pruebas`.

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
