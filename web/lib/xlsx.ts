// Un .xlsx de una hoja, sin librerías: un .xlsx es un zip con unos XML adentro. Los números van
// como números (Excel los suma), el texto como texto y la primera fila en negrita. Se usa en
// "Descargar Excel" de las tablas: el Excel es una salida que Tino genera (D-068).

const enc = new TextEncoder();

// CRC-32 (el zip lo exige por archivo).
const TABLA_CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(b: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < b.length; i++) c = TABLA_CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

// Zip sin compresión (método "store"): suficiente para hojas de reportes y sin dependencias.
function zip(archivos: { nombre: string; datos: Uint8Array }[]): Uint8Array {
  const partes: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let pos = 0;
  for (const a of archivos) {
    const nombre = enc.encode(a.nombre);
    const crc = crc32(a.datos);
    const local = new DataView(new ArrayBuffer(30));
    local.setUint32(0, 0x04034b50, true); local.setUint16(4, 20, true); local.setUint16(6, 0x0800, true);
    local.setUint16(8, 0, true); local.setUint32(14, crc, true);
    local.setUint32(18, a.datos.length, true); local.setUint32(22, a.datos.length, true); local.setUint16(26, nombre.length, true);
    partes.push(new Uint8Array(local.buffer), nombre, a.datos);
    const c = new DataView(new ArrayBuffer(46));
    c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
    c.setUint32(16, crc, true); c.setUint32(20, a.datos.length, true); c.setUint32(24, a.datos.length, true);
    c.setUint16(28, nombre.length, true); c.setUint32(42, pos, true);
    central.push(new Uint8Array(c.buffer), nombre);
    pos += 30 + nombre.length + a.datos.length;
  }
  const tamCentral = central.reduce((s, x) => s + x.length, 0);
  const fin = new DataView(new ArrayBuffer(22));
  fin.setUint32(0, 0x06054b50, true); fin.setUint16(8, archivos.length, true); fin.setUint16(10, archivos.length, true);
  fin.setUint32(12, tamCentral, true); fin.setUint32(16, pos, true);
  const todo = [...partes, ...central, new Uint8Array(fin.buffer)];
  const salida = new Uint8Array(todo.reduce((s, x) => s + x.length, 0));
  let i = 0;
  for (const x of todo) { salida.set(x, i); i += x.length; }
  return salida;
}

const esc = (t: string) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
  .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "");
function columna(n: number): string {
  let s = "";
  for (n += 1; n > 0; n = Math.floor((n - 1) / 26)) s = String.fromCharCode(65 + ((n - 1) % 26)) + s;
  return s;
}

export type Celda = string | number | null;

// Arma el .xlsx: filas[0] es el encabezado (en negrita).
export function hacerXlsx(hoja: string, filas: Celda[][]): Uint8Array {
  const nombreHoja = esc(hoja.replace(/[\\/?*[\]:]/g, " ").slice(0, 31) || "Hoja1");
  const xmlFilas = filas.map((f, r) => `<row r="${r + 1}">${f.map((v, c) => {
    const ref = `${columna(c)}${r + 1}`;
    const estilo = r === 0 ? ' s="1"' : "";
    if (v == null || v === "") return "";
    if (typeof v === "number" && Number.isFinite(v)) return `<c r="${ref}"${estilo}><v>${v}</v></c>`;
    return `<c r="${ref}"${estilo} t="inlineStr"><is><t xml:space="preserve">${esc(String(v))}</t></is></c>`;
  }).join("")}</row>`).join("");
  const anchos = (filas[0] ?? []).map((_, c) => {
    const largo = Math.max(...filas.map((f) => String(f[c] ?? "").length), 6);
    return `<col min="${c + 1}" max="${c + 1}" width="${Math.min(60, largo + 2)}" customWidth="1"/>`;
  }).join("");
  const x = (s: string) => enc.encode(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n${s}`);
  return zip([
    { nombre: "[Content_Types].xml", datos: x(`<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`) },
    { nombre: "_rels/.rels", datos: x(`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`) },
    { nombre: "xl/workbook.xml", datos: x(`<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="${nombreHoja}" sheetId="1" r:id="rId1"/></sheets></workbook>`) },
    { nombre: "xl/_rels/workbook.xml.rels", datos: x(`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`) },
    { nombre: "xl/styles.xml", datos: x(`<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`) },
    { nombre: "xl/worksheets/sheet1.xml", datos: x(`<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>${anchos ? `<cols>${anchos}</cols>` : ""}<sheetData>${xmlFilas}</sheetData></worksheet>`) },
  ]);
}

// Descarga el archivo en el navegador.
export function descargarXlsx(nombreArchivo: string, hoja: string, filas: Celda[][]) {
  const datos = hacerXlsx(hoja, filas);
  const blob = new Blob([datos], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nombreArchivo.endsWith(".xlsx") ? nombreArchivo : nombreArchivo + ".xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
