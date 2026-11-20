// Página pública de presentación de Tino (ruta "/"). Componente de servidor: lo que corre
// en el navegador es Escenario (entradas, inclinación y pausa), EscenaPortada, Contador,
// CopiarNumeros y Movimiento (línea de avance y botón de pausa).
// Todos los datos son de ejemplo e inventados (ver ejemplo.ts).
import { Fragment, type CSSProperties, type ReactNode } from "react";
import { MAMUT } from "@/lib/mamut";
import { Chip, Simbolo } from "./Chip";
import { Contador } from "./Contador";
import { CopiarNumeros } from "./CopiarNumeros";
import { EscenaPortada } from "./EscenaPortada";
import { Escenario } from "./Escenario";
import { Icono } from "./Lucide";
import { Chulito, LogoTino, SelloMamut } from "./Marcas";
import { Avance, BotonPausa } from "./Movimiento";
import {
  CIERRE,
  EQUIPO,
  FRANJA,
  PAGOS,
  RESUMEN_PAGOS,
  TOTAL_DIA,
  comoNumeros,
  formatear,
  sumar,
  totalPunto,
} from "./ejemplo";
import s from "./presentacion.module.css";

// Variables CSS por elemento (--i para escalonar, --p para las barras).
const v = (variables: Record<string, string | number>) => variables as CSSProperties;
const pesos = (n: number) => formatear(n, "pesos");

// "Ir a la demo": abre la pantalla de entrada del programa en otra pestaña. Quien no tenga
// usuario se queda ahí.
function BotonDemo({ variante = "principal" }: { variante?: "principal" | "grande" | "secundario" }) {
  const clase =
    variante === "grande" ? `${s.boton} ${s.grande}` : variante === "secundario" ? `${s.boton} ${s.secundario}` : s.boton;
  return (
    <a href="/entrar" target="_blank" rel="noopener" className={clase}>
      Ir a la demo
      <Icono nombre="external-link" tamano={18} />
      <span className={s.oculto}> (se abre en otra pestaña)</span>
    </a>
  );
}

function CabezaSeccion({
  id,
  antetitulo,
  titulo,
  children,
}: {
  id: string;
  antetitulo: string;
  titulo: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className={s.cabezaSeccion} data-revelar="">
      <p className={s.antetitulo}>{antetitulo}</p>
      {/* El título sube desde detrás de una máscara cuando la sección entra. */}
      <h2 id={id} className={s.tituloSeccion}>
        <span className={s.mascara}>
          <span className={s.mascaraTexto}>{titulo}</span>
        </span>
      </h2>
      {children}
    </div>
  );
}

// Titular de la portada: cada palabra sube desde detrás de su propia máscara, en orden.
// El texto sigue siendo un solo h1 que el lector de pantalla lee de corrido.
function Palabras({ texto, desde = 0 }: { texto: string; desde?: number }) {
  return (
    <>
      {texto.split(" ").map((palabra, i) => (
        <Fragment key={i}>
          <span className={s.palabra}>
            <span style={v({ "--w": desde + i })}>{palabra}</span>
          </span>{" "}
        </Fragment>
      ))}
    </>
  );
}

function Cabecera() {
  return (
    <header className={s.cabecera}>
      <div className={`${s.ancho} ${s.cabeceraFila}`}>
        <a href="#inicio" className={s.logoEnlace} aria-label="Tino, volver al inicio">
          {/* El ícono de Tino (docs/marca/tino-icono.svg) al lado de la palabra. */}
          <svg className={s.iconoMarca} viewBox="0 0 100 100" aria-hidden="true" focusable="false">
            <rect width="100" height="100" rx="24" fill="#74305F" />
            <path d="M50 48 V78" fill="none" stroke="#FFFFFF" strokeWidth="12" strokeLinecap="round" />
            <path d="M37 27 L46 36 L64 15" fill="none" stroke="#E9C6DC" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <LogoTino alto={44} claseChulito={s.chulitoLogo} decorativo />
        </a>
        <span className={s.espacio} />
        <nav aria-label="Secciones" className={s.nav}>
          <a href="#inicio">Inicio</a>
          <a href="#conciliar">Conciliación</a>
          <a href="#descuadres">Descuadres</a>
          <a href="#excel">Excel</a>
          <a href="#equipo">Equipo</a>
          <a href="/precios">Precios</a>
        </nav>
        <BotonDemo variante="secundario" />
      </div>
      <Avance />
    </header>
  );
}

