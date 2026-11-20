// Iniciales en un círculo de color. El color sale del id: la misma persona siempre tiene
// el mismo, sin guardarlo. Los pares de color son los de DESIGN.md §15 (contraste AA).
const PARES = 6;

function tono(id: string) {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return h % PARES;
}

export function iniciales(nombre: string) {
  const partes = nombre.trim().split(/\s+/).filter(Boolean);
  if (!partes.length) return "?";
  const a = partes[0][0];
  const b = partes.length > 1 ? partes[1][0] : partes[0][1] ?? "";
  return (a + b).toUpperCase();
}

export function Avatar({ id, nombre, tamano = 40 }: { id: string; nombre: string; tamano?: number }) {
  return (
    <span className={`m-avatar m-avatar-${tono(id)}`} aria-hidden="true"
      style={{ width: tamano, height: tamano, fontSize: Math.round(tamano * 0.38) }}>
      {iniciales(nombre)}
    </span>
  );
}
