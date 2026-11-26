# Roles configurables por empresa (diseño)

Estado: **solo diseño** (D-066). No hay código de esto hasta que Jacobo lo apruebe. Se construye
después del bloque A de la tarea 011 (Formación).

## Por qué

Hoy los roles están fijos en la base: `dueno`, `encargada`, `finanzas`, `asesora`, `soporte`,
`lider` y `responsable_punto`, y cada política de permisos dice a mano qué roles pueden qué
(76 revisiones repartidas en 14 migraciones). Cada empresa organiza su gente distinto: en una la
coordinación evalúa pero no ve la caja; en otra la encargada sí cierra el día. Con roles fijos,
cada caso nuevo es una migración. Con roles configurables, la empresa arma sus roles y Tino solo
revisa **permisos**.

## El modelo

1. **Permisos fijos de Tino.** La lista la define Tino y no cambia por empresa. Es lo que la base
   revisa.
2. **Roles de cada empresa.** Un rol es un paquete de permisos con nombre ("Coordinación",
   "Jefe de tienda"…). La empresa crea, cambia y desactiva los suyos.
3. **Alcance por puntos, aparte del rol.** Un usuario tiene un rol y además un alcance: todos los
   puntos, o una lista de puntos. "Responsable de punto" = el rol que la empresa quiera, con
   alcance de un punto.
4. **Plantillas para arrancar:** Gerencia, Coordinación, Responsable de punto y Asesora. Al crear
   una empresa se copian a la empresa; desde ahí son suyas.
5. **"Ver como" otro rol:** solo para mirar (nada se guarda), solo para quien tenga el permiso
   `ver_como` (Gerencia y soporte) y queda en la auditoría.

## Permisos propuestos

Salen de lo que hoy existe. "Ver" respeta el alcance por puntos.

| Permiso | Qué deja hacer | Hoy lo tienen |
|---|---|---|
| `ver_ventas` | Ventas, venta por persona, metas, ranking | dueño, encargada, finanzas, soporte, líder; asesora y responsable (su punto) |
| `ver_caja` | Días, reportes de caja, pagos, movimientos, cierres | dueño, encargada, finanzas, soporte; asesora y responsable (su punto) |
| `ver_conciliacion` | Bancos, extractos, conciliación, transferencias, descuadres | dueño, encargada, finanzas, soporte |
| `ver_acompanamiento` | Observaciones, evaluaciones, compromisos, sesiones, registro del día, ciclo | dueño, encargada, líder, soporte; responsable (su punto) |
| `ver_auditoria` | La auditoría | dueño, soporte |
| `ver_usuarios` | La lista de usuarios | dueño, encargada, soporte |
| `subir_archivos` | Importar archivos, la cola de la web, resolver nombres y productos | dueño, encargada, finanzas, soporte |
| `registrar_caja` | Lo del día en caja: reportes, pagos, movimientos, observaciones de caja | dueño, encargada, finanzas, soporte; asesora (su punto) |
| `cerrar_dia` | Cerrar el día | dueño, encargada; asesora y responsable (su punto) |
| `desbloquear_dia` | Reabrir un día cerrado, con nota | dueño, encargada |
| `confirmar_conciliacion` | Confirmar o rechazar propuestas y causas de descuadre | dueño, encargada, finanzas, soporte |
| `registrar_acompanamiento` | Observación, compromiso, evaluación, diagnóstico, sesión | dueño, encargada, líder, soporte; responsable (su punto) |
| `registrar_dia` | El registro del día por persona | dueño, líder; responsable (su punto) |
| `cambiar_paso` | El paso del ciclo de formación de una persona | dueño, encargada, líder, soporte; responsable (su punto) |
| `gestionar_personas` | Crear y editar personas, asignarlas a puntos, alias | dueño, encargada, líder, soporte |
| `poner_metas` | Metas por punto y por persona | dueño, encargada, líder, soporte |
| `ajustes_equipo` | Catálogo de Equipo, indicadores, etapas, umbrales, plantilla | dueño, encargada, líder, soporte |
| `ajustes_empresa` | Configuración de la empresa, palabras, perfiles de fuente, puntos | dueño, soporte |
| `gestionar_usuarios` | Crear usuarios, darles rol y alcance, desactivarlos | dueño, soporte |
| `gestionar_roles` | Crear y cambiar roles y sus permisos | (nuevo) dueño, soporte |
| `facturar` | Crear facturas en el programa de facturación (D-063, cuando exista) | (nuevo) dueño |
| `ver_como` | Mirar Tino como otro rol, sin guardar | (nuevo) Gerencia, soporte |