function Portada() {
  return (
    <section id="inicio" className={s.portada} aria-labelledby="titulo-portada">
      {/* Fondo: renglones de libro contable con su margen, y dos luces cálidas que se mueven
          muy despacio. Decorativo. */}
      <div className={s.portadaFondo} aria-hidden="true">
        <span className={s.renglones} />
        <span className={s.margenCuaderno} />
        <span className={`${s.luz} ${s.luzUna}`} />
        <span className={`${s.luz} ${s.luzOtra}`} />
      </div>
      <div className={`${s.ancho} ${s.portadaRejilla}`}>
        <div className={s.portadaTexto}>
          <p className={`${s.antetitulo} ${s.entra}`}>Cuadre diario para negocios con varios puntos de venta</p>
          <h1 id="titulo-portada" className={s.titular}>
            <Palabras texto="Cada noche, punto por punto, sabe si la plata cuadró." />
            <span className={s.titularSuave}>
              <Palabras texto="Y si no, por qué." desde={10} />
            </span>
          </h1>
          <p className={`${s.entrada} ${s.entra}`} style={v({ "--d": "520ms" })}>
            Tino junta el Excel de cada punto, el programa de facturación, los extractos de sus bancos, las
            liquidaciones de los datáfonos y los avisos de transferencia. Concilia los pagos y le pone arriba lo
            que necesita atención.
          </p>
          <div className={`${s.acciones} ${s.entra}`} style={v({ "--d": "620ms" })}>
            <BotonDemo variante="grande" />
            <a href="#conciliar" className={s.botonTexto}>
              Ver cómo concilia
              <Icono nombre="arrow-down" tamano={18} />
            </a>
          </div>
          <p className={`${s.pequeno} ${s.entra}`} style={v({ "--d": "700ms" })}>
            La demo se abre en otra pestaña y pide usuario y contraseña.
          </p>
        </div>
        <EscenaPortada />
      </div>
    </section>
  );
}

// Franja que pasa despacio bajo la portada con lo que Tino resuelve en un día. La primera
// copia es la que lee el lector de pantalla; la segunda solo completa la vuelta.
function Franja() {
  const lista = (copia: boolean) => (
    <ul className={s.franjaLista} aria-hidden={copia || undefined}>
      {FRANJA.map((f, i) => (
        <li key={i}>
          <Simbolo estado={f.estado} />
          {f.texto}
        </li>
      ))}
    </ul>
  );
  return (
    <section className={s.franja} aria-label="Ejemplos de lo que Tino revisa en un día">
      <div className={s.franjaVentana}>
        <div className={s.franjaPista}>
          {lista(false)}
          {lista(true)}
        </div>
      </div>
      <BotonPausa />
    </section>
  );
}

const FUENTES = [
  { nombre: "Excel diario de cada punto", dice: "Lo que se anotó en caja." },
  { nombre: "Programa de facturación", dice: "Lo que se facturó y con qué forma de pago." },
  { nombre: "Extractos de sus bancos", dice: "Lo que de verdad entró a cada cuenta, en el banco que use." },
  { nombre: "Datáfonos", dice: "Cada venta con tarjeta y lo que la red liquidó." },
  { nombre: "Liquidaciones", dice: "Comisiones y retenciones tal como las cobró cada red." },
  { nombre: "Avisos de transferencia", dice: "Cada transferencia, minutos después de hecha." },
];

