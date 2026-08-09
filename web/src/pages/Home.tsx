import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import RepoInput from "../components/RepoInput";
import {
  createAnalysis,
  listGallery,
  type GalleryEntry,
  ORBIT_SELF_REPO_URL,
} from "../lib/api";

const STEPS = [
  {
    n: "01",
    title: "Paste a repo URL",
    detail:
      "Any public GitHub repo. Orbit shallow-clones it into a sandbox — nothing runs, nothing leaks.",
  },
  {
    n: "02",
    title: "Deterministic scan, then reasoning",
    detail:
      "A static scanner extracts languages, frameworks, ports, and datastores with file:line evidence. An agent reasons over those facts — never invents a service it can't point to.",
  },
  {
    n: "03",
    title: "Get a validated architecture",
    detail:
      "A schema-checked zerops.yaml, an interactive service map, and a migration checklist — ready to commit.",
  },
];

export default function Home() {
  const [gallery, setGallery] = useState<GalleryEntry[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    listGallery(6)
      .then(setGallery)
      .catch(() => setGallery([]));
  }, []);

  async function analyzeOrbitItself() {
    const { slug } = await createAnalysis(ORBIT_SELF_REPO_URL);
    navigate(`/a/${slug}`);
  }

  return (
    <div>
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
            <div
              className="orbit-ring"
              style={{ width: 420, height: 420, animationDuration: "32s" }}
            >
              <span
                className="orbit-dot"
                style={{
                  color: "var(--color-accent)",
                  background: "var(--color-accent)",
                }}
              />
            </div>
          </div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
            <div
              className="orbit-ring"
              style={{
                width: 640,
                height: 640,
                animationDuration: "48s",
                animationDirection: "reverse",
              }}
            >
              <span
                className="orbit-dot"
                style={{
                  color: "var(--color-info)",
                  background: "var(--color-info)",
                }}
              />
            </div>
          </div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
            <div
              className="orbit-ring"
              style={{ width: 860, height: 860, animationDuration: "64s" }}
            >
              <span
                className="orbit-dot"
                style={{
                  color: "var(--color-success)",
                  background: "var(--color-success)",
                }}
              />
            </div>
          </div>
        </div>

        <div className="relative max-w-4xl mx-auto px-6 pt-28 pb-20 flex flex-col items-center text-center gap-8">
          <span className="text-xs uppercase tracking-[0.2em] text-accent font-medium">
            Built for Zerops
          </span>
          <div>
            <h1 className="text-5xl sm:text-6xl font-semibold tracking-tight">
              Orbit
            </h1>
            <p className="text-slate-400 mt-4 text-lg max-w-xl mx-auto">
              Point Orbit at any repo. Get a launch-ready Zerops architecture in
              60 seconds.
            </p>
          </div>

          <RepoInput />

          <button
            onClick={analyzeOrbitItself}
            className="flex items-center gap-2 text-sm bg-slate-900 border border-slate-800 hover:border-accent
                       text-slate-300 hover:text-accent transition rounded-full px-4 py-2"
          >
            🪞 Watch Orbit analyze Orbit
          </button>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-6 py-16 border-t border-slate-900">
        <h2 className="text-xs uppercase tracking-wide text-slate-500 mb-8 text-center">
          How it works
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {STEPS.map((step) => (
            <div key={step.n} className="flex flex-col gap-2">
              <span className="font-mono-code text-accent text-sm">
                {step.n}
              </span>
              <h3 className="font-medium">{step.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                {step.detail}
              </p>
            </div>
          ))}
        </div>
      </section>

      {gallery.length > 0 && (
        <section className="max-w-4xl mx-auto px-6 pb-24">
          <div className="flex items-center justify-between mb-4 pt-8 border-t border-slate-900">
            <h2 className="text-xs uppercase tracking-wide text-slate-500">
              Recent analyses
            </h2>
            <Link to="/gallery" className="text-sm text-accent hover:underline">
              View all
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {gallery.map((g) => (
              <Link
                key={g.slug}
                to={`/a/${g.slug}`}
                className="block bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 hover:border-accent transition"
              >
                <p className="font-mono-code text-sm truncate">{g.repo_url}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {new Date(g.created_at).toLocaleString()}
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
