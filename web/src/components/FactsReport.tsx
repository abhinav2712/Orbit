import type { FactsSummary, Fact, PortFact, Evidence } from "../lib/api";

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  return (
    <div className="mt-1.5 flex flex-col gap-1">
      {evidence.slice(0, 3).map((e, i) => (
        <div
          key={i}
          className="text-xs font-mono-code text-slate-500 bg-slate-950/60 rounded px-2 py-1"
        >
          <span className="text-accent">
            {e.file}:{e.line}
          </span>
          {e.snippet && <span className="text-slate-600"> — {e.snippet}</span>}
        </div>
      ))}
      {evidence.length > 3 && (
        <span className="text-xs text-slate-600">
          +{evidence.length - 3} more
        </span>
      )}
    </div>
  );
}

function FactSection({ title, facts }: { title: string; facts: Fact[] }) {
  if (facts.length === 0) return null;
  return (
    <div>
      <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-2">
        {title}
      </h3>
      <div className="flex flex-col gap-2">
        {facts.map((f, i) => (
          <div
            key={i}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2"
          >
            <span className="text-sm font-medium">{f.value}</span>
            <EvidenceList evidence={f.evidence} />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function FactsReport({ facts }: { facts: FactsSummary }) {
  const nothingDetected =
    facts.languages.length === 0 && facts.frameworks.length === 0;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4 text-sm text-slate-400">
        <span className="font-mono-code">{facts.head_sha?.slice(0, 7)}</span>
        {facts.has_dockerfile && (
          <span className="text-xs bg-slate-900 border border-slate-800 rounded-full px-2 py-0.5">
            Dockerfile present
          </span>
        )}
        {facts.static_output_dir && (
          <span className="text-xs bg-slate-900 border border-slate-800 rounded-full px-2 py-0.5">
            Static output: {facts.static_output_dir}
          </span>
        )}
      </div>

      <FactSection title="Languages" facts={facts.languages} />
      <FactSection title="Frameworks" facts={facts.frameworks} />

      {facts.ports.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wide text-slate-500 mb-2">
            Ports
          </h3>
          <div className="flex flex-col gap-2">
            {facts.ports.map((p: PortFact, i) => (
              <div
                key={i}
                className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2"
              >
                <span className="text-sm font-mono-code text-accent">
                  {p.port}
                </span>
                <EvidenceList evidence={p.evidence} />
              </div>
            ))}
          </div>
        </div>
      )}

      <FactSection title="Datastores" facts={facts.datastores} />
      <FactSection title="Queues" facts={facts.queues} />
      <FactSection title="Storage" facts={facts.storage} />
      <FactSection title="Build commands" facts={facts.build_commands} />
      <FactSection title="Environment variables" facts={facts.env_vars} />

      {nothingDetected && (
        <p className="text-sm text-slate-500">
          No languages or frameworks detected — this repo's stack may not be
          covered by Orbit's scanner yet.
        </p>
      )}
    </div>
  );
}
