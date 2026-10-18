import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { ViewId } from '../App'
import { plural, usd, useModel, type Model } from '../lib/model'
import { LAST_STEP, OPENS_AT, VIEW_NAMES } from '../lib/guide'
import { STEPS, currentStep, useStore } from '../lib/store'
import { useToasts } from '../lib/toasts'

/* eslint-disable @typescript-eslint/no-explicit-any */

/*
 * Guided path: one real Monsoon run, told in ten steps. Only the Overview is open at first; each view opens
 * at the step that needs it, and stays open. Steps move on by themselves when the visitor does the thing
 * (starts the run, approves, fast-forwards), so the guide follows real state instead of a script.
 */

type Ctx = { m: Model; view: ViewId; runId: string | null; late: string[] }
type Step = {
  view: ViewId
  title: (c: Ctx) => string
  body: (c: Ctx) => string
  target?: () => Element | null
  /** the guide moves on by itself once this is true */
  done?: (c: Ctx) => boolean
  /** shown while the visitor or DOMINO still has to do something */
  waiting?: (c: Ctx) => string | null
  action?: (c: Ctx) => { label: string; run: () => void } | null
  next?: boolean
}

const q = (sel: string) => () => [...document.querySelectorAll(sel)].find((e) => e.getBoundingClientRect().width > 0) ?? null
const byText = (sel: string, re: RegExp) => () => [...document.querySelectorAll(sel)].find((e) => re.test(e.textContent ?? '') && e.getBoundingClientRect().width > 0) ?? null
const cardWith = (re: RegExp) => () => {
  const h = byText('h2, h3, summary', re)()
  return h?.closest('.card, details') ?? h
}