## Tablas

```
permiso            (codigo pk, nombre, descripcion, grupo)          -- catálogo fijo de Tino, sin empresa
rol                (id, empresa_id, nombre, descripcion, plantilla, sistema bool, activo, creado_en)
                   unique (empresa_id, nombre)
rol_permiso        (id, empresa_id, rol_id, permiso -> permiso.codigo, creado_en)
                   unique (rol_id, permiso)
usuario            + rol_id (fk a rol de su empresa), + alcance text check in ('todos', 'puntos')
usuario_punto      (id, empresa_id, usuario_id, punto_id, desde, hasta)   -- el alcance cuando es 'puntos'
ver_como           (id, empresa_id, usuario_id, rol_id, desde, hasta)     -- cada vez que alguien mira como otro
```

- Todas con `empresa_id`, RLS, auditoría, sin DELETE (un permiso se quita marcando el
  `rol_permiso` como anulado o, mejor, con una función que deja la fila histórica). `permiso` es
  un catálogo global de solo lectura, como `festivo`.
- `rol.sistema = true` solo para el rol de soporte: lo crea Tino, no se lista para el cliente.

## Cómo cambia `app.tiene_rol`

Hoy: `app.tiene_rol(array['dueno','encargada'])` compara el rol del usuario con una lista.

Después:

```sql
-- ¿El usuario de esta sesión tiene este permiso? (stable, security definer, set search_path = '')
app.tiene_permiso(p_permiso text) returns boolean
-- ¿Y lo tiene para este punto? Combina el permiso con el alcance (todos o sus puntos).
app.puede_en_punto(p_permiso text, p_punto uuid) returns boolean
```

- Las políticas pasan de `app.tiene_rol(array[...])` a `app.tiene_permiso('...')`, y las de
  "solo su punto" (`rol_actual() = 'responsable_punto' and p_punto = app.punto_actual()`) a
  `app.puede_en_punto('...', punto_id)`.
- Para no consultar las tablas fila por fila, los permisos del usuario se calculan una vez por
  petición y se guardan en una variable de la sesión (`set_config('app.permisos', ..., true)`).
- Con "ver como" activo, `tiene_permiso` responde con los permisos del rol que se mira **solo para
  ver**; todo permiso de escritura responde falso, así la base rechaza cualquier cambio aunque
  la pantalla fallara.
- `app.tiene_rol` y `app.rol_actual` se quedan mientras dure la migración, para que las 400+
  pruebas de hoy sigan pasando sin tocarlas.

## Plan de migración paso a paso

1. **0016 – tablas y equivalencia.** Crea `permiso` (la lista de arriba), `rol`, `rol_permiso`,
   `usuario_punto`, `ver_como` y las columnas nuevas de `usuario`. Para cada empresa crea **un
   rol por cada rol fijo de hoy** (Dueño, Encargada, Finanzas, Asesora, Líder, Responsable de
   punto y Soporte, este último de sistema) con exactamente los permisos de la tabla de arriba.
   Pasa a cada usuario a su rol equivalente y su `punto_id` a `usuario_punto`. Un trigger mantiene
   `usuario.rol` igual al rol equivalente mientras se migra. Nada cambia para nadie todavía.
2. **Prueba de equivalencia.** Una prueba nueva arma la "matriz" (cada usuario de prueba × cada
   tabla × ver/crear/cambiar) con las funciones viejas, y exige que la nueva dé lo mismo, celda
   por celda. Las 467 pruebas de hoy corren sin cambios.
