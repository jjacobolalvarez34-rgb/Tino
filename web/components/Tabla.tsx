"use client";
// Tabla de DESIGN.md con lo que pide Jacobo: total al final, orden por columna y "Copiar
// como números". En el celular se vuelve lista: la primera columna en negrita y el resto
// debajo, cada dato con su nombre.
import { useMemo, useState } from "react";
import { copiarComoNumeros, miles, pesos } from "@/lib/formato";
import { Icono } from "./Iconos";

export type Columna<F> = {
  clave: string; titulo: string; tipo?: "texto" | "pesos" | "numero" | "porcentaje";
  valor: (f: F) => string | number | null; mostrar?: (f: F) => React.ReactNode; total?: "suma" | ((filas: F[]) => number | null);
};

const fmt = (tipo: Columna<unknown>["tipo"], v: string | number | null) => {
  if (v == null || v === "") return "—";
  if (tipo === "pesos") return pesos(Number(v));
  if (tipo === "numero") return miles(Number(v));
  if (tipo === "porcentaje") return `${v} %`;
  return String(v);
};

export function Tabla<F>({ titulo, columnas, filas, clave, alTocar, avisar, vacio = "No hay datos para este período." }: {
  titulo: string; columnas: Columna<F>[]; filas: F[]; clave: (f: F) => string; alTocar?: (f: F) => void;
  avisar?: (t: string) => void; vacio?: string;
}) {
  const [orden, setOrden] = useState<{ clave: string; asc: boolean } | null>(null);
  const ordenadas = useMemo(() => {
    if (!orden) return filas;
    const c = columnas.find((x) => x.clave === orden.clave);
    if (!c) return filas;
    return [...filas].sort((a, b) => {
      const va = c.valor(a), vb = c.valor(b);
      if (va == null) return 1;
      if (vb == null) return -1;
      const r = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb), "es");
      return orden.asc ? r : -r;
    });
  }, [filas, columnas, orden]);

  const totales = columnas.map((c) =>
    c.total === "suma" ? filas.reduce((s, f) => s + (Number(c.valor(f)) || 0), 0) : c.total ? c.total(filas) : null);
  const hayTotal = totales.some((t) => t != null);

  async function copiar() {
    const plano = (c: Columna<F>, v: string | number | null) =>
      v == null ? "" : c.tipo && c.tipo !== "texto" ? String(Math.round(Number(v))) : String(v);
    const datos = [columnas.map((c) => c.titulo), ...ordenadas.map((f) => columnas.map((c) => plano(c, c.valor(f))))];
    if (hayTotal) datos.push(columnas.map((c, i) => (i === 0 ? "Total" : plano(c, totales[i]))));
    const ok = await copiarComoNumeros(datos);
    avisar?.(ok ? "Copiado. Péguelo en Excel." : "El navegador no dejó copiar.");
  }

  function ordenar(c: string) {
    setOrden((o) => (o?.clave === c ? { clave: c, asc: !o.asc } : { clave: c, asc: false }));
  }

  if (!filas.length) return <p className="m-vacio">{vacio}</p>;
  return (
    <section className="m-tabla" aria-label={titulo}>
      <div className="m-tabla-barra">
        <button className="boton texto compacto" onClick={copiar}><Icono id="copiar" />Copiar como números</button>
      </div>
      <div className="m-tabla-escritorio caja">
        <table>
          <thead>
            <tr>
              {columnas.map((c) => (
                <th key={c.clave} className={c.tipo && c.tipo !== "texto" ? "d" : ""}
                  aria-sort={orden?.clave === c.clave ? (orden.asc ? "ascending" : "descending") : "none"}>
                  <button className="m-orden" onClick={() => ordenar(c.clave)}>
                    {c.titulo}<span aria-hidden="true">{orden?.clave === c.clave ? (orden.asc ? " ↑" : " ↓") : ""}</span>
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ordenadas.map((f) => (
              <tr key={clave(f)} className={alTocar ? "m-tocable" : ""} onClick={alTocar ? () => alTocar(f) : undefined}>
                {columnas.map((c, i) => (
                  <td key={c.clave} className={c.tipo && c.tipo !== "texto" ? "d num" : ""}>
                    {i === 0 && alTocar
                      ? <button className="m-enlace-fila" onClick={(e) => { e.stopPropagation(); alTocar(f); }}>{c.mostrar ? c.mostrar(f) : fmt(c.tipo, c.valor(f))}</button>
                      : c.mostrar ? c.mostrar(f) : fmt(c.tipo, c.valor(f))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
          {hayTotal && (
            <tfoot>
              <tr>{columnas.map((c, i) => <td key={c.clave} className={i ? "d num" : ""}>{i === 0 ? "Total" : fmt(c.tipo, totales[i])}</td>)}</tr>
            </tfoot>
          )}
        </table>
      </div>
      <ul className="m-tabla-celular m-lista">
        {ordenadas.map((f) => {
          const [primera, ...resto] = columnas;
          const cuerpo = (
            <>
              <span className="m-fila-texto">
                <b>{primera.mostrar ? primera.mostrar(f) : fmt(primera.tipo, primera.valor(f))}</b>
                <span className="m-pares">
                  {resto.map((c) => <span key={c.clave}>{c.titulo} <b className="num">{c.mostrar ? c.mostrar(f) : fmt(c.tipo, c.valor(f))}</b></span>)}
                </span>
              </span>
              {alTocar && <Icono id="derecha" />}
            </>
          );
          return (
            <li key={clave(f)}>
              {alTocar ? <button className="m-fila" onClick={() => alTocar(f)}>{cuerpo}</button> : <div className="m-fila">{cuerpo}</div>}
            </li>
          );
        })}
        {hayTotal && (
          <li className="m-fila m-fila-total">
            <span className="m-fila-texto"><b>Total</b>
              <span className="m-pares">{columnas.slice(1).map((c, i) => totales[i + 1] != null &&
                <span key={c.clave}>{c.titulo} <b className="num">{fmt(c.tipo, totales[i + 1])}</b></span>)}</span>
            </span>
          </li>
        )}
      </ul>
    </section>
  );
}