export function Guide({ view, go }: { view: ViewId; go: (v: ViewId) => void }) {
  const st = useStore()
  const m = useModel()
  const [rect, setRect] = useState<DOMRect | null>(null)
  // made smaller on this step; the next step opens the card again
  const [minAt, setMinAt] = useState<number | null>(null)
  const guided = st.experience === 'guided'
  const step = st.guideStep

  const T = m.totals
  const late: string[] = (m.delivery?.pos ?? []).filter((p: any) => p.days_late > 0).map((p: any) => p.site_name ?? p.site)
  const ctx: Ctx = { m, view, runId: st.runId, late }
  const startDemo = () => { st.setMode('scripted'); st.setScenario('monsoon'); void st.run() }

  const steps: Step[] = [
    { view: 'overview', target: q('.ov-hero'),
      title: () => (st.guideMax > 0 ? 'Pick up where you left off' : 'A quiet morning at Kestrel Devices'),
      body: (c) => `${st.guideMax > 0 ? 'Your earlier run ended when the page reloaded; everything you opened stays open. ' : ''}Kestrel builds laptops from ${c.m.totals?.orders ?? 117} customer orders, all on time. Its dashboard watches only the suppliers it pays directly. Now a monsoon floods central Thailand.`,
      action: () => ({ label: 'Start the flood', run: () => { startDemo(); advance() } }) },
    { view: 'overview', target: q('.map-card'),
      title: () => 'DOMINO is investigating',
      body: () => 'It reads the alert, finds the flooded places in the graph, and follows supply paths from the flood to your suppliers, factories and customer orders. Try the "Tier-1 view" switch above the map: that is all a normal dashboard sees.',
      waiting: () => { const s = STEPS.find((x) => x.id === currentStep(st)); return s ? `Working on step ${Number(s.num)} of 7: ${s.title}` : 'Starting' },
      done: (c) => c.m.phase === 'awaiting' },
    { view: 'overview', target: q('.ov-nums'),
      title: () => `${T?.exposed ?? '—'} orders in danger, ${T?.projected_late ?? '—'} really late`,
      body: () => 'In danger means an order depends on the flooded factory somewhere upstream. Late means its factory runs out of parts before the flood is over. DOMINO acts on the late ones and shows the fees at stake.',
      action: () => ({ label: 'Show me how it spread', run: () => go('chain') }),
      done: (c) => c.view === 'chain' },
    { view: 'chain', target: q('.view.on .card'),
      title: () => 'The supplier nobody was watching',
      body: (c) => `${c.m.site ? c.m.short(c.m.site.id) : 'The flooded factory'} is not on Kestrel's supplier list, yet ${plural(c.m.d.exposedTier1.length, 'of your suppliers', 'of your suppliers')} depend on it. That is why the dashboard saw nothing. Hover a company to follow its path.`,
      next: true },
    { view: 'overview', target: byText('button', /^Approve plan$/),
      title: () => 'Your call',
      body: (c) => {
        const rec = c.m.rec, plan = c.m.d.plan
        return `DOMINO tested five plans in copies of the graph. It recommends buying from ${plural(c.m.suppliersInPlan.length, 'other supplier')}${plan?.spend_cents != null ? ` for ${usd(plan.spend_cents)}` : ''}${rec ? `, which protects ${rec.protected_projected} of the ${T?.projected_late ?? '—'} late orders` : ''}. Nothing is bought until a person approves.`
      },
      waiting: () => 'Your turn: press Approve plan',
      done: (c) => c.m.executed },
    { view: 'shipments', target: q('.ff'),
      title: () => 'Orders placed. Now let time pass',
      body: () => 'The purchase orders exist, but no parts have arrived yet: those orders are protected on paper only. Fast-forward to delivery to see which suppliers arrive on time and which come in late.',
      waiting: (c) => (c.m.d.verify ? 'Your turn: press Fast-forward to delivery' : 'DOMINO is running its safety checks'),
      done: (c) => !!c.m.delivery },
    { view: 'agent', target: () => q('.learned')() ?? cardWith(/What DOMINO remembers/)(),
      title: () => 'DOMINO learned something',
      body: (c) => `${c.late.length ? `${c.late.slice(0, 2).join(' and ')} came in late.` : 'Every supplier arrived on time.'} DOMINO wrote how each supplier did to its memory graph, which survives a reset of the world. Run the same flood again and watch the plan change.`,
      action: () => ({ label: 'Run the same flood again', run: () => { startDemo(); advance() } }) },
    { view: 'agent', target: byText('summary', /memory/i),
      title: () => 'Same flood, a different plan',
      body: () => 'This time the balanced plan ranks suppliers with what DOMINO learned. The box below the plan says which ranking changed and why, with the purchase order behind it.',
      waiting: (c) => (c.m.phase === 'awaiting' ? null : 'DOMINO is planning again'),
      next: true },
    { view: 'xray', target: q('.view.on h1'),
      title: () => 'Find the next flood first',
      body: () => 'Risk X-ray stops every upstream site on its own, in copies of the graph, and ranks the damage. Hidden weak points are companies you have no contract with that would still hurt you. Click one, then "Rehearse this disruption".',
      next: true },
    { view: 'overview', target: q('.top-right'),
      title: () => 'Everything is open',
      body: () => 'You have seen the whole loop: trace, impact, a human decision, delivery and memory. The full version adds Live alerts with real disasters, Claude Code mode to drive DOMINO from your own terminal, and Reset the world for a clean start.',
      action: () => ({ label: 'Open the full version', run: () => st.setExperience('free') }) },
  ]
  const cur = guided ? steps[Math.min(step, LAST_STEP)] : null

  // A reload loses the run; go back to the first step instead of pointing at things that are gone.
  useEffect(() => {
    if (guided && step > 0 && step < 8 && st.ready && st.runStatus === 'idle' && !st.runId) st.setGuideStep(0)
  }, [guided, st.ready]) // eslint-disable-line react-hooks/exhaustive-deps

  // Move to the step's view when the step changes.
  useEffect(() => { if (cur && view !== cur.view) go(cur.view) }, [step, guided]) // eslint-disable-line react-hooks/exhaustive-deps

  // Advance by itself when the visitor (or DOMINO) has done the thing.
  function advance() {
    const next = Math.min(step + 1, LAST_STEP)
    const opened = (Object.keys(OPENS_AT) as ViewId[]).filter((v) => OPENS_AT[v] === next && next > st.guideMax)
    st.setGuideStep(next)
    if (opened.length) useToasts.getState().push(<span><b>Unlocked:</b> {opened.map((v) => VIEW_NAMES[v]).join(' and ')}</span>)
  }

  const isDone = cur?.done?.(ctx) ?? false
  useEffect(() => {
    if (!guided || !isDone) return
    const t = window.setTimeout(() => advance(), 700)
    return () => clearTimeout(t)
  }, [isDone, step, guided]) // eslint-disable-line react-hooks/exhaustive-deps

  // Ring around what the step is about; follows layout changes and scrolling.
  useLayoutEffect(() => {
    if (!cur?.target || minAt === step) return
    const find = () => {
      const r = cur.target?.()?.getBoundingClientRect()
      setRect(r && r.width > 0 ? r : null)
    }
    const first = window.setTimeout(() => { cur.target?.()?.scrollIntoView({ block: 'center', behavior: 'smooth' }); find() }, 350)
    const again = window.setInterval(find, 500)
    window.addEventListener('resize', find)
    window.addEventListener('scroll', find, true)
    return () => { clearTimeout(first); clearInterval(again); window.removeEventListener('resize', find); window.removeEventListener('scroll', find, true) }
  }, [cur, step, minAt, view])

  if (!cur) return null
  const min = minAt === step
  const failed = m.phase === 'failed'
  const wait = failed ? null : cur.waiting?.(ctx) ?? null
  const action = failed ? { label: 'Start the flood again', run: startDemo } : cur.action?.(ctx) ?? null
  const showRing = rect && !min && !(cur.done && isDone)
  const you = !!wait && wait.startsWith('Your turn')
  // keep the card off what it points at: when the target sits on the right, the card moves to the left
  const side = rect && rect.left + rect.width / 2 > window.innerWidth * 0.55 && window.innerWidth > 760 ? 'left' : ''

  if (min) {
    return (
      <button type="button" className="guide-mini" onClick={() => setMinAt(null)}>
        <span className="guide-num">{step + 1}</span><span>{cur.title(ctx)}</span>
      </button>
    )
  }
  return (
    <>
      {showRing && <div className="guide-ring" style={{ left: rect.left - 6, top: rect.top - 6, width: rect.width + 12, height: rect.height + 12 }} aria-hidden />}
      <aside className={`guide-card ${side}`} role="dialog" aria-live="polite" aria-label="Guide">
        <div className="guide-bar"><i style={{ width: `${((step + (isDone ? 1 : 0)) / LAST_STEP) * 100}%` }} /></div>
        <div className="guide-top">
          <span className="sub">Guided · step {step + 1} of {LAST_STEP + 1}</span>
          <button type="button" className="guide-x" aria-label="Make the guide smaller" title="Make smaller" onClick={() => setMinAt(step)}>–</button>
        </div>
        <h3>{failed ? 'The run stopped' : cur.title(ctx)}</h3>
        <p>{failed ? 'Something interrupted the run (another visitor may have reset the shared world). Start it again; nothing you opened closes.' : cur.body(ctx)}</p>
        {wait && <div className={`guide-wait ${you ? 'you' : ''}`}>{you ? <i className="guide-you" /> : <i className="spin" />}{you ? wait.replace(/^Your turn: p/, 'P') : wait}</div>}
        <div className="guide-nav">
          {step > 0 && <button type="button" className="btn btn-ghost" onClick={() => st.setGuideStep(step - 1)}>Back</button>}
          {action
            ? <button type="button" className="btn btn-accent" disabled={st.busy} onClick={action.run}>{action.label}</button>
            : cur.next
              ? <button type="button" className="btn btn-accent" disabled={!!wait} onClick={advance}>Next</button>
              : null}
        </div>
      </aside>
    </>
  )
}

