# Subir archivos desde la web (bloque E): dos caminos

Hoy los lectores (Excel del día, extracto del banco en PDF o .zip, Bold y Redeban) están en
Python, en `ingesta/` y `motores/conciliador/`. La web es Next.js en Vercel (D-042). Para subir
desde el celular hay dos caminos razonables; elige Jacobo.

## A · Una función de Python en Vercel (recomendado)

La web manda el archivo a `/api/subir` y una función de Python en el mismo proyecto de Vercel
corre exactamente los mismos lectores de hoy (`cargar.preparar` y `cargar.subir`, con la sesión de
quien sube, así RLS sigue decidiendo). Vercel lo permite junto a Next.js (como su plantilla
"Next.js + FastAPI").

- **A favor:** un solo lector (el mismo del .exe), mismas pruebas, mismo aviso de archivo
  repetido y "Deshacer" de siempre; funciona desde el celular sin nada prendido en la oficina.
- **En contra:** la compilación tiene que copiar `ingesta/`, `motores/` y `panel/datos/` dentro de
  `web/` y llevar sus dependencias (openpyxl, el lector de PDF); el plan de Vercel limita el tamaño
  de la función (~250 MB) y el tiempo (60 s en Pro; un Excel de un mes tarda ~1–2 min en este PC:
  hay que medirlo allá y quizá leer solo la hoja nueva). Hay que probarlo en una vista previa de
  Vercel antes de producción.

## B · Subir a Supabase y procesar después

La web guarda el archivo en Supabase Storage (carpeta por empresa, con RLS) y lo deja "en cola".
El programa de escritorio (o un proceso programado) lo procesa con los lectores de Python y la
pantalla Archivos muestra "en cola → cargado" o el error.

- **A favor:** no depende de los límites de Vercel; los archivos originales quedan guardados.
- **En contra:** alguien tiene que procesar la cola (el PC prendido o un servidor aparte); desde el
  celular no se ve el resultado al instante.

## Lo que no cambia en ninguno

Aviso de archivo repetido (por su huella sha256), "Deshacer" que no borra, errores por resolver en
Archivos y nada de datos reales en el repositorio.
