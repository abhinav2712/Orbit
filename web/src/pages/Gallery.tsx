import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listGallery, type GalleryEntry } from "../lib/api";

export default function Gallery() {
  const [gallery, setGallery] = useState<GalleryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listGallery(50)
      .then(setGallery)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <Link to="/" className="text-sm text-slate-400 hover:text-accent">
        ← Home
      </Link>
      <h1 className="text-2xl font-semibold mt-4 mb-8">All analyses</h1>
      {loading && <p className="text-slate-500">Loading…</p>}
      {!loading && gallery.length === 0 && (
        <p className="text-slate-500">No public analyses yet.</p>
      )}
      <div className="flex flex-col gap-2">
        {gallery.map((g) => (
          <Link
            key={g.slug}
            to={`/a/${g.slug}`}
            className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 hover:border-accent transition"
          >
            <span className="font-mono-code text-sm">{g.repo_url}</span>
            <span className="text-xs text-slate-500">
              {new Date(g.created_at).toLocaleString()}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
