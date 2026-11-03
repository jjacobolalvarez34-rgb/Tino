# -*- coding: utf-8 -*-
"""Núcleo de cálculo: la lógica que decide sobre la plata.

Implementa motores/CONTRATO.md. Solo pesos enteros, sin leer archivos ni base de
datos, y sin valores fijos: tolerancias y porcentajes llegan como parámetro.
La misma lógica vive en motores/nucleo_ts/. Si cambias algo aquí, cambia primero
el contrato y sus casos.
"""
import datetime as dt
import re
from itertools import combinations

# Por encima de esto, 100 × monto deja de ser exacto en TypeScript.
MAXIMO_PESOS = 90_000_000_000_000

# \Z y no $: en Python, $ también acepta un salto de línea al final.
_RE_PESOS = re.compile(r"^-?[0-9,]*[0-9](\.[0-9]+)?\Z", re.ASCII)
_RE_LINEA = re.compile(
    r"^(?P<fecha>[0-9]{4}/[0-9]{2}/[0-9]{2})\s+"
    r"(?P<tipo>PAGO QR|PAGO LLAVE)\s+"
    r"(?P<resto>.*)\Z", re.ASCII)
_RE_VALOR = re.compile(
    r"(-?[0-9.]*[0-9],[0-9]{3}(?:,[0-9]{3})*\.[0-9]{2}|-?[0-9]+\.[0-9]{2})\s*\Z", re.ASCII)
_RE_REFERENCIA = re.compile(r"\b([0-9]{7,10})\b", re.ASCII)

# Solo espacios ASCII: strip() sin argumento también quita otros, como el NBSP.
_ESPACIOS = " \t\n\r\f\v"


def a_pesos(texto):
    """Texto del valor -> pesos enteros, sin pasar por float."""
    if not _RE_PESOS.match(texto):
        return None
    negativo = texto.startswith("-")
    limpio = texto.lstrip("-").replace(",", "")
    entero, _, decimales = limpio.partition(".")
    pesos = int(entero)
    if decimales and decimales[0] >= "5":
        pesos += 1
    if pesos > MAXIMO_PESOS:
        return None
    return -pesos if negativo else pesos


def restar(a, b):
    """Empareja dos listas monto por monto, contando repeticiones."""
    e = emparejar(a, b)
    return {"sobran_a": e["sobran_a"], "sobran_b": e["sobran_b"]}


def emparejar(a, b):
    """Lo mismo que restar, y además dice qué ítem de b quedó con cada ítem de a."""
    pendientes = {}
    for item in b:
        pendientes.setdefault(item["monto"], []).append(item)
    parejas, sobran_a = [], []
    for item in a:
        grupo = pendientes.get(item["monto"])
        if grupo:
            parejas.append({"a": item, "b": grupo.pop()})
        else:
            sobran_a.append(item)
    sobran_b = [item for grupo in pendientes.values() for item in grupo]
    return {"parejas": parejas, "sobran_a": sobran_a, "sobran_b": sobran_b}


def parecidos(a, b):
    """¿Pudo ser un error de digitación? 35.900 vs 39.500, 36.900 o 3.590."""
    sa, sb = str(a), str(b)
    if sa == sb:
        return False
    if len(sa) == len(sb):
        if sorted(sa) == sorted(sb):
            return True
        return sum(1 for x, y in zip(sa, sb) if x != y) == 1
    return a * 10 == b or b * 10 == a


def sobrantes_vecinos(vecinos):
    """Lo que le sobra a los días vecinos. Usar el día entero daría falsos "llegó
    otro día" con montos que se repiten a diario."""
    ext_sobra, excel_sobra = [], []
    for v in vecinos:
        if not v["cubre"]:
            if v["tiene_excel"]:
                excel_sobra += v["anotado"]
            continue
        if not v["tiene_excel"]:
            ext_sobra += v["externo"]
            continue
        r = restar(v["anotado"], v["externo"])
        ext_sobra += r["sobran_b"]
        excel_sobra += r["sobran_a"]
    return {"ext_sobra": ext_sobra, "excel_sobra": excel_sobra}


def _a_otro_dia(pendientes, vecinos, donde, otro_dia):
    """Separa lo que aparece en un día vecino de lo que sigue sin aparecer."""
    sigue = restar(pendientes, vecinos)["sobran_a"]
    # Por id y no por monto: con montos repetidos, restar señalaría la fila equivocada.
    siguen = {i["id"] for i in sigue}
    otro_dia += [{"donde": donde, "monto": i["monto"], "id": i["id"]}
                 for i in pendientes if i["id"] not in siguen]
    return sigue


