// Cuánto va de la meta, en un anillo. Llega a 100 % y se pone verde; si pasa, lo dice el
// número, no el anillo. Sin meta, no se inventa: muestra un anillo vacío y "Sin meta".
export function AnilloMeta({ valor, meta, tamano = 72, etiqueta }: {
  valor: number; meta: number | null; tamano?: number; etiqueta?: string;
}) {
  const r = 15.5;
  const largo = 2 * Math.PI * r;
  const pct = meta && meta > 0 ? Math.round((valor / meta) * 100) : null;
  const lleno = pct == null ? 0 : Math.min(pct, 100) / 100;
  const texto = pct == null ? "Sin meta" : `${pct} % de la meta`;
  return (
    <span className="m-anillo" role="img" aria-label={(etiqueta ? etiqueta + ": " : "") + texto}
      style={{ width: tamano, height: tamano }}>
      <svg viewBox="0 0 36 36" aria-hidden="true">
        <circle cx="18" cy="18" r={r} className="m-anillo-fondo" />
        {pct != null && (
          <circle cx="18" cy="18" r={r} className={"m-anillo-valor" + (pct >= 100 ? " lleno" : "")}
            strokeDasharray={`${lleno * largo} ${largo}`} transform="rotate(-90 18 18)" />
        )}
      </svg>
      <span className="m-anillo-texto num" aria-hidden="true">{pct == null ? "—" : `${pct}%`}</span>
    </span>
  );
}
