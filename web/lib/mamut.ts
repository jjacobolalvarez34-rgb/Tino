// Información de Mamut Herd, la empresa detrás de Tino. Sale del kit de marca
// (Tino-datos/mamut/kit/mamut-herd-kit-de-marca/MAMUT-HERD.md). Si cambia allá, se cambia aquí.

// Web de Mamut Herd (20 nov 2026). El sello del pie enlaza aquí, en otra pestaña.
export const MAMUT_HERD_URL: string = "https://mamutherdpage.vercel.app/#productos";

export const MAMUT = {
  nombre: "Mamut Herd",
  firma: "Un producto de Mamut Herd",
  derechos: "© 2026 Mamut Herd",
  correo: "mamutherdoficial@gmail.com",
  whatsapp: "+57 320 487 1882",
  whatsappUrl: "https://wa.me/573204871882",
  // Sello en línea del kit, copiado tal cual. Proporción ancho/alto del archivo: 1193,55 / 208.
  sello: {
    fondoClaro: "/mamut/un-producto-de-mamut-herd-linea-para-fondo-claro.svg",
    proporcion: 1193.55 / 208,
    alt: "Un producto de Mamut Herd",
  },
} as const;
