"use client";
// Las pantallas de caja de antes, dentro del marco nuevo (D-046): riel o barra inferior y
// "+ Registrar". Programa queda como puente para que esas pantallas sigan usando useYo().
import { createContext, useContext } from "react";
import { Marco, useMarco } from "./Marco";

export type Yo = { id: string; nombre: string; rol: string; empresa_id: string; empresa: string };
const Contexto = createContext<Yo | null>(null);
export const useYo = () => useContext(Contexto);

function Puente({ children }: { children: React.ReactNode }) {
  const { yo } = useMarco();
  return <Contexto.Provider value={yo}>{children}</Contexto.Provider>;
}

export function Programa({ children }: { children: React.ReactNode }) {
  return <Marco><Puente>{children}</Puente></Marco>;
}
