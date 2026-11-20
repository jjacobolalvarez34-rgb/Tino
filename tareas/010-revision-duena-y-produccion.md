# 010 · Revisión de la dueña y paso a producción

Paso del plan: antes de dar acceso a la dueña
Estado: en curso

## Objetivo
Corregir lo que encontró la revisión en tino-pruebas y después pasar a producción, para que la
dueña de Milagros pueda entrar a Tino con sus datos de verdad.

## Alcance
- A · Correcciones (punto 02, día 1, nombres, hora de Bogotá, comparación, ticket, meses, capturas).
- B · Resolver nombres y productos en la web.
- C · tino-produccion, respaldos, Vercel por ambiente.
- D · Pantalla de Usuarios (sin invitar a nadie).
- E · Subir archivos desde la web (puede ir después).
- F · Página /precios.

## Fuera de alcance
Indicadores comerciales por asesora, lector de correos, Siigo automático, otros bancos, app de
asesoras, sin internet, cobros en línea.

## Hecho cuando
1. ⏳ En producción, octubre de los 11 puntos cuadra con los Excel. Listo para correr
   (aplicar_migraciones.py, maestros --produccion, cargar_octubre produccion, comparar_totales);
   espera llave_servicio y conexion en produccion.json.
2. ⏳ La venta sin asesora solo tiene nombres de verdad ambiguos y se resuelven desde la web.
   Construido (Por resolver, 0012); espera 0012 en tino-pruebas para recargar.
3. ✅ Fechas en hora de Bogotá; comparación y ticket correctos.
4. ✅ Crear un usuario con rol dueño sin invitarlo (probar_usuarios_api.py, 12 de 12).
   En Vercel falta la variable SUPABASE_SERVICE_ROLE_KEY.
5. ⏳ Subir un Excel del día desde el celular: Jacobo elige el camino A o B
   (docs/OPERACION/subir-desde-la-web.md).
6. ⏳ Respaldo propuesto ✅ y restauración probada en local ✅; falta repetirla contra producción.
7. ✅ /precios se ve bien en celular y computador sin iniciar sesión (capturas enviadas).
8. ✅ Pruebas en verde.

## Cómo lo reviso yo (Jacobo)
- docs/OPERACION/produccion.md: los pasos que me tocan y los que corre Claude.
- Capturas en D:\Repositorios\Tino-datos\capturas (empresa demo, datos inventados).

## Notas
Decisiones D-053 a D-056. Bitácora del 20 nov 2026.
