"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowDownToLine, ArrowRight, BookOpen, Check, CheckCheck, ChevronRight, CircleDot, Clock3, Code2, FileCode2, FileSearch, FolderGit2, GitBranch, History, Leaf, LoaderCircle, LockKeyhole, Play, ScanLine, Settings2, ShieldCheck, Sparkles, Sprout, Terminal, X } from "lucide-react";
import { Button } from "@/components/ui/button";

type Repo = {id: string; name: string; path: string; synthetic: boolean; execution: string};
type Issue = {id: string; title: string; severity: string; withheld: boolean; reason: string | null; evidence: {tool: string; code: string; path: string; line: number; excerpt: string; message: string}};
type Scan = {id: string; repository: Repo; files: number; bytes: number; issues: Issue[]; duration_ms: number};
type Proposal = {id: string; summary: string; model: string; model_digest: string; inference_ms: number; before: Record<string,string>; after: Record<string,string>; risk: string; reasons: {rule: string; explanation: string}[]; lines_changed: number; diff: string};
type CheckResult = {name: string; status: string; output: string; duration_ms: number};
type Run = {id: string; copy_path: string; baseline: CheckResult[]; checks: CheckResult[]; before_issues: number; after_issues: number; resolved: number; regressions: number; verdict: string; source_unchanged: boolean};
type Health = {model: {available: boolean; model: string; digest: string; message: string; ollama_version?: string}};
type Event = {id: number; at: string; event: string; detail: Record<string,unknown>};

