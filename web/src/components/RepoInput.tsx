import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAnalysis } from "../lib/api";

export default function RepoInput() {
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/.test(url.trim())) {
      setError(
        "Enter a public GitHub repo URL, e.g. https://github.com/owner/repo",
      );
      return;
    }
    setSubmitting(true);
    try {
      const { slug } = await createAnalysis(url.trim());
      navigate(`/a/${slug}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 w-full max-w-xl"
    >
      <div className="flex gap-2">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm font-mono-code
                     placeholder:text-slate-600 focus:outline-none focus:border-accent"
          disabled={submitting}
        />
        <button
          type="submit"
          disabled={submitting || !url.trim()}
          className="bg-accent text-slate-950 font-medium px-6 py-3 rounded-lg
                     hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          {submitting ? "Analyzing…" : "Analyze"}
        </button>
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
    </form>
  );
}
