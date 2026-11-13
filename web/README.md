# Tino en la web

Las mismas pantallas del programa de escritorio, para abrir desde cualquier navegador
(también el celular). Next.js con TypeScript, sobre la misma base de Supabase.

## Qué hace

- Entrar con correo y clave (Supabase Auth). Cada consulta va con la sesión de quien
  entra: RLS decide qué ve y qué cambia. La llave de servicio nunca llega aquí.
- Inicio (lo que necesita atención), Transferencias, Sin origen (asignar con nota),
  Por confirmar, Descuadres (pruebas y cierre con nota), Archivos (historial y deshacer)
  y Puntos de venta.
- La revisión del día corre aquí mismo, con el núcleo de `motores/nucleo_ts`:
  `lib/revision.ts` da exactamente lo mismo que la versión en Python
  (`tests/web/comparar_revision.ts`).

Todavía no hace: subir archivos (los lectores de Excel y PDF son Python; por ahora se
suben desde el `.exe`), la conexión con Siigo y los ajustes de datáfonos y códigos de pago.

## Subirla a Vercel (una vez)

1. En Vercel: **Add New → Project** y elegir el repositorio de Tino en GitHub.
2. **Root Directory:** `web`. El framework se detecta solo (Next.js).
3. **Environment Variables**, con los valores de Supabase → Project Settings → API:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (la pública, nunca la de servicio)
4. **Deploy.** Cada push a la rama elegida vuelve a publicar.
5. En Supabase → Authentication → URL Configuration, poner la dirección de Vercel
   como **Site URL**.

Antes de abrirla a clientes: apagar el registro abierto en Supabase (Authentication →
"Allow new users to sign up"), porque los usuarios los crea Tino, no cada persona.

## En este computador

Con la caché de npm y los temporales en D: (nada en C:):

```
set npm_config_cache=D:\Repositorios\Tino-datos\construir\npm-cache
set TEMP=D:\Repositorios\Tino-datos\trabajo\tmp
npm install
npm run revisar      # tipos
npm run build        # lo mismo que hace Vercel
npm run dev          # http://localhost:3000, con web/.env.local
```
