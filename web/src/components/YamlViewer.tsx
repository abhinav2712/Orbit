import { useState } from "react";

interface Props {
  yaml: string;
  slug: string;
  services: { name: string; role: string; reasoning: string }[] | null;
}

export default function YamlViewer({ yaml, services }: Props) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(yaml);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function handleDownload() {
    const blob = new Blob([yaml], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "zerops.yaml";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <button
          onClick={handleCopy}
          className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-md transition"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
        <button
          onClick={handleDownload}
          className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1.5 rounded-md transition"
        >
          Download zerops.yaml
        </button>
      </div>
      <pre className="bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono-code text-sm overflow-x-auto leading-relaxed">
        {yaml}
      </pre>
      {services && services.length > 0 && (
        <div className="mt-4 flex flex-col gap-2">
          <h3 className="text-xs uppercase tracking-wide text-slate-500">
            Why each block exists
          </h3>
          {services.map((s) => (
            <div
              key={s.name}
              className="bg-slate-900/60 border border-slate-800 rounded-md px-3 py-2 text-sm"
            >
              <span className="font-mono-code text-accent">{s.name}</span>
              <span className="text-slate-500"> ({s.role})</span>
              <p className="text-slate-400 mt-1">{s.reasoning}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
