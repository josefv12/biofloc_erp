import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ApiError } from "./api/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import "./index.css";

function esFalloDeRed(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 0 || error.status === 502 || error.status === 503);
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (intentos, error) => esFalloDeRed(error) && intentos < 2,
      retryDelay: 600,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
  },
});

const root = document.getElementById("root");
if (!root) {
  throw new Error("No se encontró el elemento #root");
}

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
