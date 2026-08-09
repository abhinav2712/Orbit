import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listGallery, deleteAnalysis, type GalleryEntry } from "../lib/api";

export default function Gallery() {
  const [gallery, setGallery] = useState<GalleryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listGallery(50)
      .then(setGallery)
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(e: React.MouseEvent, slug: string) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Delete this analysis? This cannot be undone.")) return;
    await deleteAnalysis(slug);
    setGallery((prev) => prev.filter((g) => g.slug !== slug));
  }

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
            className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 hover:border-accent transition group"
          >
            <span className="font-mono-code text-sm">{g.repo_url}</span>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">
                {new Date(g.created_at).toLocaleString()}
              </span>
              <button
                onClick={(e) => handleDelete(e, g.slug)}
                className="text-xs text-slate-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition px-2 py-1"
                title="Delete analysis"
              >
                Delete
              </button>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
