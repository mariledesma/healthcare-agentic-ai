import { useEffect, useState } from 'react';

const API = 'http://127.0.0.1:8000';
type Scores = { mean_barrier_jaccard: number; mean_task_jaccard: number };
type Aggregate = { mode: string; training_shield: string; evaluation_shield: boolean;
  success: { mean: number }; unsafe_proposed: number; unsafe_after_shield: number };
type Summary = {
  status: string; bundle?: string; message?: string; limitations?: string[];
  safety?: { attack_rows: number; attack_flag_rate: number; clean_verification_rejection_rate: number; scope: string };
  representation?: { scope: string; split_counts: Record<string, number>;
    training: { method: string; dimensions: number; epochs: number };
    metrics: Record<string, Record<string, Scores>> };
  rl?: { scope: string; seeds: number[]; aggregates: Aggregate[] };
};
type Simulation = { status: string; scenario?: string; scope?: string; trace?: {
  state: string; proposed_action: string; applied_action: string; reward: number; shield_intervened: boolean;
}[] };
type Neighbors = { status: string; scope?: string; neighbors?: { case_id: string; similarity: number }[] };

export type WorkflowResearch = {
  agent_workflow?: { status: string; controller: string; decision: string; steps_used: number; max_steps: number;
    trace: { step: number; tool: string; event_sha256: string }[];
    source_quality?: { issues: { issue_id: string; message: string; source_value: unknown }[] };
    injection_signals?: { source_path: string; kind: string }[] };
  safety_verification?: { status: string; rejected: { reasons: string[]; proposal: unknown }[]; missing_task_ids: string[] };
  provenance?: { input_sha256: string; manifest_sha256: string; scope: string };
};

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(API + url, options);
  if (!response.ok) throw new Error(`Research request failed (${response.status}). Check the API and frozen experiment bundle.`);
  return response.json() as Promise<T>;
}

