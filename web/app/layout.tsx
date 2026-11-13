import type { Metadata } from "next";
import "./globals.css";
import { Iconos } from "@/components/Iconos";

export const metadata: Metadata = {
  title: "Tino",
  description: "Cuadre diario por punto de venta: transferencias, tarjetas y descuadres.",
  robots: { index: false, follow: false },
};

export default function Raiz({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&display=swap" />
        <link rel="icon" href="/icono.svg" />
      </head>
      <body>
        <Iconos />
        {children}
      </body>
    </html>
  );
}
