import { useCallback, useRef, useState } from "react";
import { ErrorMessage } from "./components/ErrorMessage";
import { LoadingSkeleton } from "./components/LoadingSkeleton";
import { PatentDetail } from "./components/PatentDetail";
import { ResultsList } from "./components/ResultsList";
import { SearchBar } from "./components/SearchBar";
import { ApiError, getPatent, searchPatents } from "./services/api";
import type {
  PatentDetail as PatentDetailType,
  SearchMode,
  SearchResultItem,
} from "./types";

const RECENT_KEY = "paten:recentPatents";
const MAX_RECENT = 20;

function loadRecent(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

function saveRecent(numbers: string[]) {
  localStorage.setItem(RECENT_KEY, JSON.stringify(numbers.slice(0, MAX_RECENT)));
}

export default function App() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [liveSearch, setLiveSearch] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [searched, setSearched] = useState(false);
  const [fipsHint, setFipsHint] = useState<string | null>(null);
  const [recent, setRecent] = useState<string[]>(loadRecent);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detail, setDetail] = useState<PatentDetailType | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const runSearch = useCallback(async () => {
    const q = query.trim();
    if (q.length < 2) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setSearched(true);
    setFipsHint(
      liveSearch ? "Запрос к ФИПС и поиск по базе…" : "Поиск по локальной базе…",
    );

    try {
      const res = await searchPatents(q, 10, mode, liveSearch, controller.signal);
      if (controller.signal.aborted) return;
      setResults(res.results);
      setFipsHint(
        res.fips_message ??
          (res.total > 0 ? `Найдено: ${res.total}` : "Ничего не найдено"),
      );
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      const msg =
        e instanceof ApiError
          ? e.message
          : "Не удалось выполнить поиск. Проверьте, что бэкенд запущен.";
      setError(msg);
      setResults([]);
      setFipsHint(null);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [query, mode, liveSearch]);

  const openDetail = async (patentNumber: string) => {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetail(null);
    const updated = [patentNumber, ...recent.filter((n) => n !== patentNumber)];
    setRecent(updated);
    saveRecent(updated);
    try {
      const data = await getPatent(patentNumber);
      setDetail(data);
    } catch {
      setError("Не удалось загрузить карточку патента");
      setDetailOpen(false);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-navy text-white py-8 px-4 shadow-md">
        <div className="max-w-5xl mx-auto text-center">
          <h1 className="text-2xl sm:text-3xl font-bold mb-2">
            Paten — поиск патентов ФИПС
          </h1>
          <p className="text-white/80 text-sm sm:text-base max-w-xl mx-auto">
            Семантический поиск по базе патентов с подгрузкой данных с ФИПС
          </p>
        </div>
      </header>

      <main className="flex-1 px-4 py-8 max-w-5xl mx-auto w-full">
        <SearchBar
          value={query}
          onChange={setQuery}
          onSearch={runSearch}
          disabled={loading}
        />

        <div className="flex justify-center gap-2 mt-4 flex-wrap items-center">
          {(["hybrid", "semantic", "keyword"] as SearchMode[]).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                mode === m
                  ? "bg-accent text-white border-accent"
                  : "bg-white border-slate-200 text-slate-600 hover:border-accent"
              }`}
            >
              {m === "hybrid"
                ? "Гибрид"
                : m === "semantic"
                  ? "Смысл"
                  : "Текст"}
            </button>
          ))}
          <label className="flex items-center gap-2 text-sm text-slate-600 ml-2">
            <input
              type="checkbox"
              checked={liveSearch}
              onChange={(e) => setLiveSearch(e.target.checked)}
              className="rounded border-slate-300"
            />
            Живой поиск ФИПС
          </label>
        </div>

        {fipsHint && searched && !loading && (
          <p className="text-center text-sm text-slate-500 mt-3">{fipsHint}</p>
        )}

        {!searched && !loading && (
          <div className="mt-12 text-center text-slate-500 max-w-md mx-auto">
            <p className="mb-4">
              Введите запрос и нажмите «Найти патенты» или клавишу Enter.
            </p>
            {recent.length > 0 && (
              <div className="text-left bg-white rounded-xl p-4 border border-slate-100">
                <p className="text-sm font-medium text-navy mb-2">
                  Недавно просмотренные
                </p>
                <ul className="space-y-1">
                  {recent.map((num) => (
                    <li key={num}>
                      <button
                        type="button"
                        className="text-accent text-sm hover:underline"
                        onClick={() => openDetail(num)}
                      >
                        {num}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="mt-8">
          {loading && <LoadingSkeleton />}
          {error && !loading && (
            <ErrorMessage message={error} onRetry={runSearch} />
          )}
          {!loading && !error && searched && (
            <ResultsList
              results={results}
              onSelect={openDetail}
              showScores={import.meta.env.DEV}
            />
          )}
        </div>
      </main>

      {detailOpen && (
        <PatentDetail
          patent={detail}
          loading={detailLoading}
          onClose={() => setDetailOpen(false)}
        />
      )}

      <footer className="py-4 text-center text-xs text-slate-400">
        Личный сервис · данные ФИПС
      </footer>
    </div>
  );
}
