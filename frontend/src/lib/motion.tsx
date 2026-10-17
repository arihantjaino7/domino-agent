/* Motion primitives for React, following the Rekora motion guide: one easing, motion with a job. */
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { create } from 'zustand'

const reduced = () => typeof window !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

/** Headline whose words rise out of their own masks. Re-plays when the text changes. */
export function SplitHeadline({ lead, soft }: { lead: string; soft?: string }) {
  let k = 0
  const words = (text: string, cls?: string) =>
    text.split(/(\s+)/).map((part, i) =>
      /^\s+$/.test(part) || !part ? (
        part
      ) : (
        <span key={`${cls}-${i}`} className="w" aria-hidden>
          <span className={cls} style={{ ['--k' as string]: k++ }}>
            {part}
          </span>
        </span>
      ),
    )
  return (
    <h1 key={`${lead}|${soft}`} aria-label={`${lead} ${soft ?? ''}`.trim()}>
      {words(lead)}
      {soft && (
        <>
          {' '}
          <em>{words(soft)}</em>
        </>
      )}
    </h1>
  )
}

/** Number that counts from its previous value to the new one with an exponential ease-out. */
export function CountUp({ value, format }: { value: number | null | undefined; format: (n: number) => string }) {
  const [shown, setShown] = useState<number | null>(value ?? null)
  const from = useRef<number>(value ?? 0)
  const first = useRef(true)
  useEffect(() => {
    if (value == null) {
      setShown(null)
      return
    }
    if (reduced()) {
      setShown(value)
      from.current = value
      return
    }
    const start = from.current
    const dur = first.current ? 1500 : 900
    first.current = false
    const t0 = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / dur)
      const e = p === 1 ? 1 : 1 - Math.pow(2, -10 * p)
      setShown(start + (value - start) * e)
      if (p < 1) raf = requestAnimationFrame(tick)
      else from.current = value
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value])
  return <>{shown == null ? '—' : format(Math.round(shown))}</>
}

