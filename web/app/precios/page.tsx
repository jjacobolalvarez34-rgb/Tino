// Precios: página pública, sin iniciar sesión. Todos los valores salen de web/lib/precios.ts.
import type { Metadata } from "next";
import Link from "next/link";
import { LogoTino, SelloMamut } from "@/components/presentacion/Marcas";
import { MAMUT } from "@/lib/mamut";
import { CONDICIONES, PLANES, TEXTO_PRINCIPAL, pesosCortos } from "@/lib/precios";
import { Calculadora } from "./Calculadora";
import s from "./precios.module.css";

export const metadata: Metadata = {
  title: "Precios · Tino",
  description: TEXTO_PRINCIPAL,
};

const PREGUNTAS = [
  {
    p: "¿Qué pasa con mis datos?",
    r: "Cada empresa ve solo sus datos: lo cuida la base de datos, no solo la pantalla. Nada se borra: lo que se corrige se anula o se ajusta, y queda quién lo hizo. Los datos son suyos.",
  },
  {
    p: "¿Cómo empiezo?",
    r: `Con un piloto de ${CONDICIONES.diasPiloto} días a mitad de precio. En la implementación configuramos sus puntos, su banco, sus datáfonos y la forma de sus Excel; después sube los archivos del día y Tino hace el cuadre.`,
  },
  {
    p: "¿Puedo cancelar?",
    r: "Sí. El plan mensual se cancela cuando quiera; el anual cubre los 12 meses que pagó.",
  },
  {
    p: "¿En qué aparatos funciona?",
    r: "En el navegador del celular y del computador. Los archivos del día (Excel, extracto del banco y datáfonos) se suben desde cualquiera de los dos: quedan en cola y los carga el programa de escritorio de Tino.",
  },
];

const PRONTO = ["Funcionar sin internet", "Leer solos los avisos de transferencia del correo", "Más bancos y datáfonos"];

export default function Precios() {
  return (
    <div className={s.pagina}>
      <header className={s.cabecera}>
        <Link href="/" className={s.logo} aria-label="Tino, inicio"><LogoTino alto={32} decorativo /></Link>
        <nav className={s.nav} aria-label="Páginas">
          <Link href="/">Qué es Tino</Link>
          <a href="/entrar" target="_blank" rel="noopener" className={s.botonSecundario}>Ir a la demo<span className={s.oculto}> (se abre en otra pestaña)</span></a>
        </nav>
      </header>

      <main className={s.contenido}>
        <section className={s.portada} aria-labelledby="t-precios">
          <p className={s.antetitulo}>Precios</p>
          <h1 id="t-precios" className={s.titulo}>Pague por punto de venta. Nada más.</h1>
          <p className={s.principal}>{TEXTO_PRINCIPAL}</p>
        </section>

        <section className={s.planes} aria-label="Planes">
          {PLANES.map((p) => (
            <article key={p.id} className={s.plan + (p.destacado ? " " + s.destacado : "")} aria-labelledby={"plan-" + p.id}>
              {p.destacado && <span className={s.cinta}>El más elegido</span>}
              <h2 id={"plan-" + p.id} className={s.planNombre}>{p.nombre}</h2>
              <p className={s.precio}><span className={s.cifra}>$ {pesosCortos(p.precio)}</span><span className={s.unidad}> por punto al mes</span></p>
              <p className={s.resumen}>{p.resumen}</p>
              <ul className={s.incluye}>
                {p.incluye.map((x) => <li key={x}><span aria-hidden="true" className={s.chulo}>✓</span>{x}</li>)}
              </ul>
            </article>
          ))}
        </section>

        <Calculadora />

        <section className={s.condiciones} aria-labelledby="t-condiciones">
          <h2 id="t-condiciones" className={s.subtitulo}>Condiciones</h2>
          <dl className={s.lista}>
            <div><dt>Mínimo</dt><dd>{CONDICIONES.minimoPuntos} puntos de venta.</dd></div>
            <div><dt>Implementación</dt><dd>Desde $ {pesosCortos(CONDICIONES.implementacionDesde)}, una sola vez: configuramos sus puntos, su banco, sus datáfonos y la forma de sus Excel.</dd></div>
            <div><dt>Pago anual</dt><dd>12 meses por el precio de {CONDICIONES.mesesPagadosAlAno}.</dd></div>
            <div><dt>Precio de fundador</dt><dd>{Math.round(CONDICIONES.descuentoFundador * 100)} % menos, fijo por {CONDICIONES.mesesFundador} meses, para los primeros {CONDICIONES.cuposFundador} clientes.</dd></div>
            <div><dt>Piloto</dt><dd>{CONDICIONES.diasPiloto} días a mitad de precio.</dd></div>
          </dl>
        </section>

        <section className={s.preguntas} aria-labelledby="t-preguntas">
          <h2 id="t-preguntas" className={s.subtitulo}>Preguntas frecuentes</h2>
          {PREGUNTAS.map((q) => (
            <details key={q.p} className={s.pregunta}>
              <summary>{q.p}</summary>
              <p>{q.r}</p>
            </details>
          ))}
          <div className={s.pronto}>
            <h3>Próximamente</h3>
            <ul>{PRONTO.map((x) => <li key={x}><span className={s.chipPronto}>Próximamente</span>{x}</li>)}</ul>
          </div>
        </section>

        <section className={s.cierre}>
          <h2 className={s.subtitulo}>¿Lo probamos con sus puntos?</h2>
          <p>Escríbanos y armamos el piloto de {CONDICIONES.diasPiloto} días.</p>
          <div className={s.acciones}>
            <a className={s.botonPrincipal} href={MAMUT.whatsappUrl} target="_blank" rel="noopener noreferrer">Escribir por WhatsApp<span className={s.oculto}> (se abre en otra pestaña)</span></a>
            <a className={s.botonSecundario} href="/entrar" target="_blank" rel="noopener">Ir a la demo<span className={s.oculto}> (se abre en otra pestaña)</span></a>
          </div>
          <p className={s.pequeno}>{MAMUT.whatsapp} · {MAMUT.correo}</p>
        </section>
      </main>

      <footer className={s.pie}>
        <SelloMamut alto={20} />
        <span>{MAMUT.derechos}</span>
      </footer>
    </div>
  );
}
