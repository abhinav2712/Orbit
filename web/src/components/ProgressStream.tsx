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
const STAGE_LABEL: Record<string, string> = {
  queued: "Queued",
  cloning: "Cloning",
  scanning: "Scanning",
  reasoning: "Architecting",
  validating: "Validating",
  done: "Done",
};

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

  const currentIndex = Math.max(
    0,
    STAGES.indexOf(status as (typeof STAGES)[number]),
  );
  const fillPercent = (currentIndex / (STAGES.length - 1)) * 100;

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <div className="relative mb-10">
        <div className="absolute top-[7px] left-0 right-0 h-px bg-slate-800" />
        <div
          className="absolute top-[7px] left-0 h-px bg-accent transition-all duration-700 ease-out"
          style={{ width: `${fillPercent}%` }}
        />
        <div className="relative flex items-center justify-between">
          {STAGES.map((stage, i) => (
            <div key={stage} className="flex flex-col items-center gap-2">
              <div
                className={`w-[14px] h-[14px] rounded-full border-2 transition-all duration-500 ${
                  i < currentIndex
                    ? "bg-accent border-accent"
                    : i === currentIndex
                      ? "bg-slate-950 border-accent stage-active"
                      : "bg-slate-950 border-slate-700"
                }`}
              />
              <span
                className={`text-xs transition-colors ${i <= currentIndex ? "text-slate-200" : "text-slate-600"}`}
              >
                {STAGE_LABEL[stage]}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div
        className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono-code text-sm
                       max-h-64 overflow-y-auto flex flex-col gap-1.5"
      >
        {log.length === 0 && (
          <span className="text-slate-600 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            Waiting for progress…
          </span>
        )}
        {log.map((e, i) => (
          <div
            key={i}
            className="text-slate-400 animate-[fadeIn_0.3s_ease-out]"
          >
            <span className="text-accent">[{e.status}]</span> {e.message}
          </div>
        ))}
      </div>
    </div>
  );
}
