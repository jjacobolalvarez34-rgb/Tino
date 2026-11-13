/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  poweredByHeader: false,
  // La revisión usa el núcleo de motores/nucleo_ts, que vive fuera de web/.
  experimental: { externalDir: true },
  // Ninguna página guarda datos de clientes en caché del servidor: todo se lee con la
  // sesión de quien entra, y RLS decide qué ve.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "same-origin" },
          { key: "X-Content-Type-Options", value: "nosniff" },
        ],
      },
    ];
  },
};

export default config;
