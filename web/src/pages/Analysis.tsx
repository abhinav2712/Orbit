import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getAnalysis, type AnalysisResult } from "../lib/api";
import ProgressStream from "../components/ProgressStream";
import YamlViewer from "../components/YamlViewer";
import ArchMap from "../components/ArchMap";
import Checklist from "../components/Checklist";

type Tab = "architecture" | "yaml" | "checklist" | "report";

export default function Analysis() {
  const { slug } = useParams<{ slug: string }>();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [tab, setTab] = useState<Tab>("architecture");
  const [loading, setLoading] = useState(true);

  async function refetch() {
    if (!slug) return;
    setResult(await getAnalysis(slug));
    setLoading(false);
  }

  useEffect(() => {
    refetch(); /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [slug]);

  if (loading || !result) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-20 text-center text-slate-500">
        Loading…
      </div>
    );
  }

  const isRunning = !["done", "failed"].includes(result.status);

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <Link to="/" className="text-sm text-slate-400 hover:text-accent">
        ← Orbit
      </Link>

      <div className="flex items-center gap-2 mt-4 mb-1">
        <span
          className={`w-2 h-2 rounded-full ${
            result.status === "done"
              ? "bg-success"
              : result.status === "failed"
                ? "bg-red-500"
                : "bg-info animate-pulse"
          }`}
        />
        <span className="text-xs uppercase tracking-wide text-slate-400">
          {result.status}
        </span>
      </div>

      <h1 className="text-xl font-mono-code mt-4 mb-1">
        {result.facts_summary?.repo_url ?? slug}
      </h1>
      <p className="text-xs text-slate-500 mb-8">
        {result.facts_summary?.head_sha?.slice(0, 7)} ·{" "}
        {new Date(result.created_at).toLocaleString()}
      </p>

      {isRunning && (
        <ProgressStream
          analysisId={result.id}
          currentStatus={result.status}
          onFinished={refetch}
        />
      )}

      {result.status === "failed" && (
        <div className="bg-red-950/40 border border-red-900 rounded-lg p-6 text-center">
          <p className="text-red-300 font-medium mb-1">Analysis failed</p>
          <p className="text-sm text-red-400/80">{result.error}</p>
        </div>
      )}

      {result.status === "done" && (
        <div>
          <div className="flex gap-1 border-b border-slate-800 mb-6">
            {(["architecture", "yaml", "checklist", "report"] as Tab[]).map(
              (t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2 text-sm capitalize border-b-2 transition ${
                    tab === t
                      ? "border-accent text-accent"
                      : "border-transparent text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {t === "yaml" ? "zerops.yaml" : t}
                </button>
              ),
            )}
          </div>
          {tab === "architecture" && result.services && (
            <ArchMap services={result.services} />
          )}
          {tab === "yaml" && result.zerops_yaml && (
            <YamlViewer
              yaml={result.zerops_yaml}
              slug={result.slug}
              services={result.services}
            />
          )}
          {tab === "checklist" && result.checklist && (
            <Checklist analysisId={result.id} steps={result.checklist} />
          )}
          {tab === "report" && (
            <pre className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono-code text-xs overflow-x-auto">
              {JSON.stringify(result.facts_summary, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
