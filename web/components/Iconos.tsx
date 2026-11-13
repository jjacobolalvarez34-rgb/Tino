// Íconos de Lucide (ISC) y el logo de Tino, los mismos del programa.
export function Iconos() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: '<!-- Íconos de Lucide (ISC) -->\n  <symbol id="i-dia" viewBox="0 0 24 24"><path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/></symbol>\n  <symbol id="i-subir" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></symbol>\n  <symbol id="i-transf" viewBox="0 0 24 24"><path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/></symbol>\n  <symbol id="i-revisar" viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></symbol>\n  <symbol id="i-caja" viewBox="0 0 24 24"><rect width="20" height="12" x="2" y="6" rx="2"/><circle cx="12" cy="12" r="2"/><path d="M6 12h.01M18 12h.01"/></symbol>\n  <symbol id="i-ventas" viewBox="0 0 24 24"><path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></symbol>\n  <symbol id="i-copiar" viewBox="0 0 24 24"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></symbol>\n  <symbol id="i-cargando" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></symbol>\n  <symbol id="i-ok" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></symbol>\n  <symbol id="i-alerta" viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/></symbol>\n  <symbol id="i-buscar" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></symbol>\n  <symbol id="i-ajustes" viewBox="0 0 24 24"><path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/></symbol>\n  <symbol id="i-excel" viewBox="0 0 24 24"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 13h2"/><path d="M14 13h2"/><path d="M8 17h2"/><path d="M14 17h2"/></symbol>\n  <symbol id="i-salir" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/></symbol>\n\n  <symbol id="logo" viewBox="0 0 100 100"><rect width="100" height="100" rx="24" fill="#74305F"/><path d="M50 48 V78" fill="none" stroke="#FFFFFF" stroke-width="12" stroke-linecap="round"/><path d="M37 27 L46 36 L64 15" fill="none" stroke="#E9C6DC" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/></symbol>' }} />
  );
}

export function Icono({ id, girando }: { id: string; girando?: boolean }) {
  return (
    <svg className={"icono" + (girando ? " girando" : "")} aria-hidden="true">
      <use href={`#i-${id}`} />
    </svg>
  );
}
