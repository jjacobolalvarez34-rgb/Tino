// "/" es la página de presentación de Tino. El programa vive en /resumen y se entra por /entrar.
import type { Metadata } from "next";
import { Presentacion } from "@/components/presentacion/Presentacion";

export const metadata: Metadata = {
  title: "Tino · Cuadre diario para negocios con varios puntos",
  description:
    "Tino junta el Excel de cada punto, Siigo, el extracto del banco, Bold, Redeban y los avisos de transferencia; concilia los pagos y dice por qué no cuadró la caja. Un producto de Mamut Herd.",
};

export default function Inicio() {
  return <Presentacion />;
}