def cruzar(anotado, externo, ext_vecinos, excel_vecinos):
    """Lo anotado en el día contra lo externo (banco o datáfono)."""
    r = restar(anotado, externo)
    no_llegaron, no_anotadas = r["sobran_a"], r["sobran_b"]

    otro_dia = []
    if no_llegaron:
        no_llegaron = _a_otro_dia(no_llegaron, ext_vecinos, "externo_otro_dia", otro_dia)
    if no_anotadas:
        no_anotadas = _a_otro_dia(no_anotadas, excel_vecinos, "anotado_otro_dia", otro_dia)

    mal_digitadas = []
    for item in list(no_llegaron):
        par = next((x for x in no_anotadas if parecidos(item["monto"], x["monto"])), None)
        if par:
            mal_digitadas.append({"anotado": item, "externo": par})
            no_llegaron.remove(item)
            no_anotadas.remove(par)

    return {"no_llegaron": no_llegaron, "no_anotadas": no_anotadas,
            "otro_dia": otro_dia, "mal_digitadas": mal_digitadas}


def dia_habil_siguiente(fecha, festivos):
    d = dt.date.fromisoformat(fecha)
    while True:
        d += dt.timedelta(days=1)
        # weekday(): sábado = 5, domingo = 6. El viernes sí es día hábil.
        if d.weekday() < 5 and d.isoformat() not in festivos:
            return d.isoformat()


def bloques_deposito(fechas, festivos):
    """Agrupa días de venta por el día en que se consignan."""
    por_consignacion = {}
    for f in set(fechas):
        por_consignacion.setdefault(dia_habil_siguiente(f, festivos), []).append(f)
    return [{"consignacion": c, "dias": sorted(por_consignacion[c]),
             "grande": len(por_consignacion[c]) > 1}
            for c in sorted(por_consignacion)]


def coincide_deposito(banco, esperado, tolerancia, porcentajes):
    return any(abs(100 * banco - p * esperado) <= 100 * tolerancia for p in porcentajes)


def cruces_redeban(filas, tolerancia, max_cruce):
    """Filas que cuadran solas, y grupos que solo cuadran juntos porque el banco
    repartió el abono en dos fechas."""
    salida = [{**f, "coincide": abs(f["banco"] - f["esperado"]) <= tolerancia,
               "sin_datos": f["banco"] == 0 and f["esperado"] == 0,
               "cruzado": False, "cruza_con": []} for f in filas]

    grupos = {}
    for i, f in enumerate(salida):
        if not f["coincide"] and not f["sin_datos"]:
            grupos.setdefault((f["codigo"], f["franquicia"]), []).append(i)

    for indices in grupos.values():
        if len(indices) < 2:
            continue
        for n in range(2, min(max_cruce, len(indices)) + 1):
            for combo in combinations(indices, n):
                if any(salida[i]["cruzado"] for i in combo):
                    continue
                banco = sum(salida[i]["banco"] for i in combo)
                esperado = sum(salida[i]["esperado"] for i in combo)
                if abs(banco - esperado) <= tolerancia:
                    fechas = [salida[i]["fecha"] for i in combo]
                    for i in combo:
                        salida[i]["cruzado"] = True
                        salida[i]["cruza_con"] = list(fechas)
    return salida


def estado_dia(descuadre, causas, tolerancia_cuadra, porcentaje_explicado, reglas_sin_peso):
    """Las causas son hipótesis alternativas: cuenta la que más explica, no la suma."""
    magnitud = abs(descuadre)
    mayor = max((abs(c["monto"]) for c in causas
                 if c["monto"] != 0 and c["regla"] not in reglas_sin_peso), default=0)
    explicado = min(magnitud, mayor)
    if magnitud <= tolerancia_cuadra:
        estado = "cuadra"
    elif 100 * explicado >= porcentaje_explicado * magnitud:
        estado = "explicado"
    else:
        estado = "sin_explicar"
    signo = 1 if descuadre >= 0 else -1
    return {"estado": estado, "explicado": signo * explicado,
            "sin_explicar": descuadre - signo * explicado}


def leer_linea_transferencia(linea):
    """Una línea del movimiento de Bancolombia: PAGO QR o PAGO LLAVE."""
    m = _RE_LINEA.match(linea.strip(_ESPACIOS))
    if not m:
        return None
    valor = _RE_VALOR.search(m.group("resto"))
    if not valor:
        return None
    pesos = a_pesos(valor.group(1))
    if pesos is None:
        return None
    refs = _RE_REFERENCIA.findall(m.group("resto")[:valor.start()])
    return {"fecha": m.group("fecha").replace("/", "-"), "tipo": m.group("tipo"),
            "referencia": refs[0] if refs else None, "valor": pesos}


