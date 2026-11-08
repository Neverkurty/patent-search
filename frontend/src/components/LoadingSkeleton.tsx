export function LoadingSkeleton() {
  return (
    <div className="space-y-4 max-w-4xl mx-auto w-full">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="animate-pulse bg-white rounded-xl p-5 border border-slate-100 shadow-sm"
        >
          <div className="h-4 bg-slate-200 rounded w-1/4 mb-3" />
          <div className="h-5 bg-slate-200 rounded w-3/4 mb-2" />
          <div className="h-3 bg-slate-100 rounded w-full mb-1" />
          <div className="h-3 bg-slate-100 rounded w-5/6" />
        </div>
      ))}
    </div>
  );
}
