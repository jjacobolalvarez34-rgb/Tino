// El logo de Tino ("Visto bueno", docs/marca/tino-logo.svg) y el sello de Mamut Herd.
import { MAMUT, MAMUT_HERD_URL } from "@/lib/mamut";
import s from "./presentacion.module.css";

// Logo en línea para poder dibujar el chulito. Las letras van en el color del texto y el
// chulito en ciruela, como en el archivo de la marca; no se deforma ni se le pone sombra.
export function LogoTino({
  alto,
  claseChulito,
  decorativo = false,
}: {
  alto: number;
  claseChulito?: string;
  decorativo?: boolean;
}) {
  const accesible = decorativo ? { "aria-hidden": true as const } : { role: "img", "aria-label": "Tino" };
  return (
    <svg viewBox="0 30 380 200" width={Math.round(alto * 1.9)} height={alto} focusable="false" {...accesible}>
      <g fill="none" stroke="#22161F" strokeWidth="24" strokeLinecap="round" strokeLinejoin="round">
        <path d="M40 62 V166 Q40 200 74 200" />
        <path d="M16 104 H70" />
        <path d="M112 112 V200" />
        <path d="M152 200 V140 C152 118 168 102 190 102 C212 102 228 118 228 140 V200" />
        <circle cx="304" cy="152" r="50" />
      </g>
      <path
        className={claseChulito}
        pathLength={1}
        d="M94 62 L109 77 L136 44"
        fill="none"
        stroke="#74305F"
        strokeWidth="17"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// El chulito solo, para el sello de "revisado" y el cierre de la página.
export function Chulito({ clase, grosor = 5 }: { clase?: string; grosor?: number }) {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      <path
        className={clase}
        pathLength={1}
        d="M13 25 L21 33 L36 15"
        fill="none"
        stroke="currentColor"
        strokeWidth={grosor}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Sello "Un producto de Mamut Herd" del kit, sobre fondo claro. Va en el pie, más pequeño
// que el logo de Tino. Mientras MAMUT_HERD_URL esté vacía, se muestra sin enlace.
export function SelloMamut({ alto = 20 }: { alto?: number }) {
  const imagen = (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={MAMUT.sello.fondoClaro}
      alt={MAMUT.sello.alt}
      width={Math.round(alto * MAMUT.sello.proporcion)}
      height={alto}
      className={s.selloImagen}
    />
  );
  if (!MAMUT_HERD_URL) return <span className={s.sello}>{imagen}</span>;
  return (
    <a href={MAMUT_HERD_URL} target="_blank" rel="noopener noreferrer" className={s.sello}>
      {imagen}
    </a>
  );
}