def punto_por_referencia(referencia, puntos):
    por_ultimos4 = {p["codigo"][-4:]: p["punto"] for p in puntos}
    return por_ultimos4.get(referencia[-4:])


def _redondear(a, b):
    """División entera redondeada. Nunca pasa por float."""
    if b == 0:
        return 0
    if a < 0:
        return -_redondear(-a, b)
    q, r = divmod(a, b)
    return q + 1 if 2 * r >= b else q


def _grupos(cobros, clave_de):
    """Agrupa cobros por una clave y suma lo que cada grupo lleva."""
    grupos = {}
    for c in cobros:
        clave = clave_de(c)
        if clave is None:
            continue
        g = grupos.setdefault(clave, {"clave": clave, "cobros": 0, "bruto": 0, "comision": 0,
                                      "retenciones": 0, "prestamo": 0, "neto": 0})
        # Una reversión resta plata, pero no es una venta.
        g["cobros"] += 1 if c["bruto"] >= 0 else 0
        for campo in ("bruto", "comision", "retenciones", "prestamo", "neto"):
            g[campo] += c[campo]
    for g in grupos.values():
        g["ticket_promedio"] = _redondear(g["bruto"], g["cobros"])
    return list(grupos.values())


def _por_bruto(grupos):
    return sorted(grupos, key=lambda g: (-g["bruto"], g["clave"]))


def _por_clave(grupos):
    return sorted(grupos, key=lambda g: g["clave"])


def _pico(grupos):
    """La clave de mayor bruto. Si empatan, la primera de la lista."""
    mejor = None
    for g in grupos:
        if mejor is None or g["bruto"] > mejor["bruto"]:
            mejor = g
    return mejor["clave"] if mejor else None