/** First visit: choose the guided path or the full war room. */
export function Welcome() {
  const st = useStore()
  if (st.experience !== null) return null
  const pick = (e: 'guided' | 'free') => {
    if (e === 'guided') { st.setGuideStep(0); if (st.mode !== 'scripted') st.setMode('scripted') }
    st.setExperience(e)
  }
  return (
    <div className="welcome" role="dialog" aria-modal="true" aria-labelledby="welcome-h">
      <div className="welcome-in">
        <div className="logo welcome-logo" aria-hidden><span /><span /></div>
        <h1 id="welcome-h">DOMINO</h1>
        <p className="welcome-lede">A supply-chain agent on FalkorDB. When a disaster stops a factory you never buy from, DOMINO finds the orders it will really delay, tests a fix, and asks you before it buys anything.</p>
        <div className="welcome-cards">
          <button type="button" className="welcome-card primary" onClick={() => pick('guided')}>
            <span className="welcome-k">Recommended · about 3 minutes</span>
            <b>Guide me</b>
            <span>Live through one flood step by step. Each part of the war room opens when the story reaches it.</span>
            <span className="welcome-go">Start the guide →</span>
          </button>
          <button type="button" className="welcome-card" onClick={() => pick('free')}>
            <span className="welcome-k">Everything open</span>
            <b>Explore on my own</b>
            <span>All views, all four ways to run the agent, Risk X-ray and Live alerts, right away.</span>
            <span className="welcome-go">Open the war room →</span>
          </button>
        </div>
        <p className="sub welcome-foot">You can switch between the two at any time, top right.</p>
      </div>
    </div>
  )
}

/** Top-right switch between the guided path and the full war room. */
export function ExperienceSwitch() {
  const st = useStore()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const off = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', off)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', off); document.removeEventListener('keydown', esc) }
  }, [open])
  if (st.experience === null) return null
  const guided = st.experience === 'guided'
  const startGuide = () => {
    useStore.setState({ guideMax: 0 })
    st.setGuideStep(0)
    if (st.mode !== 'scripted') st.setMode('scripted')
    st.setExperience('guided')
    setOpen(false)
  }
  return (
    <div className="xp" ref={box}>
      <button type="button" className={`xp-btn ${guided ? 'on' : ''}`} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {guided ? <><span className="xp-dot" />Guided<span className="xp-n">{st.guideStep + 1}/{LAST_STEP + 1}</span></> : <>Full version</>}
        <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden><path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>
      </button>
      {open && (
        <div className="xp-menu" role="menu">
          <button type="button" role="menuitemradio" aria-checked={guided} className={guided ? 'on' : ''} onClick={() => (guided ? setOpen(false) : startGuide())}>
            <b>Guided</b><span>{guided ? `Step ${st.guideStep + 1} of ${LAST_STEP + 1}. Views open as you go.` : 'One flood, step by step. Starts from the beginning.'}</span>
          </button>
          <button type="button" role="menuitemradio" aria-checked={!guided} className={!guided ? 'on' : ''} onClick={() => { st.setExperience('free'); setOpen(false) }}>
            <b>Full version</b><span>Everything open: all views, modes, X-ray and Live alerts.</span>
          </button>
          {guided && <button type="button" role="menuitem" className="xp-restart" onClick={startGuide}>Start the guide over</button>}
        </div>
      )}
    </div>
  )
}