function Fuentes() {
  return (
    <section id="fuentes" className={s.seccion} aria-labelledby="t-fuentes">
      <div className={`${s.ancho} ${s.dosColumnas}`}>
        <CabezaSeccion id="t-fuentes" antetitulo="De dónde salen los datos" titulo="Hoy lo revisa en seis partes. Tino lo junta.">
          <p className={s.texto}>
            Cada punto anota a su manera y cada banco manda su propio formato. Tino lee cada fuente como
            viene y la lleva al mismo cuadre, punto por punto y día por día.
          </p>
        </CabezaSeccion>
        <dl className={s.fuentes}>
          {FUENTES.map((f, i) => (
            <div key={f.nombre} className={s.fuente} data-revelar="" style={v({ "--i": i })}>
              <dt>{f.nombre}</dt>
              <dd>{f.dice}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

function Conciliacion() {
  return (
    <section id="conciliar" className={`${s.seccion} ${s.banda}`} aria-labelledby="t-conciliar">
      <div className={`${s.ancho} ${s.dosColumnas}`}>
        <CabezaSeccion id="t-conciliar" antetitulo="Conciliación" titulo="¿La transferencia de las 3:40 sí llegó?">
          <p className={s.texto}>
            Tino cruza cada pago anotado con lo que de verdad entró: las transferencias con los avisos y el
            extracto, las tarjetas con lo que liquidó cada datáfono, las consignaciones con el extracto.
          </p>
          <p className={s.texto}>
            Lo que coincide queda verificado. Lo dudoso queda como propuesta, y una propuesta nunca se
            confirma sola: la confirma una persona.
          </p>
          <dl className={s.cifras}>
            <div>
              <dt>Pagos del sábado</dt>
              <dd className={s.num}>
                <Contador valor={RESUMEN_PAGOS.total} formato="entero" />
              </dd>
            </div>
            <div>
              <dt>Conciliados solos</dt>
              <dd className={s.num}>
                <Contador valor={RESUMEN_PAGOS.solos} formato="entero" retraso={100} />
              </dd>
            </div>
            <div>
              <dt>
                <span className={s.colorRevisar} aria-hidden="true">▲</span> Propuestas
              </dt>
              <dd className={s.num}>
                <Contador valor={RESUMEN_PAGOS.propuestas} formato="entero" retraso={200} />
              </dd>
            </div>
            <div>
              <dt>
                <span className={s.colorMal} aria-hidden="true">■</span> Sospechosa
              </dt>
              <dd className={s.num}>
                <Contador valor={RESUMEN_PAGOS.sospechosas} formato="entero" retraso={300} />
              </dd>
            </div>
          </dl>
          <p className={s.pequeno}>Cifras de un día de ejemplo.</p>
        </CabezaSeccion>

        <div className={s.escenaPagos} data-revelar="escena">
          <div className={s.tarjeta} data-inclinar="" role="group" aria-label="Ejemplo: seis pagos del sábado, conciliados">
          <div className={s.tarjetaCabeza}>
            <div>
              <p className={s.subtitulo}>Pagos del sábado</p>
              <p className={s.pequeno}>6 de {RESUMEN_PAGOS.total} · {CIERRE.fecha}</p>
            </div>
          </div>
          <ul className={s.pagos}>
            {PAGOS.map((p, i) => (
              <li key={p.hora} className={s.pago} style={v({ "--i": i })}>
                <span className={`${s.pagoHora} ${s.num}`}>{p.hora}</span>
                <strong className={s.pagoMedio}>{p.medio}</strong>
                <span className={s.pagoPrueba}>{p.prueba}</span>
                <span className={`${s.pagoMonto} ${s.num}`}>{pesos(p.monto)}</span>
                <span className={s.pagoEstado}>
                  <span className={s.chipBuscando} aria-hidden="true">
                    <Chip estado="espera">Buscando</Chip>
                  </span>
                  <span className={s.chipFinal}>
                    <Chip estado={p.estado}>{p.chip}</Chip>
                  </span>
                </span>
              </li>
            ))}
          </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

function Descuadres() {
  return (
    <section id="descuadres" className={s.seccion} aria-labelledby="t-descuadres">
      <div className={`${s.ancho} ${s.dosColumnas}`}>
        <CabezaSeccion id="t-descuadres" antetitulo="Descuadres" titulo="Si falta plata, le dice dónde buscar.">
          <p className={s.texto}>
            Para cada descuadre, Tino busca la causa más probable y le muestra la prueba: la celda del Excel,
            el cobro del datáfono o la línea del banco.
          </p>
          <p className={s.texto}>
            Si nada lo explica, lo dice así: <strong className={s.fuerte}>sin causa clara</strong>. No se
            inventa una.
          </p>
        </CabezaSeccion>

        <div className={s.escenaDescuadres} data-revelar="escena">
          <article className={`${s.tarjeta} ${s.descuadre}`} data-inclinar="" aria-label="Ejemplo: descuadre con causa probable">
            <div className={s.tarjetaCabeza}>
              <div>
                <p className={s.subtitulo}>Punto Plaza</p>
                <p className={s.pequeno}>{CIERRE.fecha}</p>
              </div>
              <Chip estado="mal">Descuadre</Chip>
            </div>
            <p className={`${s.descuadreMonto} ${s.num}`}>
              <Contador valor={-85_000} retraso={250} />
            </p>
            <div className={s.causa}>
              <p className={s.buscando} aria-hidden="true">
                Buscando la causa…
              </p>
              <div className={s.causaFinal}>
                <p className={`${s.etiqueta} ${s.causaParte}`}>Causa probable</p>
                <p className={`${s.causaNombre} ${s.causaParte}`}>Transferencia que no llegó</p>
                <ul className={s.pruebas}>
                  {[
                    `El Excel de Punto Plaza tiene una transferencia de ${pesos(85_000)} a las 15:40.`,
                    "El extracto del banco no la muestra ni el 14 ni el 15 de noviembre.",
                    "Explica todo el faltante.",
                  ].map((texto, i) => (
                    <li key={i} style={v({ "--i": i })}>
                      <span className={s.pruebaMarca}>
                        <Chulito clase={s.trazoPrueba} grosor={6} />
                      </span>
                      {texto}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <p className={s.descuadrePie}>Queda abierto hasta que una persona lo confirme, con nota y nombre.</p>
          </article>

          <article className={`${s.tarjeta} ${s.descuadre} ${s.sinCausa}`} data-inclinar="" aria-label="Ejemplo: descuadre sin causa clara">
            <div className={s.tarjetaCabeza}>
              <div>
                <p className={s.subtitulo}>Punto Norte</p>
                <p className={s.pequeno}>Viernes 13 nov</p>
              </div>
              <span className={`${s.sinCausaMonto} ${s.num}`}>{pesos(-12_000)}</span>
            </div>
            <p className={s.texto}>
              <strong className={s.fuerte}>Sin causa clara.</strong> Ninguna causa explica lo suficiente. Queda
              abierto para revisar.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}

function Excel() {
  return (
    <section id="excel" className={`${s.seccion} ${s.banda}`} aria-labelledby="t-excel">
      <div className={`${s.ancho} ${s.columna}`}>
        <CabezaSeccion id="t-excel" antetitulo="Excel" titulo="No le quita su Excel. Se lo llena.">
          <p className={s.texto}>
            Cada tabla de Tino trae un botón: Copiar como números. Entrega enteros, sin signo de pesos ni
            puntos, separados por tabulación. Se pega en Excel y las columnas se pueden sumar. Pruébelo aquí.
          </p>
        </CabezaSeccion>
        <div className={`${s.tarjeta} ${s.tablaTarjeta}`} data-revelar="escena">
          <div className={s.caja} role="region" aria-labelledby="t-tabla" tabIndex={0}>
            <table className={s.tabla}>
              <caption id="t-tabla" className={s.tablaTitulo}>
                Cierre del {CIERRE.fecha.toLowerCase()} por punto · ejemplo
              </caption>
              <thead>
                <tr>
                  <th scope="col">Punto</th>
                  <th scope="col" className={s.d}>Efectivo</th>
                  <th scope="col" className={s.d}>Tarjeta</th>
                  <th scope="col" className={s.d}>Transferencia</th>
                  <th scope="col" className={s.d}>Total</th>
                  <th scope="col" className={s.d}>Descuadre</th>
                </tr>
              </thead>
              <tbody>
                {CIERRE.puntos.map((p) => (
                  <tr key={p.punto}>
                    <th scope="row">{p.punto}</th>
                    <td className={s.d}>{pesos(p.efectivo)}</td>
                    <td className={s.d}>{pesos(p.tarjeta)}</td>
                    <td className={s.d}>{pesos(p.transferencia)}</td>
                    <td className={s.d}>{pesos(totalPunto(p))}</td>
                    <td className={`${s.d} ${p.descuadre < 0 ? s.colorMal : ""}`}>{pesos(p.descuadre)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row">Total</th>
                  <td className={s.d}>{pesos(sumar("efectivo"))}</td>
                  <td className={s.d}>{pesos(sumar("tarjeta"))}</td>
                  <td className={s.d}>{pesos(sumar("transferencia"))}</td>
                  <td className={s.d}>{pesos(TOTAL_DIA)}</td>
                  <td className={`${s.d} ${s.colorMal}`}>{pesos(sumar("descuadre"))}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <CopiarNumeros texto={comoNumeros()} />
        </div>
      </div>
    </section>
  );
}

function Equipo() {
  return (
    <section id="equipo" className={s.seccion} aria-labelledby="t-equipo">
      <div className={`${s.ancho} ${s.columna}`}>
        <CabezaSeccion id="t-equipo" antetitulo="Nuevo: Equipo" titulo="Quién vende, cuánto y qué sigue.">
          <p className={s.texto}>
            Las personas de cada punto con su venta, su ticket promedio y cómo van con la meta. Al lado, lo que
            se habló con cada una: observaciones, acompañamiento y compromisos con fecha.
          </p>
        </CabezaSeccion>
        <div className={s.equipoRejilla}>
          <div className={s.ranking} data-revelar="escena">
          <div className={s.tarjeta} data-inclinar="" role="group" aria-label="Ejemplo: ranking de ventas de noviembre">
            <div className={s.tarjetaCabeza}>
              <div>
                <p className={s.subtitulo}>Ventas de noviembre</p>
                <p className={s.pequeno}>Del 1 al 14 · ejemplo</p>
              </div>
            </div>
            <ol className={s.personas}>
              {EQUIPO.map((p, i) => (
                <li key={p.nombre} className={s.persona} style={v({ "--i": i, "--p": Math.min(p.meta, 100) / 100 })}>
                  <span className={`${s.puesto} ${s.num}`} aria-hidden="true">
                    {i + 1}
                  </span>
                  <span className={s.personaNombre}>
                    <strong>{p.nombre}</strong>
                    <span className={s.pequeno}>{p.punto}</span>
                  </span>
                  <span className={s.personaVentas}>
                    <strong className={s.num}>
                      <Contador valor={p.ventas} retraso={150 + i * 120} alinear="fin" />
                    </strong>
                    <span className={`${s.pequeno} ${s.num}`}>Ticket promedio {pesos(p.ticket)}</span>
                  </span>
                  <span className={s.meta}>
                    <span className={s.metaBarra} aria-hidden="true">
                      <span className={s.metaRelleno} />
                    </span>
                    <span className={`${s.metaTexto} ${s.num}`}>{p.meta} % de la meta</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
          </div>

          <div className={s.pendientes} data-revelar="escena" style={v({ "--i": 2 })}>
          <div className={s.tarjeta} data-inclinar="">
            <div className={s.tarjetaCabeza}>
              <div>
                <p className={s.subtitulo}>Pendientes de hoy</p>
                <p className={s.pequeno}>{CIERRE.fecha} · ejemplo</p>
              </div>
            </div>
            <ul className={s.listaPendientes}>
              <li>
                <span className={s.pendienteIcono}>
                  <Icono nombre="calendar-days" />
                </span>
                <span>
                  <strong>Revisar el compromiso con Felipe</strong>
                  <span className={s.pequeno}>Ofrecer el producto del mes en cada venta. Vence hoy.</span>
                </span>
              </li>
              <li>
                <span className={s.pendienteIcono}>
                  <Icono nombre="clipboard-list" />
                </span>
                <span>
                  <strong>Acompañar a Camila en Punto Plaza</strong>
                  <span className={s.pequeno}>Observación del martes: atiende rápido, pero no ofrece el producto del mes.</span>
                </span>
              </li>
              <li>
                <span className={s.pendienteIcono}>
                  <Icono nombre="clipboard-list" />
                </span>
                <span>
                  <strong>Hablar con Andrés sobre la meta</strong>
                  <span className={s.pequeno}>Va en 93 % y quedan 16 días del mes.</span>
                </span>
              </li>
            </ul>
          </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const NO_HACE = [
  { que: "No factura.", detalle: "Su programa de facturación sigue facturando. Tino lee lo que ya tiene." },
  { que: "No calcula impuestos.", detalle: "Retenciones y comisiones salen de las liquidaciones de los datáfonos y del banco." },
  { que: "No confirma lo dudoso.", detalle: "Una propuesta espera a que una persona la revise." },
  { que: "No borra.", detalle: "Lo que se corrige se anula o se ajusta, y queda registrado quién lo hizo." },
];

function NoHace() {
  return (
    <section className={`${s.seccion} ${s.banda}`} aria-labelledby="t-nohace">
      <div className={`${s.ancho} ${s.columna}`}>
        <CabezaSeccion id="t-nohace" antetitulo="Para que no haya sorpresas" titulo="Lo que Tino no hace." />
        <dl className={s.noHace}>
          {NO_HACE.map((n, i) => (
            <div key={n.que} className={s.noHaceFila} data-revelar="" style={v({ "--i": i })}>
              <dt>{n.que}</dt>
              <dd>{n.detalle}</dd>
            </div>
          ))}
        </dl>
        <ul className={s.garantias} data-revelar="">
          <li>
            <Icono nombre="smartphone" />
            <Icono nombre="monitor" />
            Funciona en el celular y en el computador.
          </li>
          <li>
            <Icono nombre="lock" />
            Cada empresa ve solo sus datos.
          </li>
        </ul>
      </div>
    </section>
  );
}

function Cierre() {
  return (
    <section className={`${s.seccion} ${s.cierreFinal}`} aria-labelledby="t-cierre" data-revelar="">
      <div className={`${s.ancho} ${s.cierreRejilla}`}>
        <span className={s.granChulito}>
          <Chulito clase={s.trazoGrande} grosor={4.5} />
        </span>
        <div className={s.cierreTexto}>
          <h2 id="t-cierre" className={s.tituloSeccion}>
            Entre a la demo.
          </h2>
          <p className={s.texto}>
            Es Tino de verdad, el mismo que estamos construyendo. Pide usuario y contraseña; si no tiene uno,
            pídalo por WhatsApp al {MAMUT.whatsapp}.
          </p>
          <div className={s.acciones}>
            <BotonDemo variante="grande" />
            <a href={MAMUT.whatsappUrl} target="_blank" rel="noopener noreferrer" className={s.botonTexto}>
              Pedir usuario por WhatsApp
              <span className={s.oculto}> (se abre en otra pestaña)</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function Pie() {
  return (
    <footer className={s.pie}>
      <div className={`${s.ancho} ${s.pieRejilla}`}>
        <div className={s.pieMarca}>
          <LogoTino alto={64} />
          <p className={s.pequeno}>Cuadre diario para negocios con varios puntos de venta en Colombia.</p>
        </div>
        <div className={s.pieContacto}>
          <p className={s.etiqueta}>Contacto</p>
          <a href={`mailto:${MAMUT.correo}`}>
            <Icono nombre="mail" />
            {MAMUT.correo}
          </a>
          <a href={MAMUT.whatsappUrl} target="_blank" rel="noopener noreferrer">
            <Icono nombre="message-circle" />
            WhatsApp {MAMUT.whatsapp}
            <span className={s.oculto}> (se abre en otra pestaña)</span>
          </a>
        </div>
        <div className={s.pieFirma}>
          <SelloMamut alto={20} />
          <p className={s.pequeno}>{MAMUT.derechos}</p>
        </div>
      </div>
    </footer>
  );
}

export function Presentacion() {
  return (
    <Escenario className={s.raiz}>
      <a href="#contenido" className={s.saltar}>
        Saltar al contenido
      </a>
      <Cabecera />
      <main id="contenido">
        <Portada />
        <Franja />
        <Fuentes />
        <Conciliacion />
        <Descuadres />
        <Excel />
        <Equipo />
        <NoHace />
        <Cierre />
      </main>
      <Pie />
    </Escenario>
  );
}
