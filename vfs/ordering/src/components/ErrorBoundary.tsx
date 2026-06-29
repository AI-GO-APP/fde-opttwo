import React from "react";

interface State { hasError: boolean; message: string; }

export default class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(err: any): State {
    return { hasError: true, message: err?.message || String(err) };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24, color: "#b91c1c" }}>
          <h3>發生錯誤</h3>
          <pre style={{ whiteSpace: "pre-wrap" }}>{this.state.message}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}