def _mediana(valores):
    orden = sorted(valores)
    n = len(orden)
    if n == 0:
        return 0
    if n % 2 == 1:
        return orden[n // 2]
    return _redondear(orden[n // 2 - 1] + orden[n // 2], 2)


def estadisticas_ventas(cobros):
    """Estadísticas descriptivas de cobros con tarjeta."""
    suma = _grupos(cobros, lambda c: "total")
    total = suma[0] if suma else {"cobros": 0, "bruto": 0, "comision": 0, "retenciones": 0,
                                  "prestamo": 0, "neto": 0, "ticket_promedio": 0}
    fechas = {c["fecha"] for c in cobros}
    totales = {k: v for k, v in total.items() if k != "clave"}
    totales.update(ticket_mediano=_mediana([c["bruto"] for c in cobros if c["bruto"] >= 0]), dias=len(fechas),
                   promedio_por_dia=_redondear(total["bruto"], len(fechas)))

    semana = [{"clave": i, "dias": 0, "cobros": 0, "bruto": 0, "promedio_por_dia": 0} for i in range(7)]
    for g in _grupos(cobros, lambda c: c["fecha"]):
        fila = semana[dt.date.fromisoformat(g["clave"]).weekday()]
        fila["dias"] += 1
        fila["cobros"] += g["cobros"]
        fila["bruto"] += g["bruto"]
    for fila in semana:
        fila["promedio_por_dia"] = _redondear(fila["bruto"], fila["dias"])

    por_dia = _por_clave(_grupos(cobros, lambda c: c["fecha"]))
    por_hora = _por_clave(_grupos(cobros, lambda c: c["hora"]))
    return {
        "totales": totales,
        "por_punto": _por_bruto(_grupos(cobros, lambda c: c["punto"])),
        "por_dia": por_dia,
        "por_dia_semana": semana,
        "por_hora": por_hora,
        "por_proveedor": _por_clave(_grupos(cobros, lambda c: c["proveedor"])),
        "por_franquicia": _por_bruto(_grupos(cobros, lambda c: c["franquicia"])),
        "sin_hora": sum(1 for c in cobros if c["hora"] is None),
        "dia_pico": _pico(por_dia),
        "hora_pico": _pico(por_hora),
    }


def _mismo_signo(a, b):
    return (a > 0 and b > 0) or (a < 0 and b < 0)


def causas_de_cruce(regla, cruce, descuadre):
    """Lo que no cuadró en un cruce, como causa o señal del descuadre del día.

    Una transferencia anotada que no llegó ya está sumada en la caja: no explica un
    faltante, pero sí un sobrante si se anotó dos veces.
    """
    salida = []

    def agregar(que, explica, total):
        es_causa = _mismo_signo(explica, descuadre)
        salida.append({"regla": regla, "que": que, "tipo": "causa" if es_causa else "senal",
                       "monto": explica if es_causa else 0, "total": total})

    if cruce["mal_digitadas"]:
        efecto = sum(p["anotado"]["monto"] - p["externo"]["monto"] for p in cruce["mal_digitadas"])
        agregar("mal_digitado", efecto, efecto)
    if cruce["no_anotadas"]:
        total = sum(i["monto"] for i in cruce["no_anotadas"])
        agregar("sin_anotar", -total if descuadre < 0 else 0, total)
    if cruce["no_llegaron"]:
        total = sum(i["monto"] for i in cruce["no_llegaron"])
        agregar("no_llego", total if descuadre > 0 else 0, total)
    return salida


def _contrarios(a, b):
    return (a > 0 and b < 0) or (a < 0 and b > 0)


def causa_compensacion(descuadre, vecinos, monto_minimo, tolerancia, porcentaje):
    """Un día sobra y el vecino falta un monto parecido: un error que se arrastra."""
    if abs(descuadre) < monto_minimo:
        return []
    salida = []
    for vecino in vecinos:
        y = vecino["descuadre"]
        if y is None or abs(y) < monto_minimo or not _contrarios(descuadre, y):
            continue
        dif = abs(descuadre + y)
        if dif <= tolerancia or 100 * dif <= porcentaje * max(abs(descuadre), abs(y)):
            signo = 1 if descuadre > 0 else -1
            salida.append({"regla": "R03", "que": "compensacion", "tipo": "causa",
                           "monto": signo * min(abs(descuadre), abs(y)), "total": y, "cual": vecino["cual"]})
    return salida


def causa_billete(descuadre, denominaciones, max_billetes):
    """El descuadre es justo de uno a pocos billetes iguales: un error al contar."""
    for d in sorted(set(denominaciones), reverse=True):
        cantidad, resto = divmod(abs(descuadre), d)
        if resto == 0 and 1 <= cantidad <= max_billetes:
            return [{"regla": "R04", "que": "billete", "tipo": "causa", "monto": descuadre,
                     "total": descuadre, "denominacion": d, "cantidad": cantidad}]
    return []


def causa_precios(descuadre, productos, monto_minimo, max_productos, max_mostradas):
    """El descuadre es la suma de pocos precios del punto. Es pista, no causa con peso."""
    objetivo = abs(descuadre)
    if objetivo == 0 or objetivo < monto_minimo:
        return []
    movimiento = {}
    for p in productos:
        if p["precio"] > 0:
            movimiento[p["precio"]] = movimiento.get(p["precio"], 0) + p["movimiento"]
    precios = sorted(movimiento)

    def armar(n, desde, suma):
        # Listas de n precios, de menor a mayor, que suman objetivo, en orden lexicográfico.
        if n == 1:
            resto = objetivo - suma
            return [[resto]] if resto in movimiento and resto >= precios[desde] else []
        salida = []
        for i in range(desde, len(precios)):
            if suma + n * precios[i] > objetivo:
                break
            salida += [[precios[i]] + cola for cola in armar(n - 1, i, suma + precios[i])]
        return salida

    combinaciones = []
    for n in range(1, max_productos + 1):
        combinaciones = armar(n, 0, 0) if precios else []
        if combinaciones:
            break
    if not combinaciones:
        return []
    combinaciones.sort(key=lambda c: -sum(movimiento[q] for q in c))
    return [{"regla": "R05", "que": "precios", "tipo": "causa", "monto": descuadre, "total": descuadre,
             "cuantas": len(combinaciones), "combinaciones": combinaciones[:max_mostradas]}]


_FUNCIONES = {f.__name__: f for f in (
    a_pesos, restar, emparejar, parecidos, sobrantes_vecinos, cruzar, dia_habil_siguiente,
    bloques_deposito, coincide_deposito, cruces_redeban, estado_dia,
    leer_linea_transferencia, punto_por_referencia, estadisticas_ventas, causas_de_cruce,
    causa_compensacion, causa_billete, causa_precios)}


def ejecutar(funcion, entrada):
    """Punto de entrada común con TypeScript: nombre de la función y parámetros."""
    return _FUNCIONES[funcion](**entrada)
