import type { PatentDetail as PatentDetailType } from "../types";

interface PatentDetailProps {
  patent: PatentDetailType | null;
  loading: boolean;
  onClose: () => void;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ru-RU");
}

export function PatentDetail({ patent, loading, onClose }: PatentDetailProps) {
  if (!patent && !loading) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-xl p-6"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-xl font-bold text-navy pr-4">
            {loading ? "Загрузка…" : patent?.title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-2xl leading-none"
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        {loading && (
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-slate-200 rounded w-1/3" />
            <div className="h-3 bg-slate-100 rounded w-full" />
            <div className="h-3 bg-slate-100 rounded w-full" />
          </div>
        )}

        {patent && !loading && (
          <div className="space-y-4 text-sm text-slate-700">
            <p className="font-mono text-accent">{patent.patent_number}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-slate-500">
              <span>Заявка: {formatDate(patent.application_date)}</span>
              <span>Публикация: {formatDate(patent.publication_date)}</span>
              <span>Статус: {patent.status || "—"}</span>
              <span>МПК: {patent.ipc_codes.join(", ") || "—"}</span>
            </div>
            {patent.applicants.length > 0 && (
              <p>
                <strong>Патентообладатели:</strong>{" "}
                {patent.applicants.join("; ")}
              </p>
            )}
            {patent.inventors.length > 0 && (
              <p>
                <strong>Авторы:</strong> {patent.inventors.join("; ")}
              </p>
            )}
            <section>
              <h3 className="font-semibold text-navy mb-1">Аннотация</h3>
              <p className="leading-relaxed">{patent.abstract}</p>
            </section>
            {patent.claims && (
              <section>
                <h3 className="font-semibold text-navy mb-1">Формула</h3>
                <p className="leading-relaxed whitespace-pre-wrap">
                  {patent.claims}
                </p>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
