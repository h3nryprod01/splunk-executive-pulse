"use client";

// App Router error boundary — catches render errors in any page/component
// so a single failing card never white-screens the whole dashboard.
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="max-w-md w-full bg-card border border-border rounded-2xl p-8 text-center">
        <div className="text-3xl mb-3">⚠️</div>
        <h2 className="text-lg font-semibold text-white mb-2">
          Something went wrong
        </h2>
        <p className="text-sm text-dim mb-6 font-mono break-words">
          {error.message || "Unexpected rendering error"}
        </p>
        <button
          onClick={reset}
          className="px-5 py-2.5 rounded-xl bg-splunk hover:bg-splunk-dark text-bg font-medium transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
