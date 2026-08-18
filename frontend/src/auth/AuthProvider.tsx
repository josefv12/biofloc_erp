import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { loginRequest, meRequest } from "../api/auth";
import { ApiError, UNAUTHORIZED_EVENT, clearToken, getToken, setToken } from "../api/client";
import { returnToPath } from "./returnTo";
import type { AuthState, UsuarioActual } from "../types/auth";

type AuthContextValue = AuthState & {
  login: (correo: string, password: string, from?: unknown) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [user, setUser] = useState<UsuarioActual | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    setUser(null);
    navigate("/login", { replace: true });
  }, [navigate]);

  const loadSession = useCallback(async () => {
    const stored = getToken();
    if (!stored) {
      setUser(null);
      setTokenState(null);
      setLoading(false);
      return;
    }

    setTokenState(stored);
    try {
      const me = await meRequest();
      setUser(me);
    } catch (error) {
      clearToken();
      setTokenState(null);
      setUser(null);
      if (error instanceof ApiError && error.status === 403) {
        // Usuario inactivo u otro rechazo de /me: misma salida que sesión inválida.
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  useEffect(() => {
    const onUnauthorized = () => {
      setTokenState(null);
      setUser(null);
      navigate("/login", { replace: true });
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, [navigate]);

  const login = useCallback(async (correo: string, password: string, from?: unknown) => {
    const response = await loginRequest({ correo, password });
    setToken(response.access_token);
    setTokenState(response.access_token);
    const me = await meRequest();
    setUser(me);
    navigate(returnToPath(from), { replace: true });
  }, [navigate]);

  const value = useMemo<AuthContextValue>(
    () => ({ token, user, loading, login, logout }),
    [token, user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return ctx;
}