3. **0017 – políticas por permiso.** Reescribe las políticas tabla por tabla con
   `tiene_permiso`/`puede_en_punto`. La prueba de equivalencia tiene que seguir en verde: es la
   garantía de que cada usuario ve exactamente lo mismo que antes.
4. **Web.** Marco carga los permisos del usuario; cada `["dueno", …].includes(yo.rol)` pasa a
   `puede("permiso")`. Sin cambios visibles.
5. **Pantalla de Roles** (Más → Roles, con `gestionar_roles`): lista de roles, permisos con
   interruptores agrupados (Ventas, Caja, Formación, Configuración), usar plantilla, y en
   Usuarios el alcance por puntos.
6. **"Ver como"** (con `ver_como`): una franja arriba "Está viendo como Coordinación · Salir",
   todo de solo lectura, con su fila en `ver_como` y en la auditoría.
7. **Retiro de lo viejo.** Cuando nada use `rol_actual`/`tiene_rol`, una migración final los
   deja como envoltorios de compatibilidad (no se borran de golpe).

## Cuidados

- **Nadie se queda sin acceso:** un trigger impide quitar `gestionar_usuarios` del último rol
  activo que lo tenga con al menos un usuario activo, desactivar al último usuario con ese
  permiso o cambiarle el rol. Error claro: "Tiene que quedar al menos una persona que administre
  usuarios".
- **Soporte invisible para el cliente:** el rol de sistema y sus usuarios no salen en las listas
  del cliente (RLS de `rol` y `usuario`), no se pueden editar ni asignar desde la empresa, y solo
  Tino crea usuarios de soporte.
- **Los permisos se revisan en la base (RLS)**, no solo en la pantalla: la web solo esconde
  botones.
- **Todo cambio queda auditado:** `rol`, `rol_permiso`, `usuario` (rol y alcance),
  `usuario_punto` y `ver_como` con el trigger de auditoría de siempre.
- **Lo que cada usuario ve no cambia con la migración:** la prueba de equivalencia lo exige.

## Pruebas nuevas

- Matriz de equivalencia: antes y después, cada usuario de prueba de las dos empresas × cada
  tabla × ver, crear y cambiar.
- Un rol nuevo con un solo permiso (por ejemplo `ver_ventas`) ve ventas y nada más.
- El alcance por puntos: con un punto, solo ese; con dos, esos dos.
- Último administrador: no se puede quitar `gestionar_usuarios` ni desactivarlo.
- Soporte: el cliente no ve ni edita el rol de sistema ni a sus usuarios.
- Ver como: lee lo del rol mirado, no puede escribir nada (todas las tablas), y deja auditoría.
- Otra empresa: no ve ni usa los roles de la primera.

## Riesgos

| Riesgo | Cómo se cuida |
|---|---|
| Al reescribir una política, alguien gana o pierde acceso sin querer | Prueba de equivalencia celda por celda antes de aplicar en pruebas y producción |
| Consultas más lentas (permisos por fila) | Permisos calculados una vez por petición en una variable de sesión; índices por `rol_id` |
| Una empresa se queda sin quién administre | Trigger del último administrador |
| "Ver como" deja escribir | Con ver como, todo permiso de escritura es falso en la base, no solo en la pantalla |
| Confusión del cliente con demasiados interruptores | Plantillas y permisos agrupados con nombres en español sencillo |

## Cuánto trabajo es

| Paso | Trabajo |
|---|---|
| 0016 tablas, equivalencia y matriz de pruebas | 1 a 1,5 sesiones |
| 0017 reescritura de políticas (76 revisiones) | 1 a 1,5 sesiones |
| Web: `puede()` en lugar de roles fijos | 0,5 sesiones |
| Pantalla de Roles y alcance en Usuarios | 1 sesión |
| Ver como | 0,5 a 1 sesión |
| **Total** | **4 a 5,5 sesiones** |
