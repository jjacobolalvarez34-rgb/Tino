# Programas de facturación en Colombia y sus API

Investigado el 13 nov 2026 en las páginas oficiales de cada uno. Sirve para traer las
facturas a Tino sin que nadie exporte un Excel de Siigo a mano. Lo que no se pudo
confirmar en la documentación oficial va marcado "sin confirmar".

## Cuáles se usan

Siigo y Alegra son los más usados por pymes en Colombia. World Office, Loggro y Helisa
vienen después. Los cinco emiten factura electrónica ante la DIAN.

## Resumen

| Programa | ¿API para leer facturas? | Cómo se entra | Lo que hay que saber |
| --- | --- | --- | --- |
| Siigo Nube | Sí, `GET https://api.siigo.com/v1/invoices` | `POST /auth` con `username` y `access_key` → token de 24 h; cada petición lleva `Authorization: Bearer` y `Partner-Id` | El usuario y la llave salen de Siigo Nube → Alianzas → "Mi credencial API". Desde mayo de 2025 el `Partner-Id` tendría que ser de una aplicación registrada en Siigo (sin confirmar). Límite de peticiones sin confirmar (una librería usa 100 por minuto). |
| Alegra | Sí, `GET https://api.alegra.com/api/v1/invoices` | Correo y token, con autenticación básica | Máximo 30 facturas por página (`start`, `limit`). Filtros por fecha (`date_after`, `date_before`) y estado. |
| World Office Cloud | Sí, API REST | Token generado en la aplicación, en el encabezado con prefijo `WO` | Solo en el plan Enterprise. |
| Loggro | Sí: documentos electrónicos por fecha y detalle de ventas por línea | Token del servicio de login | Hay dos API: Enterprise/Pymes (`api.loggro.com`) y POS de restaurantes (`api.pirpos.com`). |
| Helisa | No se encontró API pública | — | Habría que seguir con la exportación a Excel. |

## Siigo, en detalle

- Facturas de venta: `GET /v1/invoices`. Filtros: `date_start`/`date_end` (fecha de la
  factura), `created_start`/`created_end`, `updated_start`/`updated_end`, `name`
  (FV-003-457), `customer_identification`, `document_id`. Páginas con `page` y
  `page_size`; la respuesta trae `pagination.total_results` y enlaces `next`.
- Cada factura trae: `id`, `prefix`, `number`, `name`, `date`, `customer`, `seller`,
  `cost_center`, `total`, `balance`, `observations`, `annulled`, `retentions`,
  `items` (código, descripción, cantidad, precio, descuento, impuestos, **bodega**),
  `payments` (medio de pago y valor) y `stamp` (estado DIAN, CUFE).
- También hay notas crédito (`/credit-notes`), recibos de caja (`/vouchers`), compras,
  productos y clientes.
- Para Tino: `seller` (la asesora), `items.warehouse` o `cost_center` (el punto, según
  cómo lo tenga configurado cada empresa), `payments` (efectivo, tarjeta,
  transferencia) y `annulled`. Qué campo dice el punto va en el `perfil_fuente` de la
  empresa, no en el código.

## Siigo: qué deja hacer la API (revisado el 20 nov 2026)

No es solo de lectura. Según developers.siigo.com se puede **crear, editar, anular y borrar**
facturas de venta (y bajar su PDF o mandarla por correo); crear notas crédito, recibos de caja y
comprobantes contables; crear y editar compras, cotizaciones, documentos soporte, pagos, clientes y
productos; leer informes (balance de prueba, cartera); y suscribirse a **webhooks** (avisos al
instante, un tema por suscripción). Límite: 100 peticiones por minuto por empresa (10 en la de
pruebas). `Partner-Id` = nombre de la aplicación, 3 a 100 letras o números, sin registro previo.
Tino solo lee (D-062). Ver docs/PLAN.md §2 con lo encontrado en octubre.

## Cómo encaja en Tino

- Un conector por programa, todos con la misma salida: la factura normalizada (fecha,
  número, punto, asesora, ítems, pagos, anulada) en pesos enteros, con su id de origen.
  Así el resto de Tino no sabe de qué programa vino.
- Las credenciales de cada empresa nunca van en el repositorio ni en el `.exe`. Se
  guardan en el servidor (una función de Supabase con la llave guardada en Vault) o, en
  la fase del `.exe`, en un archivo de la empresa fuera del repositorio.
- Se trae por rango de fechas y se repite sin duplicar: el id de la factura en el
  programa de origen es la clave.
- Las facturas anuladas no se borran en Tino: quedan anuladas (D-005).

## Lo que falta decidir o conseguir

- En Milagros el punto sale del **prefijo** o del **centro de costo** (uno por punto); la bodega de los
  ítems no sirve (varias por punto). Las credenciales ya funcionan (20 nov 2026).

## Fuentes

- Siigo: [Introducción](https://developers.siigo.com/docs/siigoapi/), [Listar facturas](https://developers.siigo.com/docs/siigoapi/invoice/3-get-invoices), [Autenticación](https://siigoapi.docs.apiary.io/), [Portal de clientes](https://siigonube.portaldeclientes.siigo.com/informacion-siigo-api/)
- Alegra: [Información general](https://developer.alegra.com/docs/informaci%C3%B3n-general), [Listar facturas](https://developer.alegra.com/reference/get_invoices), [Proveedor electrónico](https://e-provider-docs.alegra.com/docs/autenticaci%C3%B3n)
- World Office: [API](https://developer.worldoffice.cloud/), [Guía](https://developer.worldoffice.cloud/guiaInterfaz.html)
- Loggro: [Documentos electrónicos por fecha](https://developer.loggro.com/reference/documentosexternosfe), [Detalle de ventas](https://developer.loggro.com/reference/consultarventasdetalladaspymes)
- Comparativas: [Guía de software 2026](https://www.guiadesoftware.com/blog/mejor-software-contabilidad-colombia), [Apideck Colombia](https://www.apideck.com/integrations/country/colombia)
