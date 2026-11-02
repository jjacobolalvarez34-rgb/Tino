# Fuentes de datos

Un archivo por tipo de fuente: `excel_diario.md`, `siigo.md`, `bancos.md`,
`datafonos.md` y `correos_notificacion.md`. Claude Code escribe el borrador
leyendo archivos de muestra; Jacobo lo corrige.

Lo que cambia entre empresas no va aquí: va en `perfil_fuente`, en la base.

## Plantilla

```markdown
# [Nombre de la fuente]

De dónde sale: [quién lo descarga, de qué sistema, cada cuánto]
Formato: [xlsx, csv, correo] · Codificación: [utf-8, latin-1] · Separador: [, ;]
Una fila es: [un pago, una venta, un abono…]

## Columnas

| Columna en el archivo | Campo en el sistema | Tipo | Ejemplo | Notas |
| --- | --- | --- | --- | --- |

## Variantes conocidas
- [formatos que cambian entre meses, puntos o empresas]

## Trampas
- [filas de totales, encabezados repetidos, fechas en texto, valores con $ o puntos]

## Archivo de muestra
`tests/casos/[fuente]/[archivo anonimizado]`
```
