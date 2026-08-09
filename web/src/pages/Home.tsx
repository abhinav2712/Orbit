import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import RepoInput from "../components/RepoInput";
import {
  createAnalysis,
  listGallery,
  type GalleryEntry,
  ORBIT_SELF_REPO_URL,
} from "../lib/api";

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
    <div className="max-w-4xl mx-auto px-6 py-20 flex flex-col items-center text-center gap-8">
      <div>
        <h1 className="text-4xl font-semibold tracking-tight">Orbit</h1>
        <p className="text-slate-400 mt-3 text-lg">
          Point Orbit at any repo. Get a launch-ready Zerops architecture in 60
          seconds.
        </p>
      </div>
      <RepoInput />
      <button
        onClick={analyzeOrbitItself}
        className="text-sm text-slate-400 hover:text-accent transition underline underline-offset-4"
      >
        🪞 Watch Orbit analyze Orbit
      </button>
      {gallery.length > 0 && (
        <div className="w-full mt-16 text-left">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm uppercase tracking-wide text-slate-500">
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
        </div>
      )}
    </div>
  );
}
