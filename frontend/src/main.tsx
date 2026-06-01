import { Component, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import "./globals.css";
import App from "./App";

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "2rem", color: "#f87171", background: "#09090b", minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "1rem" }}>
          <h1 style={{ fontSize: "1.25rem" }}>Something went wrong</h1>
          <pre style={{ color: "#a1a1aa", fontSize: "0.8rem", maxWidth: "600px", overflow: "auto" }}>{this.state.error?.message}</pre>
          <button onClick={() => window.location.reload()} style={{ padding: "0.5rem 1rem", borderRadius: "0.375rem", background: "#27272a", color: "#fafafa", border: "none", cursor: "pointer" }}>
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
);
