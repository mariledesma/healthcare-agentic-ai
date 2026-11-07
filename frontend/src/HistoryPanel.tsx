import { useEffect, useState } from 'react';
import type { CaseResult } from './App';

export type SavedReview = { recommendation_id: string; decision: 'approved' | 'rejected' | 'flagged'; review_status: string; notes: string | null; reviewer_role: string; created_at: string };
type Run = { run_id: string; case_id: string; model: string | null; status: string; final_status: string; created_at: string; has_full_artifact: boolean };
type History = { total: number; runs: Run[] };
const API = 'http://127.0.0.1:8000';

export function HistoryPanel({ onOpen }: { onOpen: (result: CaseResult, reviews: SavedReview[]) => void }) {
  const [history, setHistory] = useState<History | null>(null);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [opening, setOpening] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}/runs?limit=25&offset=${offset}`, { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('Saved runs are unavailable. Check database readiness and migration status.');
      return response.json() as Promise<History>;
    }).then(data => { if (!controller.signal.aborted) { setHistory(data); setError(''); } })
      .catch((e: Error) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [offset, revision]);
  async function open(runId: string) {
    setOpening(runId); setError('');
    try {
      const response = await fetch(`${API}/runs/${runId}`);
      if (!response.ok) throw new Error('The saved run could not be loaded or failed integrity verification.');
      const saved = await response.json() as { legacy: boolean; result: CaseResult | null; reviews: SavedReview[]; message?: string };
      if (saved.legacy || !saved.result) throw new Error(saved.message ?? 'This older run has no full artifact. Run the case again to create one.');
      onOpen(saved.result, saved.reviews);
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not load saved run'); }
    finally { setOpening(''); }
  }
  function page(next: number) { setLoading(true); setOffset(next); }
  return <section className="clinical-panel research-view">
    <h2>Saved run history</h2>
    <p>Each run preserves its source evidence, model outputs, proposal checks, and governance decisions. Review decisions are saved separately and never execute clinical actions.</p>
    <p>Older runs marked Legacy summary have no full artifact; rerun their case to capture complete evidence.</p>
    <button onClick={() => { setLoading(true); setRevision(v => v+1); }} disabled={loading}>Refresh history</button>
    {loading && <p role="status">Loading saved runs…</p>}
    {error && <p role="alert" className="research-error">{error}</p>}
    {history && <><p>{history.total} stored runs · showing {history.runs.length ? offset+1 : 0}–{offset+history.runs.length}</p>
      <div className="research-table-wrap"><table><thead><tr><th>Case</th><th>Created</th><th>Model</th><th>Outcome</th><th>Evidence</th></tr></thead>
      <tbody>{history.runs.map(run => <tr key={run.run_id}><td>{run.case_id}<br/><code>{run.run_id.slice(0,8)}</code></td>
        <td>{new Date(run.created_at).toLocaleString()}</td><td>{run.model === 'none' ? 'Offline reference' : run.model ?? 'Unknown'}</td><td>{run.final_status?.replaceAll('_',' ')}</td>
        <td><button disabled={!!opening || !run.has_full_artifact} onClick={() => open(run.run_id)}>{opening === run.run_id ? 'Loading…' : run.has_full_artifact ? 'Open saved run' : 'Legacy summary'}</button></td></tr>)}</tbody></table></div>
      <div><button disabled={loading || offset===0} onClick={() => page(Math.max(0,offset-25))}>Previous</button>{' '}
        <button disabled={loading || offset+25>=history.total} onClick={() => page(offset+25)}>Next</button></div>
    </>}
  </section>;
}
