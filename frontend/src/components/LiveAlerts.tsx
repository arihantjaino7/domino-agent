import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useStore } from '../lib/store'
import { useToasts } from '../lib/toasts'
import type { LiveAlert, LiveAlertsResponse } from '../lib/types'

const when = (value: string) => new Date(value).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const age = (value: string, now: number) => {
  const minutes = Math.max(0, Math.floor((now - new Date(value).getTime()) / 60000))
  if (minutes < 1) return 'just updated'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  return hours < 24 ? `${hours} hr ago` : `${Math.floor(hours / 24)} days ago`
}

export function LiveAlerts() {
  const [feed, setFeed] = useState<LiveAlertsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [now, setNow] = useState(Date.now)
  const [refreshKey, setRefreshKey] = useState(0)
  const [copyFallback, setCopyFallback] = useState<string | null>(null)
  const busy = useStore((s) => s.busy)
  const runStatus = useStore((s) => s.runStatus)
  const stopSites = useStore((s) => s.stopLiveSites)
  const working = busy || ['running', 'approving', 'awaiting_approval'].includes(runStatus)

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      try {
        const response = await api.liveAlerts()
        if (active) setFeed(response)
      } catch {
        if (active) setFeed({ events: [], source: 'gdacs', updated_at: null, error: 'Live alerts are temporarily unavailable. Try again shortly.' })
      } finally {
        if (active) { setLoading(false); setNow(Date.now()) }
      }
    }
    void load()
    const refresh = setInterval(() => void load(), 600000)
    const clock = setInterval(() => setNow(Date.now()), 60000)
    return () => { active = false; clearInterval(refresh); clearInterval(clock) }
  }, [refreshKey])

  const copy = async (event: LiveAlert) => {
    const command = `/mcp__domino__alert ${event.alert_text}`
    try {
      await navigator.clipboard.writeText(command)
      setCopyFallback(null)
      useToasts.getState().push('Alert copied. Paste it into Claude Code.')
    } catch {
      setCopyFallback(command)
    }
  }

  return (
    <section className="card live-alerts" aria-labelledby="live-alerts-heading" aria-busy={loading}>
      <div className="card-h">
        <div><h2 id="live-alerts-heading">Live alerts</h2><p className="sub">Real disasters, screened against your supply chain.</p></div>
        <button type="button" className="btn btn-ghost" disabled={loading} onClick={() => setRefreshKey((n) => n + 1)}>{loading ? 'Updating…' : 'Refresh alerts'}</button>
      </div>
      <div className="card-b">
        <p className="sub live-alerts-source">Source: <a href="https://www.gdacs.org/" target="_blank" rel="noreferrer" title="Global Disaster Alert and Coordination System">GDACS</a>, updated {feed?.updated_at ? <time dateTime={feed.updated_at}>{when(feed.updated_at)}</time> : 'not available'}</p>
        <p className="plain">Nearby places may need checking; proximity does not confirm damage. A manual stop changes this world. Starting a demo or watching Claude Code resets the world first.</p>
        {loading && !feed && <p className="plain" role="status">Loading current events from GDACS…</p>}
        {feed?.error && <p className="plain" role="status">{feed.error}</p>}
        {feed && !feed.error && feed.events.length === 0 && <p className="plain" role="status">GDACS returned no current events. Not being in the graph does not mean safe.</p>}
        {copyFallback && <label className="live-alert-copy sub">Clipboard unavailable. Select and copy this command:<textarea readOnly value={copyFallback} onFocus={(e) => e.target.select()} /></label>}
        {feed && feed.events.length > 0 && (
          <ul className="live-alert-list">
            {feed.events.map((event) => (
              <li key={event.id} className="live-alert">
                <div className="live-alert-meta">
                  <span className="sub">{event.type_label}</span>
                  <span className={`tag live-alert-level level-${event.alert_level.toLowerCase()}`}>{event.alert_level} alert</span>
                  {event.updated_at && <time className="sub" dateTime={event.updated_at} title={when(event.updated_at)}>{age(event.updated_at, now)}</time>}
                </div>
                <h3 title={event.title}>{event.title.length > 140 ? `${event.title.slice(0, 137).trimEnd()}…` : event.title}</h3>
                <p className="sub">{event.country}{event.starts_at && <> · Started {when(event.starts_at)}</>}</p>
                {event.in_graph ? (
                  <>
                    <p className="plain">{event.sites.length > 0 ? <>Touches {event.sites.length} {event.sites.length === 1 ? 'site' : 'sites'} in your supply chain: {event.sites.map((site) => `${site.name}${site.tier == null ? '' : ` (tier ${site.tier})`}`).join(', ')}.</> : <>Nearby graph places: {event.places.map((place) => `${place.name} (${place.kind.toLowerCase()})`).join(', ')}. No supplier sites within the screening radius.</>}</p>
                    <p className="sub">Within {event.radius_km} km of the event centre.</p>
                  </>
                ) : <p className="plain"><b>Not in the graph</b><br />Not being in the graph does not mean safe.</p>}
                <div className="live-alert-actions">
                  <button type="button" className="btn btn-ghost" onClick={() => void copy(event)}>Copy for Claude Code</button>
                  {event.in_graph && <button type="button" className="btn btn-ghost" disabled={working || event.site_ids.length === 0} onClick={() => void stopSites(event)}>Stop these sites here</button>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
