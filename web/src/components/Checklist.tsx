import { useState } from "react";
import { type ChecklistStep, toggleChecklistStep } from "../lib/api";

const PHASE_LABEL: Record<string, string> = {
  before_deploy: "Before deploy",
  deploy: "Deploy",
  after_deploy: "After deploy",
};

export default function Checklist({
  analysisId,
  steps,
}: {
  analysisId: string;
  steps: ChecklistStep[];
}) {
  const [checked, setChecked] = useState<Record<string, boolean>>(
    Object.fromEntries(steps.map((s) => [s.step_id, !!s.checked])),
  );

  async function handleToggle(stepId: string) {
    setChecked((prev) => ({ ...prev, [stepId]: !prev[stepId] }));
    try {
      await toggleChecklistStep(analysisId, stepId);
    } catch {
      setChecked((prev) => ({ ...prev, [stepId]: !prev[stepId] }));
    }
  }

  const phases: (keyof typeof PHASE_LABEL)[] = [
    "before_deploy",
    "deploy",
    "after_deploy",
  ];

  return (
    <div className="flex flex-col gap-6">
      {phases.map((phase) => {
        const phaseSteps = steps.filter((s) => s.phase === phase);
        if (phaseSteps.length === 0) return null;
        return (
          <div key={phase}>
            <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-2">
              {PHASE_LABEL[phase]}
            </h3>
            <div className="flex flex-col gap-2">
              {phaseSteps.map((step) => (
                <label
                  key={step.step_id}
                  className="flex gap-3 items-start bg-slate-900 border border-slate-800
                             rounded-lg px-4 py-3 cursor-pointer hover:border-slate-700 transition"
                >
                  <input
                    type="checkbox"
                    checked={!!checked[step.step_id]}
                    onChange={() => handleToggle(step.step_id)}
                    className="mt-1 accent-accent"
                  />
                  <div>
                    <p
                      className={`text-sm font-medium ${checked[step.step_id] ? "line-through text-slate-500" : ""}`}
                    >
                      {step.title}
                    </p>
                    <p className="text-sm text-slate-400 mt-0.5">
                      {step.detail}
                    </p>
                    {step.docs_url && (
                      <a
                        href={step.docs_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-accent hover:underline mt-1 inline-block"
                      >
                        Zerops docs →
                      </a>
                    )}
                  </div>
                </label>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
