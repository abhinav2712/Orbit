import { useEffect, useState } from "react";
import { streamAnalysisEvents, type ProgressEvent } from "../lib/api";

const STAGES = [
  "queued",
  "cloning",
  "scanning",
  "reasoning",
  "validating",
  "done",
] as const;

interface Props {
  analysisId: string;
  currentStatus: string;
  onFinished: () => void;
}

export default function ProgressStream({
  analysisId,
  currentStatus,
  onFinished,
}: Props) {
  const [log, setLog] = useState<ProgressEvent[]>([]);
  const [status, setStatus] = useState(currentStatus);

  useEffect(() => {
    if (status === "done" || status === "failed") {
      onFinished();
      return;
    }
    const close = streamAnalysisEvents(
      analysisId,
      (event) => {
        setStatus(event.status);
        setLog((prev) => [...prev, event]);
      },
      onFinished,
    );
    return close;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysisId]);

  const currentIndex = STAGES.indexOf(status as (typeof STAGES)[number]);

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <div className="flex items-center justify-between mb-8">
        {STAGES.map((stage, i) => (
          <div key={stage} className="flex-1 flex flex-col items-center">
            <div
              className={`w-3 h-3 rounded-full transition ${
                i < currentIndex
                  ? "bg-accent"
                  : i === currentIndex
                    ? "bg-accent animate-pulse"
                    : "bg-slate-700"
              }`}
            />
            <span
              className={`text-xs mt-2 ${i <= currentIndex ? "text-slate-300" : "text-slate-600"}`}
            >
              {stage}
            </span>
          </div>
        ))}
      </div>
      <div
        className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono-code text-sm
                       max-h-64 overflow-y-auto flex flex-col gap-1"
      >
        {log.length === 0 && (
          <span className="text-slate-600">Waiting for progress…</span>
        )}
        {log.map((e, i) => (
          <div key={i} className="text-slate-400">
            <span className="text-accent">[{e.status}]</span> {e.message}
          </div>
        ))}
      </div>
    </div>
  );
}
