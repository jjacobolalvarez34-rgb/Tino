# Producción

tino-produccion es donde viven los datos de uso diario. tino-pruebas sigue siendo el laboratorio
(D-054). Ninguno va a demos, capturas ni al repositorio.

## 1. Lo que hace Jacobo (sin pegar secretos en el chat)

1. **Proyecto:** organización nueva en Supabase → proyecto **tino-produccion**, región
   South America (São Paulo). Hecho el 19 nov 2026.
2. **Archivo de llaves**, fuera del repositorio: `D:\Repositorios\Tino-datos\produccion.json`
   ```
   {"url": "https://xxxx.supabase.co",
    "llave_publica": "sb_publishable_…",
    "llave_servicio": "sb_secret_…",
    "conexion": "postgresql://postgres.xxxx:CLAVE@aws-0-sa-east-1.pooler.supabase.com:5432/postgres"}
   ```
   - `url` y `llave_publica` ya están.
   - `llave_servicio`: Project Settings → API Keys → **Secret key**.
   - `conexion`: botón **Connect** → **Session pooler** → URI, con la clave de la base en lugar de
     `[YOUR-PASSWORD]`.
3. **Vercel** (proyecto `tino`, Settings → Environment Variables). Cada variable se pone por
   ambiente:

   | Variable | Production | Preview |
   |---|---|---|
   | `NEXT_PUBLIC_SUPABASE_URL` | la de tino-produccion | la de tino-pruebas |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | publishable de producción | anon de pruebas |
   | `SUPABASE_SERVICE_ROLE_KEY` | secret de producción | service_role de pruebas |

   La tercera **no** lleva `NEXT_PUBLIC_`: así nunca llega al navegador. La usa solo la pantalla
   Usuarios. Después de cambiarlas: Deployments → Redeploy.
4. **Auth de Supabase en producción:** Authentication → URL Configuration → Site URL = la
   dirección de Vercel, y en Redirect URLs agregar `https://<dirección>/clave`. Sin esto, el enlace
   de "Invitar" o "Recuperar clave" no vuelve a Tino.
5. **Correos:** el correo que trae Supabase de fábrica solo manda unos pocos por hora y es para
   pruebas. Para invitar de verdad hay que poner un SMTP propio (Authentication → Emails → SMTP),
   por ejemplo el correo de Mamut Herd o un servicio como Resend. Decisión de Jacobo.

## 2. Lo que hace Claude cuando el archivo esté completo

En este orden, todo desde este computador y en D:

```
python tests/produccion/aplicar_migraciones.py D:/Repositorios/Tino-datos/produccion.json
python ingesta/maestros.py <maestros de Milagros, fuera del repo> --produccion D:/Repositorios/Tino-datos/produccion.json
python ingesta/maestros.py <…> --produccion <…> --aplicar
```
- Crear el acceso del dueño de Milagros en producción (sin invitar a nadie) y guardar su clave en
  `Tino-datos`.
- Poner el perfil de venta por persona y cargar octubre de los 11 puntos (`cargar_octubre.py produccion`).
- Comparar totales punto por punto con pruebas:
  `python tests/produccion/comparar_totales.py <pruebas.json> <usuario> <produccion.json> <usuario> 2026-10`
- Primer respaldo y prueba de restauración (sección 3).

`aplicar_migraciones.py` aplica cada migración en su propia transacción, se niega a tocar una base
que ya tiene tablas de Tino (salvo `--desde 0013`) y al final corre `tests/produccion/verificar.sql`:
RLS en todas las tablas, empresa_id, ninguna política de borrar, sin TRUNCATE, funciones y vistas
con los permisos de quien consulta, y auditoría. Probado el 20 nov 2026 en una base local nueva:
0001 a 0012 aplicadas y las 6 verificaciones en verde.

## 3. Respaldos (propuesta: Jacobo decide antes de pagar nada)

| Opción | Qué da | Costo al mes | Contras |
|---|---|---|---|
| A · Supabase Pro | Respaldo diario automático, 7 días hacia atrás, restaurar desde el panel. Además el proyecto no se pausa | ~25 USD (por organización) | Si se borra la organización o la cuenta, se van con ella |
| B · Copia propia nocturna | `pg_dump` cada noche (GitHub Actions o este PC), cifrada, guardada fuera de Supabase | 0 USD (minutos gratis de GitHub) | Hay que cuidar la llave de cifrado; este PC no siempre está prendido |
| C · A + B (recomendada) | Lo diario de Supabase y una copia semanal fuera de Supabase | ~25 USD | — |

Point-in-time recovery (volver a cualquier minuto) es un adicional de Supabase desde ~100 USD al
mes: no hace falta al empezar.

**Herramienta ya lista y probada:** `tests/respaldo/respaldar.py`
- `respaldar <produccion.json> D:/Repositorios/Tino-datos/respaldos`: copia los esquemas de Tino
  (`public` y `app`) y los ids de los accesos.
- `restaurar <archivo.dump> <base local nueva>`: lo restaura en el Postgres local.
- `comparar <origen> <restaurada>`: cuenta filas tabla por tabla.

**Prueba de restauración del 20 nov 2026** (con la base local de laboratorio): respaldo de 5,9 MB,
restaurado en una base nueva, **44 tablas y 103.825 filas, exactamente iguales**. Falta repetirla
contra producción cuando esté `conexion`. Ojo: el `pg_dump` de este PC es versión 16; si el
servidor de Supabase es más nuevo (17), hay que usar un `pg_dump` 17 (portable, en D:) o hacer la
copia desde GitHub Actions.

## 4. Vercel para uso comercial

Sí: el plan gratis de Vercel (Hobby) es solo para uso personal, **no comercial**. Para cobrarle a
clientes hay que pasar a **Vercel Pro** (~20 USD por miembro al mes). Con un solo miembro (Jacobo)
son ~20 USD.

Costos fijos estimados con la opción C: ~45 USD al mes (Supabase Pro + Vercel Pro), más el dominio.
Ver también docs/NEGOCIO/precios.md.