/** Segmented control with the sliding pill indicator. */
export function Seg<T extends string | boolean>({
  options,
  value,
  onChange,
  disabled,
  label,
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
  disabled?: boolean
  label: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const ind = useRef<HTMLSpanElement>(null)
  const move = () => {
    const on = ref.current?.querySelector<HTMLButtonElement>(':scope > button.on')
    if (!on || !ind.current) return
    ind.current.style.width = `${on.offsetWidth}px`
    ind.current.style.height = `${on.offsetHeight}px`
    ind.current.style.transform = `translate(${on.offsetLeft}px, ${on.offsetTop}px)`
  }
  useLayoutEffect(move)
  useEffect(() => {
    void document.fonts?.ready.then(move)
    addEventListener('resize', move)
    return () => removeEventListener('resize', move)
  })
  return (
    <div ref={ref} className="seg" role="radiogroup" aria-label={label}>
      <span ref={ind} className="ind" aria-hidden />
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          className={o.value === value ? 'on' : ''}
          disabled={disabled}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Pill button with rolling label, ripple and a magnetic pull. */
export function Btn({
  children,
  variant = 'primary',
  shine,
  icon,
  arrow,
  className = '',
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'accent'
  shine?: boolean
  icon?: ReactNode
  arrow?: boolean
}) {
  const ref = useRef<HTMLButtonElement>(null)
  const label = typeof children === 'string' ? children : null
  const onMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (reduced() || rest.disabled) return
    const r = e.currentTarget.getBoundingClientRect()
    e.currentTarget.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.18}px, ${(e.clientY - r.top - r.height / 2) * 0.25}px)`
  }
  const onLeave = (e: React.PointerEvent<HTMLButtonElement>) => {
    e.currentTarget.style.transform = ''
  }
  const onDown = (e: React.MouseEvent) => {
    if (reduced() || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    const d = Math.max(r.width, r.height) * 2
    const s = document.createElement('span')
    s.className = 'ripple'
    s.style.cssText = `width:${d}px;height:${d}px;left:${e.clientX - r.left - d / 2}px;top:${e.clientY - r.top - d / 2}px`
    ref.current.append(s)
    setTimeout(() => s.remove(), 800)
  }
  return (
    <button
      ref={ref}
      type="button"
      {...rest}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
      onMouseDown={onDown}
      className={`btn btn-${variant} ${shine ? 'btn-shine' : ''} ${className}`}
    >
      {icon}
      {label ? (
        <span className="roll">
          <b data-t={label}>{label}</b>
        </span>
      ) : (
        children
      )}
      {arrow && <span className="arr">→</span>}
    </button>
  )
}

/** Card spotlight that follows the pointer. */
export function spotHandlers() {
  return {
    onPointerMove: (e: React.PointerEvent<HTMLElement>) => {
      const r = e.currentTarget.getBoundingClientRect()
      e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`)
      e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`)
    },
  }
}

/* ---------- toasts ---------- */
interface Toast { id: number; html: ReactNode; out?: boolean }
export const useToasts = create<{ list: Toast[]; push: (html: ReactNode) => void }>((set, get) => ({
  list: [],
  push: (html) => {
    const id = Date.now() + Math.random()
    set({ list: [...get().list.slice(-2), { id, html }] })
    setTimeout(() => set({ list: get().list.map((t) => (t.id === id ? { ...t, out: true } : t)) }), 5200)
    setTimeout(() => set({ list: get().list.filter((t) => t.id !== id) }), 5700)
  },
}))
export function Toasts() {
  const list = useToasts((s) => s.list)
  return (
    <div className="toasts" aria-live="polite">
      {list.map((t) => (
        <div key={t.id} className={`toast ${t.out ? 'out' : ''}`}>
          <i aria-hidden>
            <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M2.5 6.5l2.5 2.5 4.5-6" />
            </svg>
          </i>
          <span>{t.html}</span>
        </div>
      ))}
    </div>
  )
}

/* ---------- page wipe ---------- */
export const useWipe = create<{ run: number; num: string; name: string; play: (num: string, name: string) => void }>(
  (set, get) => ({
    run: 0,
    num: '',
    name: '',
    play: (num, name) => {
      if (reduced()) return
      set({ run: get().run + 1, num, name })
    },
  }),
)
export function Wipe() {
  const { run, num, name } = useWipe()
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el || !run) return
    el.classList.remove('run')
    void el.offsetWidth
    el.classList.add('run')
    const t = setTimeout(() => el.classList.remove('run'), 1150)
    return () => clearTimeout(t)
  }, [run])
  return (
    <div ref={ref} className="wipe" aria-hidden>
      <b>
        <span>{num}</span>
        <em>{name}</em>
      </b>
    </div>
  )
}

/* ---------- first-load curtain ---------- */
export function Loader({ ready, onOut }: { ready: boolean; onOut?: () => void }) {
  const [p, setP] = useState(0)
  const [out, setOut] = useState(reduced())
  const [gone, setGone] = useState(reduced())
  useEffect(() => {
    if (reduced()) onOut?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    if (gone) return
    const t0 = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const x = Math.min(1, (now - t0) / 1400)
      setP(1 - Math.pow(1 - x, 3))
      if (x < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [gone])
  // Timers, not animation frames, decide when the curtain lifts: rAF pauses in background tabs.
  const [minDone, setMinDone] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setMinDone(true), 1500)
    const cap = setTimeout(() => setMinDone(true), 6000)
    return () => {
      clearTimeout(t)
      clearTimeout(cap)
    }
  }, [])
  useEffect(() => {
    if (!minDone || out || !ready) return
    const a = setTimeout(() => {
      setP(1)
      setOut(true)
      onOut?.()
      setTimeout(() => setGone(true), 1200)
    }, 150)
    return () => clearTimeout(a)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minDone, ready, out])
  if (gone) return null
  return (
    <div className={`loader ${out ? 'out' : ''}`} aria-hidden>
      <div className="lw">
        <div className="lword">
          {'DOMINO'.split('').map((c, i) => (
            <span key={i} style={{ ['--i' as string]: i }}>
              {c}
            </span>
          ))}
        </div>
        <div className="lmeta">
          <span>{ready ? 'World graph ready' : 'Loading world graph'}</span>
          <div className="lline">
            <i style={{ transform: `scaleX(${p})` }} />
          </div>
          <span>{String(Math.round(p * 100)).padStart(3, '0')}</span>
        </div>
      </div>
    </div>
  )
}