async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/${path}`, {method: body ? "POST" : "GET", headers: body ? {"Content-Type": "application/json"} : {}, body: body ? JSON.stringify(body) : undefined});
  if (!response.ok) { const message = await response.text(); throw new Error(message.replace(/^"|"$/g, "")); }
  return response.json();
}

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [repoId, setRepoId] = useState("demo");
  const [scan, setScan] = useState<Scan | null>(null);
  const [selected, setSelected] = useState<Issue | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [view, setView] = useState("garden");
  const [filter, setFilter] = useState("all");
  const [events, setEvents] = useState<Event[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [consent, setConsent] = useState(false);
  const refresh = useCallback(async () => {
    try { const [h,r] = await Promise.all([api<Health>("health"), api<Repo[]>("repositories")]); setHealth(h); setRepos(r); }
    catch (e) { setHealth(null); setError((e as Error).message); }
  }, []);
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 20000); return () => clearInterval(timer); }, [refresh]);
  const loadAudit = async () => { try { setEvents(await api<Event[]>("audit")); } catch(e) {setError((e as Error).message);} };
  const doScan = async () => {
    setBusy("Scanning allowlisted files with Ruff and Markdown checks…"); setError(""); setProposal(null); setRun(null); setSelected(null); setConsent(false);
    try {setScan(await api<Scan>("scans", {repository_id: repoId})); setView("garden");} catch(e) {setError((e as Error).message);} finally {setBusy("");}
  };
  const propose = async () => {
    if (!scan || !selected) return;
    setBusy("Qwen is reading the evidence and proposing a minimal edit locally…"); setError(""); setRun(null); setProposal(null); setConsent(false);
    try {setProposal(await api<Proposal>("proposals", {scan_id: scan.id, issue_id: selected.id}));} catch(e) {setError((e as Error).message);} finally {setBusy("");}
  };
  const approve = async () => {
    if (!proposal || !consent) return;
    setBusy("Creating isolated copies, comparing the baseline, and running approved checks…"); setError("");
    try {setRun(await api<Run>("approvals", {proposal_id: proposal.id, approved: true}));} catch(e) {setError((e as Error).message);} finally {setBusy("");}
  };
  const select = (issue: Issue) => {setSelected(issue); setProposal(null); setRun(null); setConsent(false); setError("");};
  const repo = repos.find(item => item.id === repoId);
  const issues = scan?.issues.filter(item => filter === "all" || (filter === "withheld" ? item.withheld : item.evidence.tool === "Ruff")) || [];
  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to main content</a>
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="PatchGardener home"><span className="brand-symbol"><Sprout size={25}/></span><span>patch<span className="brand-light">gardener</span><span className="brand-dot">.</span></span></a>
      <div className="workspace-label">YOUR WORKSPACE <span>LOCAL</span></div>
      <nav aria-label="Main navigation">
        <button className={view === "garden" ? "nav-item active" : "nav-item"} onClick={() => setView("garden")}><Leaf size={18}/> Repository garden <ChevronRight size={15}/></button>
        <button className={view === "audit" ? "nav-item active" : "nav-item"} onClick={() => {setView("audit"); void loadAudit();}}><History size={18}/> Activity log</button>
        <button className={view === "settings" ? "nav-item active" : "nav-item"} onClick={() => setView("settings")}><Settings2 size={18}/> Local setup</button>
      </nav>
      <div className="sidebar-note"><div className="tiny-label"><ShieldCheck size={16}/> A GENTLE PAIR OF HANDS</div><p>Small patches.<br/>Your approval.<br/>Always your repository.</p><div className="note-line"/><span>No cloud. No auto-push.</span></div>
      <div className="sidebar-bottom"><div className="avatar">PG</div><div>Personal workspace<small>Local-first · v0.1.0</small></div><LockKeyhole size={15}/></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="breadcrumb"><FolderGit2 size={17}/><span>Workspace</span><ChevronRight size={14}/><strong>{repo?.name || "Repository garden"}</strong></div><div className={`model-pill ${health?.model.available ? "online" : "offline"}`} title={health?.model.message || "Checking backend connection"}><span className="status-dot"/>{health?.model.available ? `${health.model.model} · local` : health ? "Model unavailable" : "Connecting locally"}</div></header>
      <main id="main">
        {error && <div role="alert" className="error-banner"><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError("")}><X size={18}/></button></div>}
        {busy && <div role="status" aria-live="polite" className="progress-banner"><LoaderCircle className="spin" size={18}/>{busy}</div>}
        {view === "garden" && <>
          <section className="hero"><div><div className="eyebrow"><span/> A LITTLE MAINTENANCE GOES A LONG WAY</div><h1>Less tending.<br/><em>More growing.</em></h1><p>Let the small fixes find their way to you.<br/>Grounded in your code. Reviewed by you.</p></div><div className="garden-art" aria-hidden="true"><div className="art-orbit"/><div className="art-orbit small"/><div className="art-leaf one"/><div className="art-leaf two"/><div className="art-leaf three"/><div className="art-stem"/><div className="art-pot"/><span className="art-plus plus-one">+</span><span className="art-plus plus-two">+</span><div className="art-caption">good code takes a little care</div></div></section>
          <section className="repository-bar" aria-label="Repository selection"><div className="repo-icon"><FolderGit2 size={23}/></div><div className="repo-select"><label htmlFor="repo">REPOSITORY</label><select id="repo" value={repoId} disabled={!!busy} onChange={e => {setRepoId(e.target.value); setScan(null); setSelected(null); setProposal(null); setRun(null);}}>{repos.length ? repos.map(item => <option key={item.id} value={item.id}>{item.name}</option>) : <option value="demo">meadow-notes</option>}</select></div>{repo?.synthetic && <span className="tag neutral">Synthetic demo</span>}<span className="repo-branch"><GitBranch size={15}/> isolated copies</span><Button onClick={doScan} disabled={!!busy || !repos.length}><ScanLine size={17}/>{scan ? "Scan again" : "Scan repository"}</Button></section>
          <section className="metrics" aria-label="Scan statistics"><Metric icon={<FileSearch/>} label="Files inspected" value={scan ? String(scan.files) : "—"} detail={scan ? `${(scan.bytes / 1024).toFixed(1)} KB · allowlisted source` : "Ready when you are"}/><Metric icon={<Sprout/>} label="Small things to tend" value={scan ? String(scan.issues.length) : "—"} detail={scan ? `${scan.issues.filter(item => !item.withheld).length} eligible for a proposal` : "Ruff + Markdown checks"}/><Metric icon={<ShieldCheck/>} label="Held for human review" value={scan ? String(scan.issues.filter(item => item.withheld).length) : "—"} detail="Protected paths stay in your hands"/><Metric icon={<CheckCheck/>} label="Verified in this review" value={run ? String(run.resolved) : "—"} detail={run ? `${run.regressions} regressions · source ${run.source_unchanged ? "unchanged" : "changed"}` : "Evidence before confidence"}/></section>
          <section className="work-section"><div className="section-heading"><div><div className="eyebrow">THE MAINTENANCE QUEUE</div><h2>A few things worth a look<span className="heading-dot">.</span></h2></div>{scan && <span className="scan-time"><Clock3 size={14}/> Scanned in {(scan.duration_ms/1000).toFixed(2)}s</span>}</div>
          <div className="queue-layout"><div className="queue-card"><div className="queue-toolbar"><div role="group" aria-label="Issue filters">{[["all", "All findings"], ["ruff", "Python"], ["withheld", "Withheld"]].map(([id,label]) => <button key={id} aria-pressed={filter === id} className={filter === id ? "filter active" : "filter"} onClick={() => setFilter(id)}>{label}{id === "all" && scan && <span>{scan.issues.length}</span>}</button>)}</div><Code2 size={16}/></div>
          {!scan ? <div className="empty-state"><div className="empty-icon"><Sprout size={31}/></div><h3>Every garden starts with a look around.</h3><p>Scan the fictional Meadow Notes repository to find<br/>real lint and documentation issues.</p><span><ShieldCheck size={14}/> Scanning never changes your source files</span></div> : issues.length === 0 ? <div className="empty-state"><Check size={28}/><h3>Nothing in this patch of the garden.</h3><p>Try another filter or select a different repository.</p></div> : <div className="issue-list">{issues.map(issue => <button key={issue.id} className={`issue-row ${selected?.id === issue.id ? "selected" : ""}`} onClick={() => select(issue)} aria-pressed={selected?.id === issue.id}><span className={`issue-symbol ${issue.withheld ? "protected" : issue.evidence.tool === "Ruff" ? "python" : "docs"}`}>{issue.withheld ? <LockKeyhole size={17}/> : issue.evidence.tool === "Ruff" ? <Code2 size={17}/> : <BookOpen size={17}/>}</span><span className="issue-info"><strong>{issue.title}</strong><span className="file-location">{issue.evidence.path}<span>:{issue.evidence.line}</span><i>·</i>{issue.evidence.code}</span></span><span className={`tag ${issue.withheld ? "amber" : "neutral"}`}>{issue.withheld ? "Withheld" : issue.severity}</span><ChevronRight size={16}/></button>)}</div>}
          <div className="queue-footer"><span className="status-dot"/> Deterministic scanners find the issue. Local AI proposes the fix.</div></div>
          <aside className="how-card"><div className="how-icon"><Sprout size={24}/></div><h3>Careful by design.</h3><p>A fix should earn your trust,<br/>one small step at a time.</p><ol><li><span>01</span><div><strong>Find the evidence</strong><small>Exact file, line, and scanner.</small></div></li><li><span>02</span><div><strong>Review a local AI patch</strong><small>A small diff with clear risk rules.</small></div></li><li><span>03</span><div><strong>Approve, then verify</strong><small>In a copy. With a real baseline.</small></div></li></ol><div className="how-bottom"><LockKeyhole size={14}/> Your original stays yours.</div></aside></div></section>
          {selected && <section className="review-section" aria-label="Patch review"><div className="section-heading"><div><div className="eyebrow">ONE SMALL, REVIEWABLE CHANGE</div><h2>{run ? "The results are in." : "Take a closer look."}</h2></div><span className="tag neutral">{selected.evidence.path}:{selected.evidence.line}</span></div><div className="evidence-card"><div className="evidence-title"><CircleDot size={17}/><strong>{selected.evidence.tool} evidence</strong><span className="tag neutral">{selected.evidence.code}</span></div><pre><span>{selected.evidence.line}</span> {selected.evidence.excerpt}</pre><p>{selected.evidence.message}</p>{selected.withheld ? <div className="withheld-notice"><LockKeyhole size={17}/>{selected.reason}</div> : !proposal && <Button onClick={propose} disabled={!!busy || !health?.model.available}><Sparkles size={16}/> Propose a local AI patch<ArrowRight size={16}/></Button>}</div>
          {proposal && <div className="proposal-card"><div className="proposal-heading"><div><span className="eyebrow">PROPOSED BY {proposal.model.toUpperCase()}</span><h3>{proposal.summary}</h3><small>{(proposal.inference_ms/1000).toFixed(1)}s local inference · {proposal.lines_changed} changed line(s) · digest {proposal.model_digest.slice(0,12)}</small></div><span className={`tag ${proposal.risk === "medium" ? "amber" : "green"}`}>{proposal.risk} risk</span></div><div className="diff-grid"><CodePane title="Original" text={Object.values(proposal.before)[0]} other={Object.values(proposal.after)[0]} kind="before"/><CodePane title="Proposed" text={Object.values(proposal.after)[0]} other={Object.values(proposal.before)[0]} kind="after"/></div><div className="risk-reasons"><strong><ShieldCheck size={16}/> Why this risk level?</strong>{proposal.reasons.map(reason => <p key={reason.rule}><Check size={14}/>{reason.explanation}</p>)}</div>{!run && <div className="approval-bar"><label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} disabled={!!busy}/><span>I reviewed this diff and approve applying it to an isolated copy.</span></label><Button onClick={approve} disabled={!consent || !!busy}><Play size={16}/> Approve & validate copy</Button></div>}
          {run && <div className={`result-panel ${run.verdict}`} role="status"><div className="result-title"><CheckCheck size={26}/><div><h3>{run.verdict === "passed" ? "A small fix. A verified improvement." : "This patch needs another look."}</h3><p>{run.resolved} issue resolved · {run.regressions} regressions · original {run.source_unchanged ? "unchanged" : "changed"}</p></div><span className="tag green">{run.verdict}</span></div><p className="baseline-note">{run.before_issues} → {run.after_issues} total findings. Existing findings remain visible; a passing patch means the selected issue is resolved without new findings.</p><div className="checks-grid">{[{label: "Before · baseline", checks: run.baseline}, {label: "After · isolated copy", checks: run.checks}].map(group => <div key={group.label}><h4>{group.label}</h4>{group.checks.map(check => <details key={check.name}><summary><span className={`check-dot ${check.status}`}/>{check.name}<span>{check.status}</span></summary><pre>{check.output}</pre></details>)}</div>)}</div><details className="copy-path"><summary>Isolated copy location</summary><code>{run.copy_path}</code></details></div>}
          <div className="export-bar"><span><GitBranch size={15}/> No commits. No pushes. You decide what ships.</span><Button variant="outline" asChild><a href={`/api/exports/${proposal.id}`} download><ArrowDownToLine size={16}/> Export .patch</a></Button></div></div>}</section>}
          <footer className="page-footer"><span><Sprout size={15}/> A healthier codebase, one small patch at a time.</span><span>LOCAL AI. HUMAN JUDGMENT.</span></footer>
        </>}
        {view === "audit" && <section className="secondary-view"><div className="eyebrow">A TRANSPARENT TRAIL</div><h1>Every little action.</h1><p>Local scans, proposal gates, approvals, and validation outcomes.</p><Button variant="outline" onClick={loadAudit}><History size={16}/> Refresh activity</Button><div className="audit-list">{events.length === 0 ? <p>No activity yet. Scan a repository to get started.</p> : events.map(event => <article key={event.id}><span className="audit-mark"><Check size={16}/></span><div><strong>{event.event.replaceAll(".", " · ")}</strong><time>{new Date(event.at).toLocaleString()}</time><pre>{JSON.stringify(event.detail, null, 2)}</pre></div></article>)}</div></section>}
        {view === "settings" && <section className="secondary-view"><div className="eyebrow">YOUR MACHINE, YOUR CODE</div><h1>Keep it close.</h1><p>Local inference and a deliberately narrow execution policy.</p><div className="settings-grid"><article className="evidence-card"><h2><Terminal size={22}/> Local model</h2><p>{health?.model.message || "Backend is not connected."}</p><pre>ollama pull qwen3:8b</pre><p>Qwen3-8B · Apache-2.0 · 8,192 token application context.</p><p>Ollama {health?.model.ollama_version || "version unavailable"}</p><Button variant="outline" onClick={refresh}>Recheck connection</Button></article><article className="evidence-card"><h2><FolderGit2 size={22}/> Add a repository</h2><p>Set <code>PG_REPO_ROOTS</code> to known-safe local directories before starting the backend. Separate paths with <code>;</code> on Windows or <code>:</code> on Linux/macOS.</p><p>External repositories receive static checks only. Their tests, install scripts, and commands are never executed.</p><p>Limits: 200 files, 64 KB per file, 1 MB total. Hidden files, secret-like content, symlinks and junctions are excluded.</p></article><article className="evidence-card"><h2><ShieldCheck size={22}/> What validation means</h2><p>A copy is separate from your source, but it is not an OS sandbox. Only the hash-verified built-in fixture runs its fixed unit tests.</p><p>Python edits are restricted to exact unused-import removal. Protected paths are withheld. Markdown links are checked against the allowlisted snapshot; external URLs and anchors are outside scope.</p><p>Data stays in the local <code>data/</code> directory, including source snapshots and the SQLite audit log.</p></article></div></section>}
      </main>
    </div>
  </div>;
}

function Metric({icon, label, value, detail}: {icon: React.ReactNode; label: string; value: string; detail: string}) { return <article className="metric"><div className="metric-top"><span>{label}</span>{icon}</div><strong>{value}</strong><small>{detail}</small></article>; }
function CodePane({title,text,other,kind}: {title: string; text: string; other: string; kind: string}) {
  const others = new Set(other.split("\n"));
  return <div className={`code-pane ${kind}`} role="region" aria-label={`${title} source`}><div className="code-label"><FileCode2 size={14}/><span className="code-title">{title}</span><span aria-hidden="true">{kind === "before" ? "−" : "+"}</span></div><pre>{text.replace(/\n$/, "").split("\n").map((line,index) => <div className={!others.has(line) ? "changed" : ""} key={index}><span className="line-number">{index+1}</span><code>{line || " "}</code></div>)}</pre></div>;
}
