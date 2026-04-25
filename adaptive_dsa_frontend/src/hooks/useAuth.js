import { useContext } from "react";
import { AuthContext } from "@/context/AuthContext";

/** Convenience hook so pages never import the context directly. */
export const useAuth = () => useContext(AuthContext);