const percent = (x: number) => `${(100*x).toFixed(1)}%`;
export function ResearchPanel({ result, caseFile }: { result: WorkflowResearch | null; caseFile: string }) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState('');
  const [scenario, setScenario] = useState('clinical');
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [neighbors, setNeighbors] = useState<Neighbors | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    request<Summary>('/research', { signal: controller.signal }).then(setSummary).catch((e: Error) => {
      if (e.name !== 'AbortError') setError(e.message);
    });
    return () => controller.abort();
  }, []);
  async function simulate() {
    setBusy(true); setError(''); setSimulation(null);
    try { setSimulation(await request<Simulation>('/research/simulate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario, shield: true }),
    })); } catch (e) { setError(e instanceof Error ? e.message : 'Simulation failed'); }
    finally { setBusy(false); }
  }
  async function retrieve() {
    setBusy(true); setError('');
    try { setNeighbors(await request<Neighbors>(`/research/cases/${encodeURIComponent(caseFile)}/neighbors`)); }
    catch (e) { setError(e instanceof Error ? e.message : 'Retrieval failed'); }
    finally { setBusy(false); }
  }
  const workflow = result?.agent_workflow;
  const verifier = result?.safety_verification;
  return <div className="research-view">
    <section className="clinical-panel">
      <h2>Agent research</h2>
      <p>Inspect evidence, verify proposals, and route review. Learned representations and reinforcement learning are research experiments with no clinical execution authority.</p>
      {error && <p role="alert" className="research-error">{error}</p>}
      {!summary && !error && <p role="status">Loading frozen experiments…</p>}
      {summary?.status === 'not_trained' && <p>{summary.message}</p>}
      {summary?.bundle && <p className="panel-subtitle">Frozen experiment: {summary.bundle}</p>}
      {workflow ? <>
        <h3>Current case: agent tool trace</h3>
        <p>{workflow.controller} · {workflow.steps_used}/{workflow.max_steps} steps · {workflow.decision.replaceAll('_', ' ')}</p>
        <ol>{workflow.trace.map(event => <li key={event.step}><strong>{event.tool.replaceAll('_', ' ')}</strong><br/><code>{event.event_sha256.slice(0, 20)}…</code></li>)}</ol>
        {(workflow.source_quality?.issues.length ?? 0) > 0 && <details><summary>Source issues requiring clarification</summary>
          <ul>{workflow.source_quality?.issues.map(issue => <li key={issue.issue_id}>{issue.message} <code>{JSON.stringify(issue.source_value)}</code></li>)}</ul>
        </details>}
        {(workflow.injection_signals?.length ?? 0) > 0 && <p>Instruction-like source text flagged for review. Pattern checks do not establish prompt-injection resistance.</p>}
      </> : <p>Run a case to inspect its agent steps and evidence checks.</p>}
      {verifier && <><h3>Proposal verification: {verifier.status.replaceAll('_', ' ')}</h3>
        <p>{verifier.rejected.length} rejected proposals · {verifier.missing_task_ids.length} missing tasks</p>
        {verifier.rejected.length > 0 && <details><summary>Rejected proposals and reasons</summary><pre>{JSON.stringify(verifier.rejected, null, 2)}</pre></details>}
      </>}
      {result?.provenance && <details><summary>Content integrity record</summary><p>{result.provenance.scope}</p>
        <p>Input digest</p><code className="research-digest">{result.provenance.input_sha256}</code>
        <p>Manifest digest</p><code className="research-digest">{result.provenance.manifest_sha256}</code></details>}
    </section>
    {summary?.safety && <section className="clinical-panel"><h2>Generative AI safety and provenance</h2>
      <div className="research-metrics"><div><strong>{summary.safety.attack_rows}</strong><span>mutated proposal cases</span></div>
        <div><strong>{percent(summary.safety.attack_flag_rate)}</strong><span>mutation flag rate</span></div>
        <div><strong>{percent(summary.safety.clean_verification_rejection_rate)}</strong><span>clean proposal rejection</span></div></div>
      <p>{summary.safety.scope}</p><p>Content hashes reveal changes relative to a manifest. They do not authenticate a clinical source or prove that generated text is true.</p>
    </section>}
    {summary?.representation && <section className="clinical-panel"><h2>Learned case representations</h2>
      <p>{summary.representation.training.dimensions}-dimensional contrastive encoder, trained for {summary.representation.training.epochs} epochs without answer labels.</p>
      <p>Cases: {Object.entries(summary.representation.split_counts).map(([name, count]) => `${name}: ${count}`).join(' · ')}</p>
      <div className="research-table-wrap"><table><caption>Test retrieval: agreement with the nearest training case</caption><thead><tr><th>Method</th><th>Barrier Jaccard</th><th>Task Jaccard</th></tr></thead>
      <tbody>{Object.entries(summary.representation.metrics.test ?? {}).map(([method, score]) => <tr key={method}><td>{method.replaceAll('_', ' ')}</td><td>{score.mean_barrier_jaccard.toFixed(3)}</td><td>{score.mean_task_jaccard.toFixed(3)}</td></tr>)}</tbody></table></div>
      <p>{summary.representation.scope}</p><button disabled={busy} onClick={retrieve}>Find similar synthetic cases</button>
      {neighbors && <><p>{neighbors.scope ?? neighbors.status}</p><ul>{neighbors.neighbors?.map(n => <li key={n.case_id}>{n.case_id}: {n.similarity.toFixed(3)} cosine similarity</li>)}</ul></>}
    </section>}
    {summary?.rl && <section className="clinical-panel"><h2>Reasoning and reinforcement learning</h2>
      <p>Tabular Q-learning learns inspect → verify → route sequences in a synthetic workflow simulator. Results span {summary.rl.seeds.length} training seeds.</p>
      <div className="research-table-wrap"><table><caption>Routing experiment and safety shield ablations</caption><thead><tr><th>Policy</th><th>Training shield</th><th>Evaluation shield</th><th>Success</th><th>Unsafe proposed</th><th>Unsafe applied</th></tr></thead>
        <tbody>{summary.rl.aggregates.map((row, i) => <tr key={i}><td>{row.mode}</td><td>{row.training_shield}</td><td>{row.evaluation_shield ? 'On' : 'Off'}</td><td>{percent(row.success.mean)}</td><td>{row.unsafe_proposed}</td><td>{row.unsafe_after_shield}</td></tr>)}</tbody></table></div>
      <p>{summary.rl.scope}</p>
      <label>Simulated scenario <select value={scenario} onChange={e => setScenario(e.target.value)}>
        <option value="coordination">Coordination proposal</option><option value="clinical">Clinical review</option><option value="uncertain">Uncertain evidence</option><option value="forbidden">Forbidden operation</option>
      </select></label> <button disabled={busy} onClick={simulate}>{busy ? 'Working…' : 'Run simulation'}</button>
      {simulation && <><p>{simulation.scope ?? simulation.status}</p><ol>{simulation.trace?.map((step, i) => <li key={i}>{step.state} → <strong>{step.applied_action}</strong> · reward {step.reward.toFixed(1)}{step.shield_intervened ? ' · shield intervened' : ''}</li>)}</ol></>}
    </section>}
    {summary?.limitations && <section className="clinical-panel"><h2>Experimental scope</h2><ul>{summary.limitations.map(item => <li key={item}>{item}</li>)}</ul></section>}
  </div>;
}
