/* Small motion helpers. One easing everywhere; motion only where it shows a change. */
import { useToasts } from './toasts'

export function Toasts() {
  const list = useToasts((s) => s.list)
  return (
    <div className="toasts" aria-live="polite">
      {list.map((t) => (
        <div key={t.id} className={`toast ${t.out ? 'out' : ''}`}>
          {t.html}
        </div>
      ))}
    </div>
  )
}
