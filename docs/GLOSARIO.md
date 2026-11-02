# Glosario

Palabras con un significado preciso en este proyecto. Si una palabra se usa
distinto en el código, el código está mal.

| Palabra | Significado |
| --- | --- |
| Empresa | Un negocio cliente. Todo dato pertenece a una empresa. |
| Punto de venta | Un local de la empresa, incluida la bodega si existe. |
| Jornada | Un día de un punto de venta. Equivale a una hoja del Excel diario. |
| Asesora | Persona que vende en un punto. Nunca se borra; se desactiva. |
| Alias | Una forma en que aparece escrito un nombre de asesora o producto en los reportes. |
| Medio de pago | Efectivo, Bold, Redeban, transferencia, Daviplata, Nequi, etc. |
| Pago | Lo que el punto reporta que recibió, por medio de pago. |
| Movimiento externo | Lo que realmente llegó según una fuente externa: extracto, liquidación de datáfono o aviso por correo. |
| Conciliación | El cruce entre un pago reportado y uno o varios movimientos externos. |
| Propuesta | Una conciliación que el sistema sugiere pero que una persona debe confirmar. |
| Descuadre | Diferencia entre lo esperado y lo reportado en una jornada, para un medio de pago o en total. |
| Causa probable | La explicación que el sistema propone para un descuadre, con su confianza y sus pruebas. |
| Evidencia | Un registro concreto que sustenta una causa: un pago, un movimiento o una venta. |
| Verificación de transferencia | El seguimiento de una transferencia: comprobante, aviso del banco y extracto. |
| Sospechosa | Transferencia sin aviso del banco pasado el tiempo límite, o con comprobante repetido. |
| Perfil de fuente | La configuración que dice cómo leer un archivo de una empresa: qué columna es qué. |
| Archivo importado | Cada archivo que entra al sistema. Todo dato sabe de qué archivo y fila salió. |
| Día cerrado | Jornada que ya no se edita sin permiso de la encargada o el dueño. |
| Copiar como números | Copiar una tabla con enteros puros, sin `$` ni puntos, para pegar en Excel. |
| Fuente de verdad | Supabase. Si algo no está en la base, no existe para el sistema. |
| Laboratorio | Milagros: datos reales usados con permiso para construir y probar. |
