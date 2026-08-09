import type { ServiceProposal } from "../lib/api";

interface Props {
  service: ServiceProposal | null;
  onClose: () => void;
}

export default function ServiceInspector({ service, onClose }: Props) {
  if (!service) return null;
  return (
    <div className="absolute top-4 right-4 w-80 bg-slate-900 border border-slate-700 rounded-lg p-4 shadow-xl">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-mono-code text-accent">{service.name}</h3>
          <p className="text-xs text-slate-500 uppercase tracking-wide">
            {service.role}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300"
        >
          ✕
        </button>
      </div>
      <p className="text-xs text-slate-500 mb-1">Zerops type</p>
      <p className="font-mono-code text-sm mb-3">{service.zerops_type}</p>
      <p className="text-xs text-slate-500 mb-1">Reasoning</p>
      <p className="text-sm text-slate-300">{service.reasoning}</p>
      {service.evidence_refs && service.evidence_refs.length > 0 && (
        <>
          <p className="text-xs text-slate-500 mt-3 mb-1">Evidence</p>
          <ul className="text-xs text-slate-400 font-mono-code flex flex-col gap-0.5">
            {service.evidence_refs.map((ref, i) => (
              <li key={i}>{ref}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
