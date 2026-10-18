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
  /** index into CHAPTERS */
  chapter: number
  title: (c: Ctx) => string
  /** what the visitor is looking at, in plain words with the real numbers */
  see: (c: Ctx) => string
  /** one line on why it matters */
  why?: (c: Ctx) => string
  /** exactly one thing to do next */
  move: (c: Ctx) => string
  /** a short label pinned to the highlighted part of the page */
  pin?: string
  target?: () => Element | null
  /** dim the rest of the page so the highlighted part stands out */
  dim?: boolean
  /** show DOMINO's seven steps as a live checklist */
  checklist?: boolean
  /** the guide moves on by itself once this is true */
  done?: (c: Ctx) => boolean
  /** shown instead of the move while DOMINO is still busy */
  waiting?: (c: Ctx) => string | null
  action?: (c: Ctx) => { label: string; run: () => void } | null
  next?: boolean
}

const CHAPTERS = ['The flood', 'The impact', 'The hidden cause', 'Your decision', 'Memory', 'Prevention']
const PLAIN: Record<string, string> = {
  detect: 'Read the flood alert', trace: 'Follow the supply chain from the flood', impact: 'Find the orders that will really be late',
  options: 'Look for other suppliers', simulate: 'Test 5 rescue plans on copies of the data', approve: 'Ask you to approve', verify: 'Check the result',
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
  // phones show the short card; "What am I looking at?" opens the explanation for this step
  const [moreAt, setMoreAt] = useState<number | null>(null)
  const guided = st.experience === 'guided'
  const step = st.guideStep

  const T = m.totals
  const late: string[] = (m.delivery?.pos ?? []).filter((p: any) => p.days_late > 0).map((p: any) => p.site_name ?? p.site)
  const ctx: Ctx = { m, view, runId: st.runId, late }
  const startDemo = () => { st.setMode('scripted'); st.setScenario('monsoon'); void st.run() }
  const factories = (m.plants ?? []).map((p: any) => m.short(p.plant)).filter(Boolean)

  const steps: Step[] = [
    { view: 'overview', chapter: 0, target: q('.ov-hero'), pin: 'All zeros: nothing is wrong yet', dim: true,
      title: () => (st.guideMax > 0 ? 'Pick up where you left off' : 'Meet Kestrel Devices'),
      see: (c) => `${st.guideMax > 0 ? 'The page reloaded, so the earlier run is gone; everything you opened stays open. ' : ''}Kestrel Devices is a (made-up) laptop maker with ${factories.length ? `${factories.length} factories` : 'three factories'} and ${c.m.totals?.orders ?? 117} customer orders. The highlighted numbers are all zero: every order is on time.`,
      why: () => 'Kestrel\'s normal dashboard only watches the suppliers it pays directly. Let\'s see what that misses.',
      move: () => 'Press "Start the flood". A monsoon will shut down factories in central Thailand.',
      action: () => ({ label: 'Start the flood', run: () => { startDemo(); advance() } }) },
    { view: 'overview', chapter: 0, target: q('.map-card'), pin: 'Watch the map fill in', checklist: true,
      title: () => 'DOMINO is investigating on its own',
      see: () => 'DOMINO\'s AI agent received the flood alert and is now working through 7 steps by itself, using the supply-chain database. The checklist below ticks off each step; the map lights up as it finds problems.',
      why: () => 'It never guesses: every number it shows comes from a database query you can inspect later.',
      move: () => 'Nothing to do. Wait about 30 seconds.',
      waiting: () => 'DOMINO is working (about 30 seconds)',
      done: (c) => c.m.phase === 'awaiting' },
    { view: 'overview', chapter: 1, target: q('.ov-nums'), pin: 'These three numbers', dim: true,
      title: () => `${T?.exposed ?? '—'} orders are in danger, but only ${T?.projected_late ?? '—'} will really be late`,
      see: () => `"In danger" (${T?.exposed ?? '—'}) = orders that need parts coming from the flooded area. "Will be late" (${T?.projected_late ?? '—'}) = the ones whose factory runs out of parts before the flood is over. Stock covers the rest.`,
      why: () => `So DOMINO focuses on the ${T?.projected_late ?? '—'} that really need help: ${usd(T?.penalty_exposure_cents)} in late fees if nobody acts.`,
      move: () => 'Press "Show me why" to see where the problem really comes from.',
      action: () => ({ label: 'Show me why', run: () => go('chain') }),
      done: (c) => c.view === 'chain' },
    { view: 'chain', chapter: 2, target: q('.view.on .card'), pin: 'Read it left to right',
      title: () => 'The flooded factory is not even Kestrel\'s supplier',
      see: (c) => `In the first column, "Upstream makers", is ${c.m.site ? c.m.short(c.m.site.id) : 'the flooded factory'}, marked stopped. Kestrel never buys from it. But it sells parts to ${plural(c.m.d.exposedTier1.length, 'company', 'companies')} in the next column, "Direct suppliers", and they supply "Our factories". The lines show the path.`,
      why: () => 'Kestrel\'s dashboard only sees the "Direct suppliers" column, so it said "no problem". DOMINO found the hidden link by following the graph.',
      move: () => 'Point at (or tap) a box to light up its path, then press Next.',
      next: true },
    { view: 'overview', chapter: 3, target: byText('button', /^Approve plan$/), pin: 'Press this', dim: true,
      title: () => 'DOMINO found a fix. You decide',
      see: (c) => {
        const rec = c.m.rec, plan = c.m.d.plan
        return `It tested 5 rescue plans on copies of the database. Its pick: buy from ${plural(c.m.suppliersInPlan.length, 'other supplier')}${plan?.spend_cents != null ? ` for ${usd(plan.spend_cents)}` : ''}${rec ? `. That saves ${rec.protected_projected} of the ${T?.projected_late ?? '—'} late orders` : ''}.`
      },
      why: () => 'The AI cannot buy anything by itself. Only your click places the orders.',
      move: () => 'Press "Approve plan" (highlighted).',
      done: (c) => c.m.executed },
    { view: 'shipments', chapter: 3, target: q('.ff'), pin: 'Press the button here', dim: true,
      title: () => 'Orders placed. Now jump ahead in time',
      see: () => 'The purchase orders now exist, but no parts have arrived yet. Fast-forward simulates the next weeks: each new supplier delivers on time or late.',
      why: () => 'Real suppliers are not perfect, and DOMINO will remember who was late.',
      move: () => 'Press "Fast-forward to delivery" (highlighted).',
      waiting: (c) => (c.m.d.verify ? null : 'DOMINO is double-checking the orders it placed (a few seconds)'),
      done: (c) => !!c.m.delivery },
    { view: 'agent', chapter: 4, target: () => q('.learned')() ?? cardWith(/What DOMINO remembers/)(), pin: 'Trust score: before → after', dim: true,
      title: () => 'DOMINO remembered who was late',
      see: (c) => `${c.late.length ? `${c.late.slice(0, 2).join(' and ')} delivered late.` : 'Every supplier delivered on time.'} The highlighted list shows each supplier's trust score before → after (lower means trusted less).`,
      why: () => 'This memory survives even when the world is reset, so the next plan can use it.',
      move: () => 'Press "Run the same flood again" and see if DOMINO chooses differently.',
      action: () => ({ label: 'Run the same flood again', run: () => { startDemo(); advance() } }) },
    { view: 'agent', chapter: 4, target: byText('summary', /memory/i), pin: 'Why the plan changed', dim: true,
      title: () => 'Same flood, smarter plan',
      see: () => 'DOMINO planned again for the same flood. The highlighted box, "Memory changed this plan", names the supplier it now trusts less and what it buys instead.',
      why: () => 'That is the difference between an AI that answers and one that learns.',
      move: () => 'Read the highlighted box, then press Next.',
      waiting: (c) => (c.m.phase === 'awaiting' ? null : 'DOMINO is planning again (about 30 seconds)'),
      next: true },
    { view: 'xray', chapter: 5, target: q('.view.on h1'),
      title: () => 'Find weak spots before the next disaster',
      see: () => 'Risk X-ray pretends each supplier site breaks, one at a time, and counts how many orders would be late. "Hidden" means Kestrel has no contract with that site, so a normal dashboard cannot see it.',
      why: () => 'Now risks can be fixed before a flood, not after.',
      move: () => 'Read the highlighted headline: the site that would hurt Kestrel most, though Kestrel never buys from it. Then press Next.',
      next: true },
    { view: 'overview', chapter: 5, target: q('.xp'), pin: 'Switch here any time',
      title: () => 'You have seen the whole story',
      see: (c) => `Flood → hidden cause → your decision → delivery → memory → prevention. All of it ran on real tools and a real graph database.${c.m.phase === 'awaiting' ? ' The second plan (from the re-run) is still waiting on the right; approving it is up to you.' : ''}`,
      move: () => 'Press "Open the full version" to explore freely, including real disaster alerts and connecting your own Claude Code.',
      action: () => ({ label: 'Open the full version', run: () => st.setExperience('free') }) },
  ]
  const cur = guided ? steps[Math.min(step, LAST_STEP)] : null

  // A reload loses the run; go back to the first step instead of pointing at things that are gone.
  useEffect(() => {
    if (guided && step > 0 && step < 8 && st.ready && st.runStatus === 'idle' && !st.runId) st.setGuideStep(0)
  }, [guided, st.ready]) // eslint-disable-line react-hooks/exhaustive-deps

  // Move to the step's view when the step changes.
  useEffect(() => { if (cur && view !== cur.view) go(cur.view) }, [step, guided]) // eslint-disable-line react-hooks/exhaustive-deps

  function advance() {
    const next = Math.min(step + 1, LAST_STEP)
    const opened = (Object.keys(OPENS_AT) as ViewId[]).filter((v) => OPENS_AT[v] === next && next > st.guideMax)
    st.setGuideStep(next)
    if (opened.length) useToasts.getState().push(<span><b>Unlocked:</b> {opened.map((v) => VIEW_NAMES[v]).join(' and ')}</span>)
  }

  // Advance by itself when the visitor (or DOMINO) has done the thing, after a short "done" moment.
  const isDone = cur?.done?.(ctx) ?? false
  useEffect(() => {
    if (!guided || !isDone) return
    const t = window.setTimeout(() => advance(), 1300)
    return () => clearTimeout(t)
  }, [isDone, step, guided]) // eslint-disable-line react-hooks/exhaustive-deps

  // Ring around what the step is about; follows layout changes and scrolling.
  useLayoutEffect(() => {
    if (!cur?.target || minAt === step) return
    const find = () => {
      const r = cur.target?.()?.getBoundingClientRect()
      setRect(r && r.width > 0 ? r : null)
    }
    const first = window.setTimeout(() => {
      const el = cur.target?.() as HTMLElement | null | undefined
      // on a phone the card covers the lower half, so bring the target to the top, under the bar
      const phone = window.innerWidth <= 760
      if (el && phone) el.style.scrollMarginTop = '96px'
      el?.scrollIntoView({ block: phone ? 'start' : 'center', behavior: 'smooth' })
      find()
    }, 350)
    const again = window.setInterval(find, 400)
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
  // keep the card off what it points at: when the target sits on the right, the card moves to the left
  const side = rect && rect.left + rect.width / 2 > window.innerWidth * 0.55 && window.innerWidth > 760 ? 'left' : ''

  // DOMINO's seven steps, ticked off as the run reports them
  const curId = currentStep(st)
  const curIdx = m.phase === 'awaiting' || m.phase === 'approving' || m.phase === 'done' ? STEPS.findIndex((s) => s.id === 'approve') : STEPS.findIndex((s) => s.id === curId)

  if (min) {
    return (
      <button type="button" className="guide-mini" onClick={() => setMinAt(null)}>
        <span className="guide-num">{step + 1}</span><span>{cur.title(ctx)}</span>
      </button>
    )
  }
  return (
    <>
      {showRing && (
        <div className={`guide-ring ${cur.dim ? 'dim' : ''}`} style={{ left: rect.left - 6, top: rect.top - 6, width: rect.width + 12, height: rect.height + 12 }} aria-hidden>
          {cur.pin && <span className={`guide-pin ${rect.top < 90 ? (rect.height > 240 ? 'inside' : 'below') : ''}`}>{cur.pin}</span>}
        </div>
      )}
      <aside className={`guide-card ${side} ${moreAt === step || failed ? 'more' : ''}`} role="dialog" aria-live="polite" aria-label="Guide">
        <div className="guide-bar"><i style={{ width: `${((step + (isDone ? 1 : 0)) / LAST_STEP) * 100}%` }} /></div>
        <div className="guide-top">
          <span className="guide-chap">Chapter {cur.chapter + 1} of {CHAPTERS.length} · {CHAPTERS[cur.chapter]}</span>
          <span className="guide-step">{step + 1}/{LAST_STEP + 1}</span>
          <button type="button" className="guide-x" aria-label="Make the guide smaller" title="Make smaller" onClick={() => setMinAt(step)}>–</button>
        </div>
        <h3>{failed ? 'The run stopped' : cur.title(ctx)}</h3>
        <div className="guide-sec"><span className="guide-k">What you are seeing</span>
          <p>{failed ? 'Something interrupted the run (another visitor may have reset the shared world). Nothing you opened closes.' : cur.see(ctx)}</p></div>
        {cur.why && !failed && <div className="guide-sec"><span className="guide-k">Why it matters</span><p>{cur.why(ctx)}</p></div>}
        <button type="button" className="guide-more" aria-expanded={moreAt === step} onClick={() => setMoreAt(moreAt === step ? null : step)}>
          {moreAt === step ? 'Show less' : 'What am I looking at?'}
        </button>
        {cur.checklist && !failed && (
          <ol className="guide-check" aria-label="What DOMINO is doing">
            {STEPS.map((s, i) => {
              const state = isDone || i < curIdx ? 'done' : i === curIdx ? 'now' : 'todo'
              return <li key={s.id} className={state}><i />{PLAIN[s.id] ?? s.title}</li>
            })}
          </ol>
        )}
        <div className={`guide-move ${isDone ? 'ok' : wait ? 'busy' : 'you'}`}>
          {isDone
            ? <><i className="guide-tick" />Done. Moving on…</>
            : wait
              ? <><i className="spin" />{wait}</>
              : <><span className="guide-k">Your move</span><span>{failed ? 'Press "Start the flood again".' : cur.move(ctx)}</span></>}
        </div>
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
