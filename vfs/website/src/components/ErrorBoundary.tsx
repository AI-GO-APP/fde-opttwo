import React from "react";

interface State {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(err: unknown): State {
    return { hasError: true, message: err instanceof Error ? err.message : String(err) };
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="error-screen">
          <h1>頁面載入失敗</h1>
          <pre>{this.state.message}</pre>
        </main>
      );
    }

    return this.props.children;
  }
}
