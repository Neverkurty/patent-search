interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="max-w-lg mx-auto text-center bg-red-50 border border-red-100 rounded-xl p-6">
      <p className="text-red-800 font-medium mb-2">{message}</p>
      <p className="text-red-600 text-sm mb-4">
        Сервер временно недоступен или произошла ошибка сети.
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
        >
          Повторить попытку
        </button>
      )}
    </div>
  );
}
