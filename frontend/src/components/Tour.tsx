import { useEffect, useLayoutEffect, useState } from 'react'
import { useStore } from '../lib/store'
import type { ViewId } from '../App'

type Step = {
  view: ViewId
  title: string
  text: string
  /** CSS selector of what to point at; a function can look for a button by its text */
  target?: string | (() => Element | null)
  action?: { label: string; run: () => void }
}

const button = (re: RegExp) => () => [...document.querySelectorAll('button')].find((b) => re.test(b.textContent ?? '') && b.getBoundingClientRect().width > 0) ?? null

const SEEN = 'domino-tour-seen'
const tourSeen = () => { try { return localStorage.getItem(SEEN) === '1' } catch { return true } }
const markSeen = () => { try { localStorage.setItem(SEEN, '1') } catch { /* storage unavailable */ } }

/** A guided tour for first-time visitors. It points at things and switches views; it never changes the shared world. */
export function Tour({ go }: { go: (v: ViewId) => void }) {
  const step = useStore((s) => s.tour)
  const setTour = useStore((s) => s.setTour)
  const setMode = useStore((s) => s.setMode)
  const run = useStore((s) => s.run)
  const replays = useStore((s) => s.replays)
  const [rect, setRect] = useState<DOMRect | null>(null)

  const steps: Step[] = [
    { view: 'overview', target: '.ov-hero', title: 'What DOMINO does',
      text: 'A flood can stop a supplier you never buy from directly, and a normal dashboard shows nothing wrong. DOMINO follows the supply chain through every tier, finds the orders that will really be late, tests recovery plans, and asks a person before it buys anything. This tour takes about a minute and changes nothing in the shared world.' },
    { view: 'overview', target: '.seg', title: 'Four ways to run it',
      text: 'Demo is a scripted agent using the real tools. Replay plays back a real Claude Code run. Claude Code lets your own Claude Code drive DOMINO. Claude API runs Claude in the backend when a key is set. Replay is the quickest way to see a real run.' },
    { view: 'overview', title: 'Watch a real run',
      text: 'Press the button to play a recording of Claude Code handling a monsoon flood. It changes nothing in the graph. Then press Next while it plays.',
      action: { label: 'Play the recording', run: () => { setMode('replay'); void run() } } },
    { view: 'overview', target: '.ov-nums', title: 'Exposed is not late',
      text: 'Orders in danger depend on the stopped site somewhere upstream. Only some of them will really run out of parts. DOMINO separates the two, and shows the penalty fees at stake.' },
    { view: 'overview', target: '.map-card', title: 'Tier-1 view versus DOMINO',
      text: 'Switch between "Tier-1 view" and "DOMINO" above the map. A tier-1 view only checks suppliers you buy from directly, so it sees nothing. DOMINO follows the graph and lights up the hidden dependency.' },
    { view: 'overview', target: button(/Approve plan/), title: 'A human decides',
      text: 'When the plan is ready the run pauses here. Press Approve plan to continue. No purchase order exists until a person approves, and the approval is bound to this exact plan and the state of the world.' },
    { view: 'chain', title: 'Supply chain', text: 'Only the companies on the disruption path are shown, from the stopped maker on the left to your customers on the right. Green marks the new suppliers in the plan.' },
    { view: 'factories', title: 'Factories', text: 'Every tile is one customer order, coloured by what will happen to it: late, in danger, protected, or fine.' },
    { view: 'shipments', title: 'Shipments', text: 'The plan buys from new suppliers. After a plan is executed, Fast-forward to delivery shows which suppliers arrive late. DOMINO remembers that, and the next plan says why it ranks suppliers differently.' },
    { view: 'xray', title: 'Risk X-ray', text: 'Before any disaster, DOMINO stops every upstream site on its own, in copies of the graph, and ranks the damage. Hidden weak points are sites you have no contract with that still hurt you. Click one and press Rehearse this disruption to watch DOMINO respond.' },
    { view: 'agent', title: 'AI agent', text: 'Every tool call, the five plans it compared, the nine safety checks, the exact database queries behind each result ("Show a database query"), and what DOMINO has learned from earlier runs.' },
    { view: 'overview', target: '.seg', title: 'Your turn',
      text: 'Run the Monsoon demo yourself, open Risk X-ray, or connect your own Claude Code (Claude Code mode shows the one command). Press Reset the world whenever you want a clean start.',
      action: { label: 'Run the demo myself', run: () => { setMode('scripted'); void run() } } },
  ]

  const cur = step !== null ? steps[step] : null
  const last = steps.length - 1

  useEffect(() => { if (step !== null) go(steps[step].view) }, [step]) // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    if (!cur) return
    const find = () => {
      const t = typeof cur.target === 'function' ? cur.target() : cur.target ? document.querySelector(cur.target) : null
      if (!t) { setRect(null); return }
      const r = t.getBoundingClientRect()
      if (r.width === 0) { setRect(null); return }
      setRect(r)
    }
    const timer = window.setTimeout(() => {
      const t = typeof cur.target === 'function' ? cur.target() : cur.target ? document.querySelector(cur.target) : null
      t?.scrollIntoView({ block: 'center', behavior: 'smooth' })
      find()
    }, 250)
    const again = window.setInterval(find, 400)
    window.addEventListener('resize', find)
    window.addEventListener('scroll', find, true)
    return () => { clearTimeout(timer); clearInterval(again); window.removeEventListener('resize', find); window.removeEventListener('scroll', find, true) }
  }, [cur, step])

  if (step === null || !cur) return null
  const close = () => { markSeen(); setTour(null) }
  const canPlay = !cur.action || cur.action.label !== 'Play the recording' || replays.length > 0

  return (
    <>
      {rect && <div className="tour-ring" style={{ left: rect.left - 6, top: rect.top - 6, width: rect.width + 12, height: rect.height + 12 }} aria-hidden />}
      <aside className="tour-card" role="dialog" aria-label="Guided tour">
        <div className="tour-top">
          <span className="sub">Step {step + 1} of {steps.length}</span>
          <button type="button" className="tour-x" aria-label="Close the tour" onClick={close}>×</button>
        </div>
        <h3>{cur.title}</h3>
        <p>{cur.text}</p>
        {cur.action && canPlay && <button type="button" className="btn btn-accent tour-act" onClick={() => cur.action!.run()}>{cur.action.label}</button>}
        <div className="tour-nav">
          <button type="button" className="btn btn-ghost" onClick={() => setTour(Math.max(0, step - 1))} disabled={step === 0}>Back</button>
          <div className="tour-dots" aria-hidden>{steps.map((_, i) => <i key={i} className={i === step ? 'on' : ''} />)}</div>
          {step < last
            ? <button type="button" className="btn btn-accent" onClick={() => setTour(step + 1)}>Next</button>
            : <button type="button" className="btn btn-accent" onClick={close}>Finish</button>}
        </div>
      </aside>
    </>
  )
}

/** First visit only: a small invitation, never an automatic takeover of the page. */
export function TourInvite() {
  const step = useStore((s) => s.tour)
  const setTour = useStore((s) => s.setTour)
  const [show, setShow] = useState(false)
  useEffect(() => { const t = window.setTimeout(() => setShow(!tourSeen()), 2500); return () => clearTimeout(t) }, [])
  if (!show || step !== null) return null
  const dismiss = () => { markSeen(); setShow(false) }
  return (
    <div className="tour-invite" role="note">
      <span>First time here? Take a one-minute tour.</span>
      <button type="button" className="btn btn-accent" onClick={() => { setShow(false); setTour(0) }}>Start the tour</button>
      <button type="button" className="tour-x" aria-label="No thanks" onClick={dismiss}>×</button>
    </div>
  )
}
