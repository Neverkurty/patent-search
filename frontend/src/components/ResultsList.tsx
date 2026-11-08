import type { SearchResultItem } from "../types";

function truncate(text: string, max = 200): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max).trim()}…`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("ru-RU");
  } catch {
    return iso;
  }
}

interface ResultsListProps {
  results: SearchResultItem[];
  onSelect: (patentNumber: string) => void;
  showScores?: boolean;
}

export function ResultsList({
  results,
  onSelect,
  showScores = false,
}: ResultsListProps) {
  if (results.length === 0) {
    return (
      <p className="text-center text-slate-500 py-8">
        По вашему запросу ничего не найдено. Попробуйте другие ключевые слова.
      </p>
    );
  }

  return (
    <ul className="space-y-4 max-w-4xl mx-auto w-full">
      {results.map(({ patent, scores }) => (
        <li
          key={patent.patent_number}
          className="bg-white rounded-xl p-5 border border-slate-100 shadow-sm hover:border-accent/30 transition-colors"
        >
          <button
            type="button"
            onClick={() => onSelect(patent.patent_number)}
            className="text-left w-full"
          >
            <span className="text-accent font-mono text-sm hover:underline">
              {patent.patent_number}
            </span>
            <h3 className="text-lg font-semibold text-navy mt-1 mb-2">
              {patent.title}
            </h3>
            <div className="flex flex-wrap gap-3 text-sm text-slate-500 mb-2">
              <span>Опубликован: {formatDate(patent.publication_date)}</span>
              {patent.status && <span>Статус: {patent.status}</span>}
              {patent.ipc_codes.length > 0 && (
                <span>МПК: {patent.ipc_codes.join(", ")}</span>
              )}
            </div>
            <p className="text-slate-600 text-sm leading-relaxed">
              {truncate(patent.abstract)}
            </p>
            {showScores && (
              <p className="text-xs text-slate-400 mt-2">
                score: {scores.final.toFixed(4)}
                {scores.semantic != null &&
                  ` · sem: ${scores.semantic.toFixed(4)}`}
                {scores.keyword != null &&
                  ` · kw: ${scores.keyword.toFixed(4)}`}
              </p>
            )}
          </button>
        </li>
      ))}
    </ul>
  );
}
