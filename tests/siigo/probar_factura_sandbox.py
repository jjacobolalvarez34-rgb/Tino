# -*- coding: utf-8 -*-
"""Crea UNA factura de prueba en la EMPRESA DE PRUEBAS de Siigo y la vuelve a mandar con la misma
llave para comprobar que no se duplica. Nunca en la cuenta de un cliente: cada factura ahí sería real
ante la DIAN.

Candados: el archivo de credenciales debe decir "empresa_de_pruebas": true, no puede ser el mismo
usuario de D:/Repositorios/Tino-datos/siigo.json (el de Milagros), y hay que pasar --si-es-de-pruebas.

Uso: python tests/siigo/probar_factura_sandbox.py <siigo_pruebas.json fuera del repo> <perfil.json> --si-es-de-pruebas
     perfil.json = el perfil de facturación (ver ingesta/siigo_facturar.py) con ids de esa empresa,
     y "venta_de_prueba": una venta con productos que existan en esa empresa de pruebas.
"""
import datetime as dt
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ingesta import siigo  # noqa: E402
from ingesta import siigo_facturar as sf  # noqa: E402


def main():
    if "--si-es-de-pruebas" not in sys.argv:
        raise SystemExit("Falta --si-es-de-pruebas: esta prueba crea una factura.")
    cred = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if cred.get("empresa_de_pruebas") is not True:
        raise SystemExit('Las credenciales no dicen "empresa_de_pruebas": true. No se crea nada.')
    cliente = Path("D:/Repositorios/Tino-datos/siigo.json")
    if cliente.exists() and json.loads(cliente.read_text(encoding="utf-8")).get("usuario") == cred.get("usuario"):
        raise SystemExit("Ese es el Siigo de un cliente, no la empresa de pruebas. No se crea nada.")
    perfil = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    venta = dict(perfil.pop("venta_de_prueba"), id=str(uuid.uuid4()))
    s = siigo.Siigo(cred["usuario"], cred["llave"], cred.get("partner_id", "Tino"))
    hoy = dt.date.today().isoformat()
    primera = sf.facturar(s, venta, dict(perfil, enviar_dian=False, enviar_correo=False), hoy)
    print("creada:", primera)
    segunda = sf.facturar(s, venta, dict(perfil, enviar_dian=False, enviar_correo=False), hoy)
    print("otra vez con la misma venta:", segunda)
    print("OK, no se duplicó." if segunda["id"] == primera["id"] else "FALLÓ: Siigo creó otra factura.")
    sys.exit(0 if segunda["id"] == primera["id"] else 1)


if __name__ == "__main__":
    main()
