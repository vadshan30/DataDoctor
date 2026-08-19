export function LoadingSpinner() { return <div className="loading-state"><span className="spinner" />Loading…</div>; }
export function ErrorMessage({ message }: { message: string }) { return <div className="error-message" role="alert">{message}</div>; }
export function EmptyState({ title, body }: { title: string; body: string }) { return <div className="empty-state"><div className="empty-icon">∅</div><h3>{title}</h3><p>{body}</p></div>; }
