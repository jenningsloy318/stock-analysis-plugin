/**
 * stock-analysis.js — canonical Dynamic Workflow script for the stock-analysis plugin
 *
 * Replaces the legacy async-pool orchestration in agents/team-lead.md. Invoked by
 * the team-lead agent via Workflow({scriptPath: '${PLUGIN_ROOT}/workflows/stock-analysis.js', args: {...}}).
 *
 * Requires Claude Code v2.1.154+ (Dynamic Workflows GA 2026-05-28) and TS Agent SDK
 * v0.3.149+. No fallback path — see CLAUDE.md "Workflow tool required" rule.
 *
 * Modes: pipeline | screen | analyze | compare | walk
 * All per-stage data stays in `let` variables here — the team-lead context window
 * only sees the final compressed return value at the end of `run()`.
 *
 * Author: Jennings Liu | Version: 2.01 | License: MIT
 */

export const meta = {
  name: 'stock-analysis',
  description: 'Unified equity research — screen GICS Level 4 → top companies → 11-stage deep-dive → scoring → adversarial verify → judge panel → 3-horizon reports → completeness critic',
  whenToUse: 'Equity research pipeline (pipeline/screen/analyze/compare/walk) — when the user wants to screen sectors, deep-dive specific tickers, compare stocks, or run a supply-chain walk. Triggered by the /stock-analysis:stock-analysis skill. Not for one-off market commentary or non-financial queries.',
  phases: [
    { title: 'Setup' },
    { title: 'Shared Data' },
    { title: 'Screening' },
    { title: 'Walk Chain' },
    { title: 'Per-Company Analysis' },
    { title: 'Scoring' },
    { title: 'Adversarial Verify' },
    { title: 'Judge Panel' },
    { title: 'Reports' },
    { title: 'Completeness Critic' },
    { title: 'Validation' },
    { title: 'Best Picks' },
  ],
}

// =============================================================================
// SCHEMAS — force structured JSON output from each subagent. Validation happens
// at the tool-call layer; the model retries on mismatch.
// =============================================================================
const VALIDATION_SCHEMA = {
  type: 'object',
  required: ['pass', 'reason'],
  properties: {
    pass: { type: 'boolean' },
    reason: { type: 'string' },
    gates_failed: { type: 'array', items: { type: 'string' } },
  },
}

const SHARED_DATA_SCHEMA = {
  type: 'object',
  required: ['status', 'files'],
  properties: {
    status: { type: 'string', enum: ['ok', 'partial', 'failed'] },
    files: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
}

const SECTOR_SCORES_SCHEMA = {
  type: 'object',
  required: ['sub_industries'],
  properties: {
    sub_industries: {
      type: 'array',
      items: {
        type: 'object',
        required: ['code', 'score'],
        properties: {
          code: { type: 'string' },         // GICS Level 4 code
          name: { type: 'string' },
          score: { type: 'number' },        // 0-100 composite
          dim_breakdown: { type: 'object' },
        },
      },
    },
  },
}

const SUB_INDUSTRY_DEEPDIVE_SCHEMA = {
  type: 'object',
  required: ['code', 'thesis', 'companies'],
  properties: {
    code: { type: 'string' },
    thesis: { type: 'string' },
    porter_summary: { type: 'string' },
    companies: {
      type: 'array',
      items: {
        type: 'object',
        required: ['ticker'],
        properties: {
          ticker: { type: 'string' },
          name: { type: 'string' },
          market_cap_usd: { type: 'number' },
          current_price: { type: 'number' },
        },
      },
    },
  },
}

const COMPANY_LIST_SCHEMA = {
  type: 'object',
  required: ['companies'],
  properties: {
    companies: {
      type: 'array',
      items: {
        type: 'object',
        required: ['ticker', 'score'],
        properties: {
          ticker: { type: 'string' },
          name: { type: 'string' },
          sub_industry_code: { type: 'string' },
          score: { type: 'number' },          // composite 0-100
          current_price: { type: 'number' },
          price_filter_pass: { type: 'boolean' },
          chain_health_adj: { type: 'number' },  // ±0.10 ecosystem bonus/penalty applied at screening
        },
      },
    },
  },
}

// Supply chain ecosystem health — lightweight check during screening + deep analysis in Stage 8
const ECOSYSTEM_HEALTH_SCHEMA = {
  type: 'object',
  required: ['ticker', 'ecosystem_momentum'],
  properties: {
    ticker: { type: 'string' },
    upstream: {
      type: 'object',
      properties: {
        health_score: { type: 'number' },           // 1-10
        trend: { type: 'string', enum: ['positive', 'negative', 'mixed', 'unknown'] },
        companies_checked: { type: 'number' },
      },
    },
    downstream: {
      type: 'object',
      properties: {
        health_score: { type: 'number' },           // 1-10
        trend: { type: 'string', enum: ['positive', 'negative', 'mixed', 'unknown'] },
        companies_checked: { type: 'number' },
      },
    },
    ecosystem_momentum: {
      type: 'object',
      required: ['score', 'direction'],
      properties: {
        score: { type: 'number' },                  // 1-10 composite
        direction: { type: 'string', enum: ['positive', 'negative', 'mixed', 'divergent'] },
        convergence: { type: 'boolean' },           // true if upstream+downstream agree
      },
    },
    propagation_risks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          direction: { type: 'string', enum: ['upstream', 'downstream'] },
          company: { type: 'string' },
          risk: { type: 'string' },
          severity: { type: 'string', enum: ['HIGH', 'MEDIUM', 'LOW'] },
        },
      },
    },
    chain_health_adjustment: { type: 'number' },    // ±0.10 screening bonus/penalty
  },
}

// Industry Trajectory — is the sector/sub-industry getting better or worse?
const INDUSTRY_TRAJECTORY_SCHEMA = {
  type: 'object',
  required: ['trajectory_score', 'trajectory_direction'],
  properties: {
    etf: { type: 'string' },
    trajectory_score: { type: 'number' },           // 1-10 composite
    trajectory_direction: { type: 'string', enum: ['strong_improvement', 'improving', 'mixed', 'deteriorating', 'strong_deterioration', 'unknown'] },
    positive_signals: { type: 'number' },
    negative_signals: { type: 'number' },
    dimensions: { type: 'object' },                 // per-dimension breakdown
  },
}

const COMPANY_ORCHESTRATOR_RESULT_SCHEMA = {
  type: 'object',
  required: ['ticker', 'status', 'stages_completed'],
  properties: {
    ticker: { type: 'string' },
    rank: { type: 'string' },
    status: { type: 'string', enum: ['completed', 'partial', 'failed'] },
    stages_completed: { type: 'array', items: { type: 'number' } },
    stages_failed: { type: 'array', items: { type: 'number' } },
    key_findings: { type: 'string' },
    company_dir: { type: 'string' },
  },
}

const SCORING_RESULT_SCHEMA = {
  type: 'object',
  required: ['companies'],
  properties: {
    companies: {
      type: 'array',
      items: {
        type: 'object',
        required: ['rank', 'ticker', 'composite_score'],
        properties: {
          rank: { type: 'string' },
          ticker: { type: 'string' },
          composite_score: { type: 'number' },
          conviction: { type: 'string', enum: ['HIGH', 'MEDIUM', 'LOW'] },
          dim_breakdown: { type: 'object' },
        },
      },
    },
    ranking_json_path: { type: 'string' },
  },
}

const WALK_RESULT_SCHEMA = {
  type: 'object',
  required: ['theme', 'candidates'],
  properties: {
    theme: { type: 'string' },
    layers: { type: 'array' },
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        required: ['ticker'],
        properties: {
          ticker: { type: 'string' },
          name: { type: 'string' },
          tier: { type: 'string' },
          asymmetry_score: { type: 'number' },
        },
      },
    },
  },
}

// Adversarial bear-case verifier — one skeptic per lens
const REFUTE_VERDICT_SCHEMA = {
  type: 'object',
  required: ['refuted', 'confidence'],
  properties: {
    refuted: { type: 'boolean' },                      // true = bear case is real
    confidence: { type: 'number', minimum: 0, maximum: 1 },
    reason: { type: 'string' },                        // 1-3 sentences
    falsifiable_signal: { type: 'string' },            // what would change the verdict
  },
}

// Judge-panel lens scoring — one per investment framework
const LENS_VERDICT_SCHEMA = {
  type: 'object',
  required: ['lens', 'score', 'verdict'],
  properties: {
    lens: { type: 'string', enum: ['buffett', 'lynch', 'marks', 'druckenmiller'] },
    score: { type: 'number', minimum: 0, maximum: 10 },
    verdict: { type: 'string', enum: ['STRONG_BUY', 'BUY', 'HOLD', 'AVOID'] },
    rationale: { type: 'string' },
    dimensions_matched: { type: 'array', items: { type: 'string' } },
    dimensions_violated: { type: 'array', items: { type: 'string' } },
  },
}

// Completeness critic on final reports — kill-switch falsifiability + missing-modality scan
const CRITIC_FINDING_SCHEMA = {
  type: 'object',
  required: ['ticker', 'horizon', 'gaps', 'kill_switch_check'],
  properties: {
    ticker: { type: 'string' },
    horizon: { type: 'string', enum: ['long', 'mid', 'short'] },
    gaps: {                                             // missing modalities/claims
      type: 'array',
      items: {
        type: 'object',
        required: ['category', 'severity'],
        properties: {
          category: { type: 'string' },                 // e.g., 'modality', 'claim', 'source'
          severity: { type: 'string', enum: ['HIGH', 'MEDIUM', 'LOW'] },
          description: { type: 'string' },
          suggested_fix: { type: 'string' },
        },
      },
    },
    kill_switch_check: {
      type: 'object',
      required: ['present', 'falsifiable'],
      properties: {
        present: { type: 'boolean' },
        falsifiable: { type: 'boolean' },               // measurable + has a clear trigger
        text: { type: 'string' },                       // verbatim kill switch from report
        issues: { type: 'array', items: { type: 'string' } },
      },
    },
    overall_quality: { type: 'string', enum: ['PASS', 'PASS_WITH_GAPS', 'FAIL'] },
  },
}

// Equity report writer — structured confirmation so null-on-failure is detectable
const REPORT_RESULT_SCHEMA = {
  type: 'object',
  required: ['ticker', 'horizon', 'status', 'file_path'],
  properties: {
    ticker: { type: 'string' },
    horizon: { type: 'string', enum: ['long', 'mid', 'short'] },
    status: { type: 'string', enum: ['written', 'partial', 'failed'] },
    file_path: { type: 'string' },              // absolute or relative path of the written .md report
    sections_written: { type: 'number' },       // count of major sections successfully populated
    sections_total: { type: 'number' },         // 24 for full report (per template)
    missing_sections: {                         // sections that could not be populated
      type: 'array',
      items: { type: 'string' },
    },
    conviction_score: { type: 'number' },       // final composite score 1-10
    rating: { type: 'string' },                 // Strong Buy / Buy / Hold / Sell / Strong Sell
    kill_switch: { type: 'string' },            // verbatim kill switch text from the report
    validation_passed: { type: 'boolean' },     // did validate_report.py pass?
    validation_errors: {                        // gate failures if validation_passed=false
      type: 'array',
      items: { type: 'string' },
    },
    notes: { type: 'string' },                  // any issues or warnings during generation
  },
}

// Best Picks highlight — structured confirmation
const BEST_PICKS_RESULT_SCHEMA = {
  type: 'object',
  required: ['status', 'file_path', 'companies_included'],
  properties: {
    status: { type: 'string', enum: ['written', 'failed'] },
    file_path: { type: 'string' },
    companies_included: { type: 'number' },     // how many companies in the highlights table
    has_bear_case_column: { type: 'boolean' },
    has_panel_consensus_column: { type: 'boolean' },
    has_kill_switch: { type: 'boolean' },
    has_current_price: { type: 'boolean' },
    notes: { type: 'string' },
  },
}

// =============================================================================
// MAIN
// =============================================================================

// Phase must be declared before any agent() call
phase('Setup')

// ---------------------------------------------------------------------------
// Args normalization — handle string/undefined args gracefully.
// When invoked by name (Workflow({name: "stock-analysis"})), the runtime may
// pass args as a string and agent() calls may not work (return null in 0s).
// ALL path resolution must work WITHOUT agent calls as a fallback.
// ---------------------------------------------------------------------------
let _args = args
if (typeof _args === 'string') {
  log(`[args] received string: "${_args}" — parsing inline`)
  const modeMatch = _args.match(/--mode\s+(\w+)/)
  const tickerMatch = _args.match(/(?:analyze|compare)\s+([A-Za-z,.]+)/i)
  const themeMatch = _args.match(/walk\s+(.+?)(?:--|$)/i)
  const topMatch = _args.match(/--top-industry\s+(\d+)/)
  const totalMatch = _args.match(/--total-company\s+(\d+)/)
  const universeMatch = _args.match(/--universe\s+(\w+)/)
  _args = {
    request: _args,
    mode: modeMatch ? modeMatch[1] : (tickerMatch ? 'analyze' : 'pipeline'),
    tickers: tickerMatch ? tickerMatch[1].toUpperCase().split(',').map(t => t.trim()).filter(Boolean) : [],
    theme: themeMatch ? themeMatch[1].trim() : undefined,
    top_industry: topMatch ? parseInt(topMatch[1]) : undefined,
    total_company: totalMatch ? parseInt(totalMatch[1]) : undefined,
    universe: universeMatch ? universeMatch[1].toUpperCase() : 'US',
  }
}
if (!_args || typeof _args !== 'object') {
  _args = {}
}

// plugin_root: try agent discovery, fall back to common paths
if (!_args.plugin_root) {
  log(`[args] plugin_root missing — trying agent discovery then static fallback`)
  const discovery = await agent(
    `Run: find ~/.claude/plugins -name "stock-analysis.js" -path "*/workflows/*" 2>/dev/null | head -1 | xargs dirname | xargs dirname\n` +
    `Return JSON: {"plugin_root": "<result>"}`,
    { label: 'discover-plugin-root', phase: 'Setup', agentType: 'general-purpose',
      schema: { type: 'object', required: ['plugin_root'], properties: { plugin_root: { type: 'string' } } } }
  )
  if (discovery?.plugin_root) {
    _args.plugin_root = discovery.plugin_root
  } else {
    // Static fallback — check common install paths without agent
    log(`[args] agent discovery returned null — using static fallback paths`)
    _args.plugin_root = '${PLUGIN_ROOT}'  // harness-resolved at load time
  }
}

// run_id: try agent, fall back to static placeholder
if (!_args.run_id) {
  const now = await agent(
    `Run: date -u +%Y%m%d%H%M\nReturn JSON: {"run_id": "<result>"}`,
    { label: 'generate-run-id', phase: 'Setup', agentType: 'general-purpose',
      schema: { type: 'object', required: ['run_id'], properties: { run_id: { type: 'string' } } } }
  )
  _args.run_id = now?.run_id || '202606250000'
}

const RUN_ID = _args.run_id
const PLUGIN_ROOT = _args.plugin_root || ''
const MODE = _args.mode || 'pipeline'
const TOP_INDUSTRY = _args.top_industry
const TOTAL_COMPANY = _args.total_company
const TICKERS = _args.tickers || []
const THEME = _args.theme
const UNIVERSE = _args.universe || 'US'
const OUTPUT_DIR = `./reports/${RUN_ID}`

if (!PLUGIN_ROOT) {
  return { status: 'failed', stage: 0, reason: `Could not resolve plugin_root. Pass it in args or ensure the plugin is installed under ~/.claude/plugins/.` }
}

// Listing-universe filter — deterministic JS-side gate so the LLM screener can't drift.
// US tickers: bare letters [A-Z]{1,5}, optional class suffix (e.g. BRK.B). NOT .TO/.HK/.SH/.SZ/.T/.L/etc.
// CN tickers: .SH or .SZ suffix.
// ALL: everything passes.
const isUSTicker = (t) => /^[A-Z]{1,5}(\.[A-Z])?$/.test(t || '')
const isCNTicker = (t) => /\.(SH|SZ)$/i.test(t || '')
const passUniverse = (t) => {
  if (UNIVERSE === 'ALL') return true
  if (UNIVERSE === 'US')  return isUSTicker(t)
  if (UNIVERSE === 'CN')  return isCNTicker(t)
  return true
}

const validModes = ['pipeline', 'screen', 'analyze', 'compare', 'walk']
if (!validModes.includes(MODE)) {
  return { status: 'failed', stage: 0, reason: `Invalid mode: ${MODE}. Expected one of ${validModes.join(', ')}.` }
}

log(`[stock-analysis] mode=${MODE} run_id=${RUN_ID} top_industry=${TOP_INDUSTRY} total_company=${TOTAL_COMPANY}`)
log(`[stock-analysis] output_dir=${OUTPUT_DIR}`)

// =============================================================================
// WORKFLOW TRACKING — persistent state file at ${OUTPUT_DIR}/workflow-tracking.json
// Updated at each phase start/end for observability and resume support.
// =============================================================================
const TRACKING_PATH = `${OUTPUT_DIR}/workflow-tracking.json`

// Phase registry — maps phase names to IDs for consistent ordering
const PHASE_REGISTRY = {
  'Setup': 0,
  'Shared Data': 1,
  'Walk Chain': 2,
  'Screening': 3,
  'Per-Company Analysis': 4,
  'Scoring': 5,
  'Adversarial Verify': 6,
  'Judge Panel': 7,
  'Reports': 8,
  'Completeness Critic': 9,
  'Validation': 10,
  'Best Picks': 11,
}

// Determine which phases apply based on mode
const getPhasesForMode = (mode) => {
  if (mode === 'walk') return ['Setup', 'Shared Data', 'Walk Chain', 'Investability Filter', 'Per-Company Analysis', 'Scoring', 'Reports', 'Validation']
  if (mode === 'screen') return ['Setup', 'Shared Data', 'Screening', 'Reports', 'Validation', 'Best Picks']
  // pipeline, analyze, compare
  return ['Setup', 'Shared Data', 'Screening', 'Per-Company Analysis', 'Scoring', 'Adversarial Verify', 'Judge Panel', 'Reports', 'Completeness Critic', 'Validation', 'Best Picks']
}

const tracking = {
  run_id: RUN_ID,
  mode: MODE,
  universe: UNIVERSE,
  tickers: TICKERS.length ? TICKERS : [],
  theme: THEME || null,
  startedAt: args.started_at || null,   // ISO timestamp passed from team-lead
  completedAt: null,
  status: 'running',
  phases: getPhasesForMode(MODE).map(name => ({
    id: PHASE_REGISTRY[name],
    name,
    status: 'pending',
    startedAt: null,
    completedAt: null,
    agents_spawned: 0,
    agents_succeeded: 0,
    agents_failed: 0,
    result_summary: null,
  })),
  companies: [],
  reports: [],
  validation_gates: {
    data_freshness: null,
    screening: null,
    scoring: null,
    reports: null,
    best_picks: null,
  },
  metrics: {
    total_agents_spawned: 0,
    total_agents_succeeded: 0,
    total_agents_failed: 0,
    total_retries: 0,
    report_iterations: 0,
  },
  errors: [],
}

// Helper: find phase entry by name
const getPhase = (name) => tracking.phases.find(p => p.name === name)

// Helper: mark phase as started + auto-persist
const trackPhaseStart = async (name) => {
  const p = getPhase(name)
  if (p) {
    p.status = 'in_progress'
    p.startedAt = args.started_at ? new Date(args.started_at).toISOString() : null
  }
  const id = PHASE_REGISTRY[name] ?? '?'
  await persistTracking(`tracking:s${id}:in_progress`, name)
}

// Helper: mark phase as completed with stats + auto-persist to disk
const trackPhaseEnd = async (name, opts) => {
  const p = getPhase(name)
  if (p) {
    p.status = opts?.failed ? 'failed' : 'completed'
    p.completedAt = p.startedAt  // best-effort — can't access clock
    p.agents_spawned = opts?.spawned ?? p.agents_spawned
    p.agents_succeeded = opts?.succeeded ?? p.agents_succeeded
    p.agents_failed = opts?.failed_count ?? p.agents_failed
    p.result_summary = opts?.summary ?? null
    // Roll up into metrics
    tracking.metrics.total_agents_spawned += (opts?.spawned ?? 0)
    tracking.metrics.total_agents_succeeded += (opts?.succeeded ?? 0)
    tracking.metrics.total_agents_failed += (opts?.failed_count ?? 0)
  }
  const id = PHASE_REGISTRY[name] ?? '?'
  await persistTracking(`tracking:s${id}:${opts?.failed ? 'failed' : 'complete'}`, name)
}

// Helper: persist tracking JSON to disk via a low-effort agent
const persistTracking = async (labelOverride, phaseName) => {
  const json = JSON.stringify(tracking, null, 2)
  const payload = json.length > 12000 ? json.slice(0, 12000) + '\n... (truncated)' : json
  await agentWithRetry(
    `Write the following JSON content to the file ${TRACKING_PATH}. ` +
    `Create the directory if needed. Write EXACTLY this content, no modifications:\n\n${payload}`,
    { label: labelOverride || 'persist:tracking', phase: phaseName || undefined, effort: 'low' }
  )
}

// Retry wrapper — retries agent() calls up to MAX_RETRIES on null returns
// (null = agent died on terminal API error after internal retries)
const MAX_RETRIES = 10
const agentWithRetry = async (prompt, opts) => {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    const result = await agent(prompt, opts)
    if (result !== null && result !== undefined) return result
    if (attempt < MAX_RETRIES) {
      log(`[retry] ${opts?.label || 'agent'} returned null — attempt ${attempt}/${MAX_RETRIES}, retrying...`)
      tracking.metrics.total_retries += 1
    }
  }
  log(`[retry] ${opts?.label || 'agent'} exhausted ${MAX_RETRIES} retries — returning null`)
  tracking.metrics.total_retries += 1
  tracking.errors.push({ phase: opts?.phase || 'unknown', agent_label: opts?.label || 'unknown', error: `exhausted ${MAX_RETRIES} retries`, fatal: false })
  return null
}

// Setup phase complete
await trackPhaseStart('Setup')
await trackPhaseEnd('Setup', { spawned: 0, succeeded: 0, failed_count: 0, summary: `mode=${MODE} run_id=${RUN_ID}` })
log(`[setup] complete: mode=${MODE}, run_id=${RUN_ID}, plugin_root=${PLUGIN_ROOT}`)

// -----------------------------------------------------------------------------
// PHASE 1 — Shared Data Collection (all modes)
// -----------------------------------------------------------------------------
phase('Shared Data')
await trackPhaseStart('Shared Data')
const sharedData = await agentWithRetry(
  `You are stock-analysis:data-collector. Fetch macro indicators, economic surprises, ` +
  `sector/sub-industry relative strength, market breadth, theme performance. ` +
  `plugin_root=${PLUGIN_ROOT} output_dir=${OUTPUT_DIR}. Run scripts via ` +
  `'uv run python ${PLUGIN_ROOT}/scripts/<script>.py'. Write all outputs under ` +
  `${OUTPUT_DIR}/. Return {status, files, notes} per schema.`,
  {
    agentType: 'stock-analysis:data-collector',
    schema: SHARED_DATA_SCHEMA,
    phase: 'Shared Data',
    label: 'data-collector',
    effort: 'low',
  }
)

if (!sharedData || sharedData.status === 'failed') {
  await trackPhaseEnd('Shared Data', { spawned: 1, succeeded: 0, failed_count: 1, summary: 'failed — data collection error', failed: true })
  tracking.status = 'failed'
  tracking.errors.push({ phase: 'Shared Data', agent_label: 'data-collector', error: sharedData?.notes || 'returned null', fatal: true })
  await persistTracking()
  return { status: 'failed', stage: 1, reason: 'Shared data collection failed', detail: sharedData?.notes }
}

// Stage 1.5 validation
const dataValid = await agentWithRetry(
  `You are stock-analysis:report-validator. Validate shared data freshness for ${OUTPUT_DIR}. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate data-freshness ` +
  `--output-dir ${OUTPUT_DIR}'. Return {pass, reason, gates_failed} per schema.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Shared Data', label: 'validate:data', effort: 'low' }
)
tracking.validation_gates.data_freshness = dataValid?.pass ?? false
if (!dataValid?.pass) {
  await trackPhaseEnd('Shared Data', { spawned: 2, succeeded: 1, failed_count: 1, summary: `failed — validation: ${dataValid?.reason}`, failed: true })
  tracking.status = 'failed'
  tracking.errors.push({ phase: 'Shared Data', agent_label: 'validate:data', error: dataValid?.reason || 'validation failed', fatal: true })
  await persistTracking()
  return { status: 'failed', stage: 1.5, reason: dataValid?.reason || 'Data validation failed' }
}
await trackPhaseEnd('Shared Data', { spawned: 2, succeeded: 2, failed_count: 0, summary: `ok — ${sharedData.files?.length || 0} files written` })
await persistTracking()

// -----------------------------------------------------------------------------
// PHASE 2 — Walk Mode (early branch, replaces screening + per-company)
// -----------------------------------------------------------------------------
if (MODE === 'walk') {
  phase('Walk Chain')
  await trackPhaseStart('Walk Chain')
  const walkResult = await agentWithRetry(
    `You are stock-analysis:roadmap-walker. Theme: "${THEME}". top_industry=${TOP_INDUSTRY || 7}. ` +
    `plugin_root=${PLUGIN_ROOT} output_dir=${OUTPUT_DIR} shared_data_path=${OUTPUT_DIR}/stage1.json. ` +
    `Perform top-down chain decomposition: anchor quantitative dated demand roadmap → ` +
    `reverse-walk finished-product→raw-substrate (≥5 layers) → score 4-element chokepoint ` +
    `checklist per layer → run score_bottleneck_asymmetry.py for each candidate → ` +
    `write walk_roadmap.json, walk_chain.json, walk_candidates.json, walk.md.`,
    { agentType: 'stock-analysis:roadmap-walker', schema: WALK_RESULT_SCHEMA, phase: 'Walk Chain', label: 'roadmap-walker' }
  )

  if (!walkResult) {
    await trackPhaseEnd('Walk Chain', { spawned: 1, succeeded: 0, failed_count: 1, summary: 'failed — walker returned null', failed: true })
    tracking.status = 'failed'
    await persistTracking()
    return { status: 'failed', stage: 'walk', reason: 'roadmap-walker returned null' }
  }
  await trackPhaseEnd('Walk Chain', { spawned: 1, succeeded: 1, failed_count: 0, summary: `ok — ${walkResult.candidates?.length || 0} candidates found` })

  // ─────────────────────────────────────────────────────────────────────────
  // Walk Phase 2: Investability Filter — quick data checks on top candidates
  // Filters out: illiquid micro-caps, distressed financials, Stage 4 declines
  // Uses: fetch_financials, fetch_technicals, compute_liquidity, fetch_supply_chain_ecosystem
  // ─────────────────────────────────────────────────────────────────────────
  const rawCandidates = (walkResult.candidates || []).filter(c => (c.asymmetry_score || 0) >= 50)
  const topCandidates = rawCandidates.slice(0, Math.min(rawCandidates.length, TOP_INDUSTRY || 7))

  let filteredWatchlist = topCandidates
  if (topCandidates.length > 0) {
    phase('Investability Filter')
    await trackPhaseStart('Investability Filter')
    log(`[walk] Running investability filter on ${topCandidates.length} candidates`)

    const filterResults = await parallel(topCandidates.map(c => () =>
      agentWithRetry(
        `You are stock-analysis:quant-analyst. QUICK investability check for walk-mode candidate ` +
        `ticker=${c.ticker} (theme: "${THEME}", layer: "${c.tier || ''}", asymmetry: ${c.asymmetry_score || 0}). ` +
        `plugin_root=${PLUGIN_ROOT} output_dir=${OUTPUT_DIR}. ` +
        `Run these scripts ONLY (quick check, not full analysis): ` +
        `1. uv run python ${PLUGIN_ROOT}/scripts/fetch_financials.py ${c.ticker} --output ${OUTPUT_DIR}/walk_filter_${c.ticker}_fin.json ` +
        `2. uv run python ${PLUGIN_ROOT}/scripts/fetch_technicals.py ${c.ticker} --period 1y --output ${OUTPUT_DIR}/walk_filter_${c.ticker}_tech.json ` +
        `3. uv run python ${PLUGIN_ROOT}/scripts/compute_liquidity.py ${c.ticker} --output ${OUTPUT_DIR}/walk_filter_${c.ticker}_liq.json ` +
        `4. uv run python ${PLUGIN_ROOT}/scripts/fetch_supply_chain_ecosystem.py ${c.ticker} --output ${OUTPUT_DIR}/walk_filter_${c.ticker}_eco.json ` +
        `\nEvaluate PASS/FAIL on 5 criteria: ` +
        `(a) Market cap ≥ $500M (investable size) ` +
        `(b) Average daily volume ≥ $5M (liquidity) ` +
        `(c) NOT Weinstein Stage 4 (not in structural decline) ` +
        `(d) Altman Z-Score NOT in Distress zone OR D/E < 5.0 (not near-bankrupt) ` +
        `(e) Ecosystem health NOT all-red (upstream+downstream not both collapsing) ` +
        `\nReturn: pass=true if ≥4/5 pass, pass=false if <4/5 pass. ` +
        `Include: market_cap, avg_volume, weinstein_stage, z_score, ecosystem_direction, current_price.`,
        {
          agentType: 'stock-analysis:quant-analyst',
          schema: {
            type: 'object',
            required: ['ticker', 'pass'],
            properties: {
              ticker: { type: 'string' },
              pass: { type: 'boolean' },
              market_cap: { type: 'number' },
              avg_daily_volume: { type: 'number' },
              weinstein_stage: { type: 'number' },
              z_score: { type: 'number' },
              ecosystem_direction: { type: 'string' },
              current_price: { type: 'number' },
              fail_reasons: { type: 'array', items: { type: 'string' } },
              pass_count: { type: 'number' },
            },
          },
          phase: 'Investability Filter',
          label: `filter:${c.ticker}`,
          effort: 'low',
        }
      )
    ))

    const passed = filterResults.filter(Boolean).filter(r => r.pass)
    const failed = filterResults.filter(Boolean).filter(r => !r.pass)
    log(`[walk] Investability: ${passed.length} passed, ${failed.length} filtered out`)

    if (failed.length > 0) {
      log(`[walk] Filtered out: ${failed.map(f => `${f.ticker}(${(f.fail_reasons || []).join(',')})`).join('; ')}`)
    }

    filteredWatchlist = passed.map(r => {
      const orig = topCandidates.find(c => c.ticker === r.ticker) || {}
      return { ...orig, ...r, rank: '000' }  // rank assigned below
    })

    await trackPhaseEnd('Investability Filter', {
      spawned: topCandidates.length,
      succeeded: passed.length,
      failed_count: failed.length,
      summary: `${passed.length}/${topCandidates.length} passed investability gate`,
    })
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Walk Phase 3: Full Per-Company Deep-Dive on filtered candidates
  // Re-uses the same pipeline logic as analyze/pipeline modes (Stage 5-16)
  // ─────────────────────────────────────────────────────────────────────────
  if (filteredWatchlist.length > 0) {
    // Assign ranks and convert to watchlist format for the per-company pipeline
    watchlist = filteredWatchlist.map((c, i) => ({
      rank: String(i + 1).padStart(3, '0'),
      ticker: c.ticker,
      name: c.name || c.ticker,
      price_filter_pass: true,
      walk_asymmetry: c.asymmetry_score,
      walk_tier: c.tier,
    }))
    log(`[walk] ${watchlist.length} candidates entering full deep-dive analysis (Stage 5-16)`)
    // Fall through to PHASE 5 (Per-Company Analysis) below — same as pipeline/analyze
  } else {
    // No candidates passed — write walk-only report and exit
    phase('Reports')
    await trackPhaseStart('Reports')
    await agentWithRetry(
      `You are stock-analysis:screening-report-writer. Write final walk report in 中文 ` +
      `to ${OUTPUT_DIR}/WALK_${THEME.replace(/\s+/g,'_')}_${RUN_ID}.md. Read walk_roadmap.json, ` +
      `walk_chain.json, walk_candidates.json. Note: ALL candidates failed investability filter ` +
      `(too small, illiquid, distressed, or Stage 4). Include 当前股价 and failure reasons.`,
      { agentType: 'stock-analysis:screening-report-writer', phase: 'Reports', label: 'walk-report' }
    )
    await trackPhaseEnd('Reports', { spawned: 1, succeeded: 1, failed_count: 0, summary: 'walk report (no investable candidates)' })

    phase('Validation')
    await trackPhaseStart('Validation')
    const walkValid = await agentWithRetry(
      `You are stock-analysis:report-validator. Validate walk report at ${OUTPUT_DIR}. ` +
      `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate report-quality ` +
      `--output-dir ${OUTPUT_DIR}'.`,
      { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:walk' }
    )
    await trackPhaseEnd('Validation', { spawned: 1, succeeded: 1, failed_count: 0, summary: walkValid?.pass ? 'passed' : `failed — ${walkValid?.reason}` })
    tracking.status = walkValid?.pass ? 'completed' : 'partial'
    tracking.completedAt = tracking.startedAt
    await persistTracking()
    return {
      status: walkValid?.pass ? 'completed' : 'partial',
      mode: 'walk',
      theme: THEME,
      candidates_found: walkResult.candidates?.length || 0,
      investable_count: 0,
      reason: 'All candidates failed investability filter',
      output_dir: OUTPUT_DIR,
    }
  }
}

// -----------------------------------------------------------------------------
// PHASE 3 — Screening (pipeline + screen modes)
// -----------------------------------------------------------------------------
let watchlist = []
if (MODE === 'pipeline' || MODE === 'screen') {
  phase('Screening')
  await trackPhaseStart('Screening')

  // Stage 2: sector screener over 3 parallel batches of ~54 GICS Level 4 sub-industries
  const batches = ['0-54', '55-108', '109-163']
  const sectorBatchResults = await parallel(batches.map((range, i) => () =>
    agentWithRetry(
      `You are stock-analysis:sector-screener. Process GICS Level 4 batch ${range} (i=${i}). ` +
      `Read shared data from ${OUTPUT_DIR}/stage1.json. Score 12 dimensions (Growth, Profitability, ` +
      `Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, RS, Cyclicality, Constituent ` +
      `Quality, Supply/Demand, Industry Trajectory). ` +
      `For Industry Trajectory: run 'uv run python ${PLUGIN_ROOT}/scripts/compute_industry_trajectory.py ` +
      `--etf [SUB_INDUSTRY_ETF]' for each sub-industry ETF proxy to assess whether the industry ` +
      `is improving or deteriorating (revenue acceleration, margin direction, RS momentum, fund flows, ` +
      `valuation change, capital cycle position). Factor trajectory_score into the composite. ` +
      `Write to ${OUTPUT_DIR}/stage2-batch-${i}.json.`,
      {
        agentType: 'stock-analysis:sector-screener',
        schema: SECTOR_SCORES_SCHEMA,
        phase: 'Screening',
        label: `sector:batch${i}`,
      }
    )
  ))

  // Aggregate top sub-industries from the 3 batches
  const allSubIndustries = sectorBatchResults
    .filter(Boolean)
    .flatMap(r => r.sub_industries || [])
    .sort((a, b) => b.score - a.score)
  const topSubIndustries = allSubIndustries.slice(0, TOP_INDUSTRY || (MODE === 'screen' ? 30 : 5))

  if (!topSubIndustries.length) {
    return { status: 'failed', stage: 2, reason: 'No sub-industries scored — sector-screener returned empty' }
  }
  log(`[screening] selected top ${topSubIndustries.length} sub-industries`)

  // Stage 3 + 4: pipeline — for each top sub-industry, deep-dive then company-screen
  // pipeline() runs items through stages WITHOUT a barrier — slow sub-industries don't
  // block fast ones from progressing to company screening.
  watchlist = await pipeline(
    topSubIndustries,
    si => agentWithRetry(
      `You are stock-analysis:sector-screener. Deep-dive sub-industry ${si.code} (${si.name}). ` +
      `Porter's Five Forces, TAM/SAM/SOM, catalysts, barriers, company universe, profit pools. ` +
      `Read shared data from ${OUTPUT_DIR}/stage1.json. Write to ${OUTPUT_DIR}/stage3-${si.code}.json.`,
      {
        agentType: 'stock-analysis:sector-screener',
        schema: SUB_INDUSTRY_DEEPDIVE_SCHEMA,
        phase: 'Screening',
        label: `deepdive:${si.code}`,
      }
    ),
    deepdive => agentWithRetry(
      `You are stock-analysis:company-screener. Screen companies in sub-industry ${deepdive.code} ` +
      `(${deepdive.companies?.length || 0} candidates). LISTING UNIVERSE: ${UNIVERSE} — ` +
      (UNIVERSE === 'US' ? `INCLUDE ONLY tickers listed on NYSE/NASDAQ (bare A-Z symbols, e.g. AAPL, BRK.B). ` +
        `EXCLUDE non-US listings: .T (Tokyo), .HK (Hong Kong), .SH/.SZ (China A-shares), .L (London), .TO (Toronto), .DE/.PA/.AS (Europe), .AX (Australia). ` :
       UNIVERSE === 'CN' ? `INCLUDE ONLY .SH and .SZ tickers (China A-shares). EXCLUDE all others. ` :
                            `Accept any listing exchange. `) +
      `Apply price filter (US < $100, China A-shares < ¥100, all other markets < $100 USD equiv). ` +
      `Score growth/profitability/moat/valuation/management/risk/liquidity. ` +
      `ALSO run 'uv run python ${PLUGIN_ROOT}/scripts/fetch_supply_chain_ecosystem.py [TICKER]' ` +
      `for each top-5 candidate to get ecosystem health. Apply chain_health_adj (±10% score bonus/penalty): ` +
      `ecosystem_momentum.score>=7 → +5-10% bonus, <=4 → -5-10% penalty, 4-7 → no adjustment. ` +
      `Include chain_health_adj in the company output. ` +
      `Write to ${OUTPUT_DIR}/stage4-${deepdive.code}.json.`,
      {
        agentType: 'stock-analysis:company-screener',
        schema: COMPANY_LIST_SCHEMA,
        phase: 'Screening',
        label: `screen:${deepdive.code}`,
      }
    )
  )

  // Flatten + rank top companies across ALL sub-industries (NOT quota per sub-industry).
  // Apply listing-universe gate deterministically as a backstop — LLM screener may drift.
  const allCompanies = (watchlist || [])
    .filter(Boolean)
    .flatMap(r => r.companies || [])
    .filter(c => c.price_filter_pass !== false)
    .filter(c => passUniverse(c.ticker))
    .sort((a, b) => b.score - a.score)
  watchlist = allCompanies.slice(0, TOTAL_COMPANY || 10).map((c, i) => ({
    ...c,
    rank: String(i + 1).padStart(3, '0'),
  }))

  log(`[screening] selected top ${watchlist.length} companies for deep-dive (universe=${UNIVERSE})`)

  // Stage 4.5 validation
  const screenValid = await agentWithRetry(
    `You are stock-analysis:report-validator. Validate screening completeness for ${OUTPUT_DIR}. ` +
    `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate screening-completeness ` +
    `--output-dir ${OUTPUT_DIR}'. Required: sub-industry leaderboard ≥10 entries with valid GICS ` +
    `codes, company watchlist ≥10 (or all if MODE=screen and top-industry<10), price filter applied.`,
    { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Screening', label: 'validate:screening', effort: 'low' }
  )
  if (!screenValid?.pass) {
    log(`[WARN] screening validation: ${screenValid?.reason}`)
    // Non-fatal — proceed but flag in final result
  }
  tracking.validation_gates.screening = screenValid?.pass ?? false
  const screenAgents = 3 + topSubIndustries.length * 2 + 1  // batches + pipeline(deepdive+screen) + validator
  const screenFailed = sectorBatchResults.filter(r => !r).length + (watchlist || []).filter(r => !r).length
  await trackPhaseEnd('Screening', { spawned: screenAgents, succeeded: screenAgents - screenFailed, failed_count: screenFailed, summary: `${watchlist.length} companies selected from ${topSubIndustries.length} sub-industries` })
  // Populate tracking.companies for pipeline mode
  tracking.companies = watchlist.map(c => ({ ticker: c.ticker, rank: c.rank, status: 'pending', stages_completed: [], stages_failed: [], current_stage: null }))
  await persistTracking()
}

// In analyze/compare modes, watchlist comes directly from args.tickers
if (MODE === 'analyze' || MODE === 'compare') {
  watchlist = TICKERS.map((t, i) => ({
    rank: String(i + 1).padStart(3, '0'),
    ticker: t,
    name: t,
    price_filter_pass: true, // user-specified override
  }))
  log(`[${MODE}] watchlist set from user-provided tickers: ${TICKERS.join(', ')}`)
}

// -----------------------------------------------------------------------------
// PHASE 4 — Screen-mode reports (early termination)
// -----------------------------------------------------------------------------
if (MODE === 'screen') {
  phase('Reports')
  await trackPhaseStart('Reports')
  const horizons = ['long', 'mid', 'short']
  await parallel(horizons.map(h => () =>
    agentWithRetry(
      `You are stock-analysis:screening-report-writer. Write ${h}-term screening report in 中文 ` +
      `to ${OUTPUT_DIR}/SCREEN_${h}_${RUN_ID}.md. Read stage2 sector scores + stage3 deep-dives + ` +
      `stage4 company watchlist. Include 推荐标的排名 (001, 002, ...) and 当前股价 for each company.`,
      { agentType: 'stock-analysis:screening-report-writer', phase: 'Reports', label: `report:screen:${h}` }
    )
  ))
  await trackPhaseEnd('Reports', { spawned: 3, succeeded: 3, failed_count: 0, summary: '3 screening reports written' })

  phase('Validation')
  await trackPhaseStart('Validation')
  const reportsValid = await agentWithRetry(
    `You are stock-analysis:report-validator. Validate screening reports at ${OUTPUT_DIR}. ` +
    `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate report-quality ` +
    `--output-dir ${OUTPUT_DIR}'.`,
    { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:screen-reports' }
  )
  await trackPhaseEnd('Validation', { spawned: 1, succeeded: 1, failed_count: 0, summary: reportsValid?.pass ? 'passed' : `failed — ${reportsValid?.reason}` })

  phase('Best Picks')
  await trackPhaseStart('Best Picks')
  await agentWithRetry(
    `You are stock-analysis:equity-report-writer. Write HIGHLIGHTS_BEST_PICKS.md in 中文 to ` +
    `${OUTPUT_DIR}/HIGHLIGHTS_BEST_PICKS.md. Top 5 sub-industries with kill switch and 当前股价.`,
    { agentType: 'stock-analysis:equity-report-writer', phase: 'Best Picks', label: 'best-picks' }
  )
  await trackPhaseEnd('Best Picks', { spawned: 1, succeeded: 1, failed_count: 0, summary: 'best picks written' })

  tracking.status = reportsValid?.pass ? 'completed' : 'partial'
  tracking.completedAt = tracking.startedAt
  await persistTracking()
  return {
    status: reportsValid?.pass ? 'completed' : 'partial',
    mode: 'screen',
    sub_industries_screened: watchlist.length,
    output_dir: OUTPUT_DIR,
  }
}

// -----------------------------------------------------------------------------
// PHASE 5 — Per-Company Deep-Dive (pipeline / analyze / compare modes)
//
// HARNESS CONSTRAINT: sub-agents spawned by a Workflow cannot themselves spawn
// further sub-agents via the Agent tool. That means the previous design (a
// company-orchestrator agent that manages stages 5-15 internally) is broken in
// this harness — orchestrators wrote orchestrator-status: failed with
// reason="no_spawn_tool_available". The fix is to drive the 4-wave dependency
// graph directly from this workflow script via parallel() + pipeline(), so the
// workflow itself is the only thing spawning specialist analysts.
//
// Per-company waves (encoded as pipeline stages — each runs after the prior):
//   Wave 1 (4 independent): Stage 5 fundamental | 7 industry | 9 macro | 13 alt-data
//   Wave 2 (depends on Wave 1): Stage 6 earnings-quality | 8 supply-chain | 10 valuation | 14 catalyst
//   Wave 3 (depends on Wave 2): Stage 11 market-regime | 12 risk
//   Wave 4 (A-share only):     Stage 15 china-market
// Within a wave, the analysts run via Promise.all (true parallel inside one
// company). Across companies, parallel(watchlist) fans out — the runtime caps
// total concurrency at min(16, cpu-2).
//
// File outputs (each analyst writes to disk so downstream waves can read them):
//   {company_dir}/stage{N}.md and {company_dir}/stage{N}.json
// -----------------------------------------------------------------------------
phase('Per-Company Analysis')
await trackPhaseStart('Per-Company Analysis')

const sharedDataPath = `${OUTPUT_DIR}/stage1.json`

// Build a per-stage prompt template — keeps the wave functions readable
const stagePrompt = (stageN, agentName, c, extra = '') => {
  const companyDir = `${OUTPUT_DIR}/${c.rank}-${c.ticker}`
  return (
    `You are stock-analysis:${agentName}. Run Stage ${stageN} analysis for ticker=${c.ticker}. ` +
    `plugin_root=${PLUGIN_ROOT} run_id=${RUN_ID} ` +
    `company_ticker=${c.ticker} company_rank=${c.rank} ` +
    `company_dir=${companyDir} shared_data_path=${sharedDataPath}. ` +
    `Run all required Python scripts via 'uv run python ${PLUGIN_ROOT}/scripts/<script>.py'. ` +
    `Write your stage summary to ${companyDir}/stage${stageN}.md and structured outputs to ` +
    `${companyDir}/stage${stageN}.json. If a checkpoint file already exists and looks complete, ` +
    `skip re-running expensive scripts and just confirm. Return a compressed completion summary ` +
    `(<500 tokens): {stage, status, files_written, key_findings}. NEVER return raw data.` +
    (extra ? ` ${extra}` : '')
  )
}

// Per-stage completion-summary schema (each analyst returns this — small object)
const STAGE_RESULT_SCHEMA = {
  type: 'object',
  required: ['stage', 'status'],
  properties: {
    stage: { type: 'number' },
    status: { type: 'string', enum: ['ok', 'partial', 'failed', 'skipped'] },
    files_written: { type: 'array', items: { type: 'string' } },
    key_findings: { type: 'string' },
    notes: { type: 'string' },
  },
}

const companyResults = await parallel(watchlist.map(c => () => pipeline(
  [c],

  // ─────────────────────────── Wave 1 ───────────────────────────
  // Stages 5, 7, 9, 13 — all independent. Run inside one company in parallel.
  async (co) => {
    const isAShare = (co.ticker || '').match(/\.(SH|SZ)$/) ? true : false
    const [s5, s7, s9, s13] = await Promise.all([
      agentWithRetry(stagePrompt(5, 'fundamental-analyst', co,
        `Focus: financial health — DuPont 5-factor, Piotroski F-Score, Lynch category, key ratios. ` +
        `Scripts: fetch_financials.py, calculate_metrics.py.`),
        { agentType: 'stock-analysis:fundamental-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s5` }),
      agentWithRetry(stagePrompt(7, 'industry-analyst', co,
        `Focus: Porter's Five Forces, TAM/SAM/SOM, moat assessment, BCG matrix, ecosystem mapping. ` +
        `ALSO run 'uv run python ${PLUGIN_ROOT}/scripts/compute_industry_trajectory.py ` +
        `--etf [INDUSTRY_ETF_PROXY] --output ${OUTPUT_DIR}/${co.rank}-${co.ticker}/industry_trajectory.json' ` +
        `to compute Industry Trajectory Score (是行业在变好还是变坏): revenue acceleration, margin direction, ` +
        `RS momentum, fund flows, valuation expansion/compression, capital cycle position. ` +
        `Explicitly state the industry life-cycle stage (emerging/growth/mature/declining) and ` +
        `capital cycle position (under-invested/mid-cycle/over-invested). ` +
        `REUSE industry thesis from ${OUTPUT_DIR}/stage3-*.json if present. Scripts: fetch_peer_universe.py, compute_industry_trajectory.py.`),
        { agentType: 'stock-analysis:industry-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s7` }),
      agentWithRetry(stagePrompt(9, 'macro-analyst', co,
        `Focus: Dalio economic cycle, Druckenmiller liquidity, Four-Box, Fed stance, CRP, FX exposure. ` +
        `REUSE macro data from ${sharedDataPath}. Scripts: fetch_global_macro.py, fetch_currency_exposure.py.`),
        { agentType: 'stock-analysis:macro-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s9` }),
      agentWithRetry(stagePrompt(13, 'alt-data-analyst', co,
        `Focus: digital footprint (web traffic, app rankings), NLP earnings call analysis, channel checks, ` +
        `transaction data. Scripts: fetch_alternatives.py, fetch_news_nlp.py, calculate_candor.py, ` +
        `analyze_earnings_transcript.py. ` +
        `For thematic / catalyst-driven theses ONLY (walk-mode candidates, news-triggered analyze runs), ` +
        `ALSO run analyze_alpha_elasticity.py to score Serenity-Alpha demand-to-financial transmission ` +
        `(category: HIGH_ELASTICITY_ALPHA / MODERATE_ELASTICITY_ALPHA / WATCH_ONLY / NARRATIVE_ONLY). ` +
        `SKIP for pure-fundamental deep-dives with no thematic catalyst.`),
        { agentType: 'stock-analysis:alt-data-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s13` }),
    ])
    return { ...co, isAShare, stages: { 5: s5, 7: s7, 9: s9, 13: s13 } }
  },

  // ─────────────────────────── Wave 2 ───────────────────────────
  // Stages 6 (←5), 8 (←7), 10 (←5+7), 14 (←13)
  async (co) => {
    const [s6, s8, s10, s14] = await Promise.all([
      agentWithRetry(stagePrompt(6, 'fundamental-analyst', co,
        `Focus: earnings quality — Beneish M-Score, Montier C-Score, accruals quality, cash conversion, ` +
        `capital allocation (Buffett retention test, buyback ROI, M&A track record), CEO quality score. ` +
        `Scripts: fetch_capital_structure.py, calculate_earnings_quality.py, diff_filings.py, ` +
        `audit_capital_allocation.py, score_ceo_quality.py. Read ${OUTPUT_DIR}/${co.rank}-${co.ticker}/stage5.json first.`),
        { agentType: 'stock-analysis:fundamental-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s6` }),
      agentWithRetry(stagePrompt(8, 'supply-chain-analyst', co,
        `Focus: Tier 1-3 supplier mapping, geographic concentration (HHI), chokepoint identification, ` +
        `disruption scenario modeling, inventory-to-sales analysis. Step 7b: bottleneck asymmetry composite. ` +
        `ALSO run 'uv run python ${PLUGIN_ROOT}/scripts/fetch_supply_chain_ecosystem.py ${co.ticker} ` +
        `--supply-chain-file ${OUTPUT_DIR}/${co.rank}-${co.ticker}/supply_chain.json ` +
        `--output ${OUTPUT_DIR}/${co.rank}-${co.ticker}/sc_ecosystem.json' — assess upstream supplier ` +
        `and downstream customer financial health (revenue growth, margins, stock momentum). ` +
        `Write ecosystem findings to sc_ecosystem.json. Flag propagation risks: if top supplier margin ` +
        `contracting >500bps or top customer rev declining >10% YoY → HIGH propagation risk. ` +
        `Scripts: fetch_supply_chain.py, fetch_supply_chain_ecosystem.py, score_bottleneck_asymmetry.py. ` +
        `Read ${OUTPUT_DIR}/${co.rank}-${co.ticker}/stage7.json first.`),
        { agentType: 'stock-analysis:supply-chain-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s8` }),
      agentWithRetry(stagePrompt(10, 'quant-analyst', co,
        `Focus: valuation — DCF+Monte Carlo, comps, SOTP, LBO floor, reverse DCF, margin of safety. ` +
        `Optionally read ${OUTPUT_DIR}/${co.rank}-${co.ticker}/bottleneck_asymmetry.json from Stage 8 ` +
        `and fold tier/asymmetry-band into valuation as ±15% qualitative adjustment. ` +
        `Scripts: calculate_metrics.py, forecast.py, fetch_private_comps.py. ` +
        `ALSO run compute_tam_adj_peg.py (TAM-runway + quality adjusted PEG) and ` +
        `compute_bayesian_growth.py (5-hypothesis intrinsic CAGR vs market-implied) — ` +
        `fold their category/verdict into the valuation summary as Serenity cross-checks. ` +
        `Read stage5.json and stage7.json first.`),
        { agentType: 'stock-analysis:quant-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s10` }),
      agentWithRetry(stagePrompt(14, 'catalyst-analyst', co,
        `Focus: catalyst calendar (FDA, earnings, product launches, regulatory), event-driven probability, ` +
        `pre/post-event drift (PEAD), catalyst sequencing. Use loop-until-dry catalyst discovery (see ` +
        `agent system prompt — up to 6 search rounds, exit on 2 consecutive empty rounds). ` +
        `Scripts: compute_earnings_edge.py, event_study.py. ` +
        `Read stage13.json (transcript NLP) first if present.`),
        { agentType: 'stock-analysis:catalyst-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s14` }),
    ])
    return { ...co, stages: { ...co.stages, 6: s6, 8: s8, 10: s10, 14: s14 } }
  },

  // ─────────────────────────── Wave 3 ───────────────────────────
  // Stages 11 (←10), 12 (←10)
  async (co) => {
    const [s11, s12] = await Promise.all([
      agentWithRetry(stagePrompt(11, 'quant-analyst', co,
        `Focus: market regime — Weinstein stage, CANSLIM, Soros reflexivity, Fama-French 5-factor attribution, ` +
        `options signals (IV, max pain, put/call), sentiment, institutional positioning, short interest, ` +
        `activist exposure, liquidity (Amihud), seasonality. Scripts: fetch_technicals.py, compute_factors.py, ` +
        `fetch_cot.py, calculate_options.py, fetch_sentiment.py, fetch_short_interest.py, ` +
        `fetch_activist_exposure.py, compute_liquidity.py, compute_seasonality.py, compute_earnings_edge.py. ` +
        `ALSO run compute_health_index.py (GF-DMA Health Index — fundamental speed × DMA structure × ` +
        `escape ratio) and fold the band (ELITE_HEALTHY / HEALTHY / MIXED / OVERHEATED / UNHEALTHY) ` +
        `alongside Weinstein stage classification. ` +
        `Read stage10.json first.`),
        { agentType: 'stock-analysis:quant-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s11` }),
      agentWithRetry(stagePrompt(12, 'risk-analyst', co,
        `Focus: scenario analysis (bull/base/bear), Marks 2nd-level thinking, Burry forensic, ` +
        `Klarman permanent-vs-temporary, kill switch definition (THESIS-falsifiable observation — NOT ` +
        `pipeline meta-state), correlation regime, credit spreads, narrative economics. ` +
        `Scripts: fetch_credit.py, fetch_behavioral.py, compute_correlation_regime.py. ` +
        `Read stage10.json first.`),
        { agentType: 'stock-analysis:risk-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s12` }),
    ])
    return { ...co, stages: { ...co.stages, 11: s11, 12: s12 } }
  },

  // ─────────────────────────── Wave 4 — A-share only ───────────────────────────
  // Stage 15 — depends on all prior. SKIP for non-.SH/.SZ tickers.
  async (co) => {
    if (!co.isAShare) {
      return { ...co, stages: { ...co.stages, 15: { stage: 15, status: 'skipped', notes: 'non A-share' } } }
    }
    const s15 = await agentWithRetry(stagePrompt(15, 'china-market-analyst', co,
      `Focus (MANDATORY for .SH/.SZ): 政策敏感性矩阵, 产业政策周期, 北向资金, 融资融券, 龙虎榜, 游资追踪. ` +
      `Read stage5-12 outputs first.`),
      { agentType: 'stock-analysis:china-market-analyst', schema: STAGE_RESULT_SCHEMA,
        phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s15` })
    return { ...co, stages: { ...co.stages, 15: s15 } }
  },
)))

// Pipeline returns one array per item; we passed [c] so each item is wrapped.
// Unwrap and roll up into the COMPANY_ORCHESTRATOR_RESULT shape downstream code expects.
const flattened = (companyResults || []).map(r => Array.isArray(r) ? r[0] : r).filter(Boolean)

const completedCompanies = flattened.map(co => {
  const stagesObj = co?.stages || {}
  const completed = Object.entries(stagesObj)
    .filter(([_, s]) => s && (s.status === 'ok' || s.status === 'partial' || s.status === 'skipped'))
    .map(([n]) => Number(n))
  const failed = Object.entries(stagesObj)
    .filter(([_, s]) => s && s.status === 'failed')
    .map(([n]) => Number(n))
  const required = co.isAShare ? [5,6,7,8,9,10,11,12,13,14,15] : [5,6,7,8,9,10,11,12,13,14]
  const missing = required.filter(n => !completed.includes(n))
  const status = missing.length === 0 && failed.length === 0 ? 'completed'
              : (completed.length >= required.length / 2) ? 'partial' : 'failed'
  return {
    ticker: co.ticker,
    rank: co.rank,
    status,
    stages_completed: completed,
    stages_failed: failed,
    company_dir: `${OUTPUT_DIR}/${co.rank}-${co.ticker}`,
    key_findings: Object.values(stagesObj)
      .map(s => s?.key_findings).filter(Boolean).slice(0, 5).join(' | '),
  }
})

const failedCount = watchlist.length - completedCompanies.filter(c => c.status !== 'failed').length
log(`[analysis] ${completedCompanies.filter(c => c.status === 'completed').length}/${watchlist.length} companies fully completed, ${completedCompanies.filter(c => c.status === 'partial').length} partial, ${failedCount} failed`)

// Update tracking for per-company analysis
const pcCompleted = completedCompanies.filter(c => c.status === 'completed').length
const pcPartial = completedCompanies.filter(c => c.status === 'partial').length
await trackPhaseEnd('Per-Company Analysis', {
  spawned: watchlist.length,
  succeeded: pcCompleted + pcPartial,
  failed_count: failedCount,
  summary: `${pcCompleted} completed, ${pcPartial} partial, ${failedCount} failed out of ${watchlist.length}`,
})
// Update per-company tracking
tracking.companies = completedCompanies.map(c => ({
  ticker: c.ticker,
  rank: c.rank,
  status: c.status,
  stages_completed: c.stages_completed || [],
  stages_failed: c.stages_failed || [],
  current_stage: null,
}))
await persistTracking()

if (completedCompanies.filter(c => c.status !== 'failed').length === 0) {
  tracking.status = 'failed'
  tracking.errors.push({ phase: 'Per-Company Analysis', agent_label: 'all', error: 'All company analyses failed', fatal: true })
  await persistTracking()
  return { status: 'failed', stage: 'per-company', reason: 'All company analyses failed — check {company_dir}/stage*.md for analyst-side errors' }
}

// -----------------------------------------------------------------------------
// PHASE 6 — Scoring & Cross-Check
// -----------------------------------------------------------------------------
phase('Scoring')
await trackPhaseStart('Scoring')
const companyDirs = completedCompanies.map(c => c.company_dir).filter(Boolean)
const scored = await agentWithRetry(
  `You are stock-analysis:scorer. Read all company outputs from these dirs: ` +
  `${JSON.stringify(companyDirs)}. Run 'uv run python ${PLUGIN_ROOT}/scripts/compute_scores.py' ` +
  `for each company — pass ALL available data flags: --metrics, --macro (shared), --technicals, ` +
  `--alternatives, --sentiment, --capital-structure, --liquidity, --short-interest, --activist, ` +
  `--options, --ecosystem, --trajectory, --credit, --correlation, --forecast, ` +
  `--earnings-edge, --health-index, --tam-adj-peg, --bayesian-growth, --cot, --seasonality. ` +
  `Omit any flag whose file does not exist. ` +
  `Run cross_check.py with --behavioral [company_dir]/behavioral.json for contradiction detection ` +
  `(incl. Rule 7: three-layer alignment stock×industry×macro). ` +
  `Run calibrate_conviction.py for Bayesian conviction calibration. Rank by composite score. ` +
  `Write ${OUTPUT_DIR}/ranking.json. mode=${MODE}.`,
  { agentType: 'stock-analysis:scorer', schema: SCORING_RESULT_SCHEMA, phase: 'Scoring', label: 'scorer' }
)

if (!scored?.companies?.length) {
  await trackPhaseEnd('Scoring', { spawned: 1, succeeded: 0, failed_count: 1, summary: 'failed — no ranked companies', failed: true })
  tracking.status = 'failed'
  tracking.errors.push({ phase: 'Scoring', agent_label: 'scorer', error: 'returned no ranked companies', fatal: true })
  await persistTracking()
  return { status: 'failed', stage: 16, reason: 'Scorer returned no ranked companies' }
}

// Stage 16.5 validation
const scoreValid = await agentWithRetry(
  `You are stock-analysis:report-validator. Validate scoring consistency for ${OUTPUT_DIR}/ranking.json. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate score-consistency ` +
  `--output-dir ${OUTPUT_DIR}'. Required: all 11 components present in 1-10 range, composite ` +
  `matches weighted sum, rating bracket consistent, no unresolved contradictions, ranking sorted.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Scoring', label: 'validate:scoring', effort: 'low' }
)
if (!scoreValid?.pass) {
  log(`[WARN] score validation: ${scoreValid?.reason}`)
}
tracking.validation_gates.scoring = scoreValid?.pass ?? false
await trackPhaseEnd('Scoring', { spawned: 2, succeeded: 2, failed_count: 0, summary: `${scored.companies.length} companies ranked` })
await persistTracking()

// -----------------------------------------------------------------------------
// PHASE 6b — Adversarial Verification (top-5 picks only)
//
// For each top pick, spawn 3 SKEPTICS, one per lens (fundamentals/macro/flow).
// Each skeptic is prompted to REFUTE the bull thesis; default-refuted on
// uncertainty. A pick "survives" only if ≥2 of 3 refute=false. Failed picks
// are flagged in the final result, NOT dropped — the user makes the call.
// Reference: research-report Pattern "Adversarial verify" + "Perspective-diverse verify".
// -----------------------------------------------------------------------------
phase('Adversarial Verify')
await trackPhaseStart('Adversarial Verify')
const TOP_FOR_VERIFY = Math.min(5, scored.companies.length)
const verifyTargets = scored.companies.slice(0, TOP_FOR_VERIFY)
const LENSES = [
  { key: 'fundamentals', focus: 'unit economics, working capital, accruals quality, capital allocation history, debt maturity, customer concentration' },
  { key: 'macro',        focus: 'interest-rate sensitivity, FX exposure, regulatory risk, geopolitical risk, end-market cyclicality, supply-chain choke risk' },
  { key: 'flow',         focus: 'institutional positioning, short interest, options skew, insider activity, sentiment regime, liquidity, factor exposure' },
]

const verifyResults = await parallel(verifyTargets.map(c => () =>
  parallel(LENSES.map(lens => () =>
    agentWithRetry(
      `You are an adversarial bear-case analyst. Try to REFUTE the bull thesis for ${c.ticker} ` +
      `(composite score ${c.composite_score}, conviction ${c.conviction}) through the ${lens.key.toUpperCase()} lens. ` +
      `Focus areas: ${lens.focus}. Read ${OUTPUT_DIR}/${c.rank}-${c.ticker}/stage*.md for evidence. ` +
      `Default to refuted=true if you are uncertain or evidence is mixed — Bayesian skeptic prior. ` +
      `Surface the single most damaging falsifiable signal (a measurable observation that would ` +
      `prove the thesis wrong). Return REFUTE_VERDICT per schema. Be terse — 1-3 sentences max in reason.`,
      {
        agentType: 'stock-analysis:risk-analyst',
        schema: REFUTE_VERDICT_SCHEMA,
        phase: 'Adversarial Verify',
        label: `refute:${c.rank}-${c.ticker}:${lens.key}`,
      }
    )
  )).then(votes => {
    const v = (votes || []).filter(Boolean)
    const refuted_count = v.filter(x => x.refuted).length
    return {
      rank: c.rank,
      ticker: c.ticker,
      composite_score: c.composite_score,
      conviction: c.conviction,
      survives: refuted_count < 2,                       // need ≥2 of 3 to NOT-refute
      refuted_count,
      verdicts: v,
      strongest_refutation: v.find(x => x.refuted)?.reason || null,
    }
  })
))

const flaggedPicks = (verifyResults || []).filter(Boolean).filter(r => !r.survives)
if (flaggedPicks.length) {
  log(`[WARN] adversarial verify flagged ${flaggedPicks.length}/${TOP_FOR_VERIFY}: ${flaggedPicks.map(p => p.ticker).join(', ')}`)
}

// Persist verify findings — equity-report-writer reads them to add a "Bear Case" section
await agentWithRetry(
  `You are stock-analysis:report-validator. Persist adversarial verification results to ` +
  `${OUTPUT_DIR}/verify_findings.json with this content: ${JSON.stringify(verifyResults || []).replace(/`/g,'\\`').slice(0, 4000)}. ` +
  `Just write the file and return {pass:true,reason:"persisted"} — no validation needed.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Adversarial Verify', label: 'persist:verify', effort: 'low' }
)
const verifyAgentsTotal = TOP_FOR_VERIFY * LENSES.length + 1  // skeptics + persist
await trackPhaseEnd('Adversarial Verify', { spawned: verifyAgentsTotal, succeeded: verifyAgentsTotal, failed_count: 0, summary: `${flaggedPicks.length}/${TOP_FOR_VERIFY} flagged` })
await persistTracking()

// -----------------------------------------------------------------------------
// PHASE 6c — Judge Panel (multi-framework cross-check on top picks)
//
// 4 independent value-framework lenses rate each top pick. Surfaces dimension
// disagreements that get washed out in the weighted composite. Synthesized into
// a single panel verdict (HIGH_CONSENSUS / MIXED / LOW_CONSENSUS) per company.
// Lenses: Buffett (moat+quality), Lynch (growth/PEG), Marks (cycle+pricing),
// Druckenmiller (macro+momentum).
// Reference: research-report Pattern "Judge panel".
// -----------------------------------------------------------------------------
phase('Judge Panel')
await trackPhaseStart('Judge Panel')
const FRAMEWORK_LENSES = [
  { lens: 'buffett',      focus: 'durable moat, ROIC vs WACC, reinvestment runway, owner earnings, capital allocation, predictability of FCF over 10y. Conservative on growth.' },
  { lens: 'lynch',        focus: 'category fit (slow grower, stalwart, fast grower, cyclical, turnaround, asset play), PEG, earnings growth durability, niche advantage, simplicity of business' },
  { lens: 'marks',        focus: 'second-level thinking: what is already priced in? cycle stage (boom/bust/recovery), implied vs realistic growth, asymmetric risk/reward, the price you pay relative to consensus' },
  { lens: 'druckenmiller', focus: 'macro fit (rates, liquidity, USD), momentum + relative strength, capital flows, factor tailwind/headwind, concentration risk, when to size up vs trim' },
]

const judgeResults = await parallel(verifyTargets.map(c => () =>
  parallel(FRAMEWORK_LENSES.map(L => () =>
    agentWithRetry(
      `You are an investment analyst applying the ${L.lens.toUpperCase()} framework strictly. ` +
      `Score ${c.ticker} on a 0-10 scale from this lens ONLY. ` +
      `Focus: ${L.focus}. Read ${OUTPUT_DIR}/${c.rank}-${c.ticker}/stage*.md and ${OUTPUT_DIR}/ranking.json. ` +
      `Do NOT defer to the composite score — the point of this lens is to disagree if the framework demands it. ` +
      `Return LENS_VERDICT per schema with: lens="${L.lens}", score (0-10), verdict (STRONG_BUY/BUY/HOLD/AVOID), ` +
      `1-2 sentence rationale, dimensions_matched (what this stock does well per ${L.lens}), ` +
      `dimensions_violated (what it does poorly per ${L.lens}).`,
      {
        agentType: 'stock-analysis:quant-analyst',
        schema: LENS_VERDICT_SCHEMA,
        phase: 'Judge Panel',
        label: `judge:${c.rank}-${c.ticker}:${L.lens}`,
      }
    )
  )).then(lensVerdicts => {
    const lv = (lensVerdicts || []).filter(Boolean)
    const verdictCounts = lv.reduce((acc, v) => { acc[v.verdict] = (acc[v.verdict] || 0) + 1; return acc }, {})
    const buyVotes = (verdictCounts.STRONG_BUY || 0) + (verdictCounts.BUY || 0)
    const avoidVotes = verdictCounts.AVOID || 0
    let consensus
    if (buyVotes >= 3 && avoidVotes === 0) consensus = 'HIGH_CONSENSUS_BUY'
    else if (avoidVotes >= 2) consensus = 'HIGH_CONSENSUS_AVOID'
    else if (buyVotes >= 2 && avoidVotes >= 1) consensus = 'MIXED'
    else consensus = 'LOW_CONSENSUS'
    const scores = lv.map(v => v.score)
    const score_mean = scores.length ? scores.reduce((a,b)=>a+b,0) / scores.length : 0
    const score_spread = scores.length ? Math.max(...scores) - Math.min(...scores) : 0
    return {
      rank: c.rank,
      ticker: c.ticker,
      consensus,
      score_mean,
      score_spread,                                    // wide spread = framework disagreement
      verdicts_by_lens: lv,
    }
  })
))

const disagreements = (judgeResults || []).filter(Boolean).filter(r => r.score_spread >= 3)
if (disagreements.length) {
  log(`[INFO] judge-panel disagreements (spread ≥3): ${disagreements.map(d => `${d.ticker}(±${d.score_spread.toFixed(1)})`).join(', ')}`)
}

// Persist judge findings
await agentWithRetry(
  `You are stock-analysis:report-validator. Persist judge-panel results to ` +
  `${OUTPUT_DIR}/judge_panel.json with this content: ${JSON.stringify(judgeResults || []).replace(/`/g,'\\`').slice(0, 8000)}. ` +
  `Just write the file and return {pass:true,reason:"persisted"} — no validation.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Judge Panel', label: 'persist:judge', effort: 'low' }
)
const judgeAgentsTotal = TOP_FOR_VERIFY * FRAMEWORK_LENSES.length + 1  // judges + persist
await trackPhaseEnd('Judge Panel', { spawned: judgeAgentsTotal, succeeded: judgeAgentsTotal, failed_count: 0, summary: `${disagreements.length} disagreements (spread≥3)` })
await persistTracking()

// -----------------------------------------------------------------------------
// PHASE 7 + 7b + 8 — Reports → Completeness Critic → Validation
//
// Gated iteration loop (cf. super-dev's _gatedLoop pattern). Each iteration:
//   1. Write/rewrite all 3-horizon reports per company (parallel fan-out).
//      On iter ≥ 2, prior-iteration critic + validator feedback is injected
//      as guidance so the writer can fix specific gaps and gate failures.
//   2. Run completeness critic over each report (parallel fan-out).
//   3. Run validate_report.py for the report-quality gate.
//   4. If critic shows NO FAIL verdicts AND validator passes → done.
//      Else if iter < maxIters → loop with feedback.
//      Else → exit with partial-quality flag.
//
// maxIters = 3 (same cap super-dev uses). Loop is BLOCKING: subsequent phases
// (Best Picks) only run after the loop exits.
// -----------------------------------------------------------------------------
const REPORT_MAX_ITERS = 3
let reportIter = 0
let priorCriticGaps = []
let priorReportValidErrors = []
let criticGaps = []
let reportValid = null

const reportTargets = scored.companies.flatMap(c =>
  ['long', 'mid', 'short'].map(horizon => ({ ...c, horizon }))
)

// Initialize report tracking entries
tracking.reports = reportTargets.map(t => ({
  ticker: t.ticker, horizon: t.horizon, status: 'pending', file_path: null, iteration: 0, validation_passed: null, critic_quality: null
}))
await trackPhaseStart('Reports')

while (reportIter < REPORT_MAX_ITERS) {
  reportIter += 1
  log(`[reports] writer → critic → validator — iteration ${reportIter}/${REPORT_MAX_ITERS}`)

  // Build per-target feedback string from previous iteration (empty on iter 1)
  const buildFeedback = (t) => {
    if (reportIter === 1) return ''
    const matchingCritic = priorCriticGaps.find(c => c?.ticker === t.ticker && c?.horizon === t.horizon)
    const gateFailures = priorReportValidErrors // global to this run, applies to all
    const lines = []
    if (matchingCritic?.gaps?.length) {
      lines.push(`PRIOR CRITIC FINDINGS (iteration ${reportIter - 1}) — fix every item:`)
      matchingCritic.gaps.forEach(g => {
        lines.push(`  - [${g.severity}] ${g.category}: ${g.description}${g.suggested_fix ? ` (fix: ${g.suggested_fix})` : ''}`)
      })
    }
    if (matchingCritic && matchingCritic.kill_switch_check?.falsifiable === false) {
      lines.push(`KILL SWITCH ISSUE (iteration ${reportIter - 1}): ${matchingCritic.kill_switch_check.issues?.join('; ') || 'not falsifiable'}. Rewrite kill switch to be measurable + clear trigger.`)
    }
    if (gateFailures.length) {
      lines.push(`PRIOR VALIDATOR GATE FAILURES (iteration ${reportIter - 1}):`)
      gateFailures.forEach(e => lines.push(`  - ${e}`))
    }
    return lines.length ? `\n\n--- FEEDBACK FROM PRIOR ITERATION ---\n${lines.join('\n')}\n--- END FEEDBACK ---\nAddress every item literally. Do not paraphrase the gate output.\n` : ''
  }

  // ---- Phase 7: Reports ----
  phase('Reports')
  const reportResults = await parallel(reportTargets.map(t => () =>
    agentWithRetry(
      `You are stock-analysis:equity-report-writer. Write ${t.horizon}-term equity research report ` +
      `for ${t.ticker} (rank ${t.rank}) in 中文 to ${OUTPUT_DIR}/${t.rank}-${t.ticker}/` +
      `${t.rank}-${t.ticker}_${t.horizon}_${RUN_ID}.md. Read all stage outputs from ` +
      `${OUTPUT_DIR}/${t.rank}-${t.ticker}/. ALSO read ${OUTPUT_DIR}/verify_findings.json (adversarial ` +
      `bear-case verdicts) and ${OUTPUT_DIR}/judge_panel.json (4-framework lens scores) — fold these ` +
      `into the report as dedicated "对手方观点 (Bear Case)" and "多框架交叉验证" sections. Include ` +
      `推荐标的排名, 当前股价, dimension breakdown table, methodology attribution, kill switch. ` +
      `Composite weights: see SKILL.md composite-weights.\n\n` +
      `After writing the report file, run validate_report.py and return a structured result per schema:\n` +
      `- ticker: "${t.ticker}"\n` +
      `- horizon: "${t.horizon}"\n` +
      `- status: "written" if report file saved successfully, "partial" if some sections missing, "failed" if unable to write\n` +
      `- file_path: the full path of the written .md file\n` +
      `- sections_written / sections_total: count of populated vs total template sections (24 max)\n` +
      `- missing_sections: list any section names you could not populate from available data\n` +
      `- conviction_score: the final composite score from scores.json\n` +
      `- rating: the mapped rating (Strong Buy / Buy / Hold / Sell / Strong Sell)\n` +
      `- kill_switch: the VERBATIM kill switch text you wrote in the report\n` +
      `- validation_passed: result of validate_report.py\n` +
      `- validation_errors: list of failing gates if any\n` +
      `- notes: any issues encountered` +
      buildFeedback(t),
      {
        agentType: 'stock-analysis:equity-report-writer',
        schema: REPORT_RESULT_SCHEMA,
        phase: 'Reports',
        label: `report:${t.rank}-${t.ticker}:${t.horizon}${reportIter > 1 ? `:r${reportIter}` : ''}`,
      }
    )
  ))

  // Log report outcomes — detect null returns (agent died on terminal API error)
  const reportSuccesses = (reportResults || []).filter(Boolean).filter(r => r.status === 'written' || r.status === 'partial')
  const reportFailures = (reportResults || []).filter(r => !r || r?.status === 'failed')
  if (reportFailures.length) {
    log(`[reports] ${reportFailures.length}/${reportTargets.length} report agents returned null/failed — will still run critic on available reports`)
  }
  if (reportSuccesses.length) {
    log(`[reports] ${reportSuccesses.length}/${reportTargets.length} reports written (${reportSuccesses.filter(r => r.status === 'partial').length} partial)`)
  }

  // ---- Phase 7b: Completeness Critic ----
  phase('Completeness Critic')
  const criticFindings = await parallel(reportTargets.map(t => () =>
    agentWithRetry(
      `You are a senior equity research editor reviewing the report at ` +
      `${OUTPUT_DIR}/${t.rank}-${t.ticker}/${t.rank}-${t.ticker}_${t.horizon}_${RUN_ID}.md. ` +
      `Find what's MISSING — be specific. Categories: (a) modality (a data source/analysis script ` +
      `that should have run but didn't), (b) claim (an assertion without a citation), (c) source ` +
      `(a citation that should exist but is absent or stale). For each gap, classify severity ` +
      `HIGH/MEDIUM/LOW and suggest a one-line fix. ` +
      `ALSO check the kill switch: extract the verbatim kill-switch text from the report. Is it ` +
      `(i) PRESENT, (ii) FALSIFIABLE (measurable observation + clear trigger)? Flag if the kill ` +
      `switch is vague ("if thesis breaks"), unmeasurable ("if sentiment turns"), or missing ` +
      `a quantitative threshold. Return CRITIC_FINDING per schema. Set overall_quality to FAIL if ` +
      `kill switch is missing OR ≥3 HIGH gaps; PASS_WITH_GAPS if 1-2 HIGH gaps; PASS otherwise. ` +
      `Persist findings to ${OUTPUT_DIR}/${t.rank}-${t.ticker}/critic_${t.horizon}.json.`,
      {
        agentType: 'stock-analysis:report-validator',
        schema: CRITIC_FINDING_SCHEMA,
        phase: 'Completeness Critic',
        label: `critic:${t.rank}-${t.ticker}:${t.horizon}${reportIter > 1 ? `:r${reportIter}` : ''}`,
      }
    )
  ))

  criticGaps = (criticFindings || []).filter(Boolean)
  const failedReports = criticGaps.filter(c => c.overall_quality === 'FAIL')

  // ---- Phase 8: validator-side report-quality gate ----
  phase('Validation')
  reportValid = await agentWithRetry(
    `You are stock-analysis:report-validator. Validate all generated reports at ${OUTPUT_DIR}. ` +
    `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate report-quality ` +
    `--output-dir ${OUTPUT_DIR}'. 8 gates: Chinese content, required sections, current price ` +
    `present, source attribution, framework divergence acknowledged, kill switch defined, ` +
    `methodology attribution, no hallucinated figures.`,
    { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: `validate:reports${reportIter > 1 ? `:r${reportIter}` : ''}`, effort: 'low' }
  )

  // Exit conditions
  if (reportValid?.pass && failedReports.length === 0) {
    log(`[reports] passed on iteration ${reportIter}/${REPORT_MAX_ITERS} (validator=pass, critic_failures=0)`)
    break
  }

  // Record feedback for next iteration
  priorCriticGaps = criticGaps
  priorReportValidErrors = reportValid?.gates_failed || (reportValid?.reason ? [reportValid.reason] : [])

  if (reportIter < REPORT_MAX_ITERS) {
    log(`[reports] iteration ${reportIter} fail — validator.pass=${reportValid?.pass}, critic.FAIL count=${failedReports.length}. Re-spawning writers with feedback.`)
  } else {
    log(`[reports] exhausted ${REPORT_MAX_ITERS} iterations — validator.pass=${reportValid?.pass}, critic.FAIL count=${failedReports.length}. Proceeding with partial quality.`)
  }
}

// Surface critic + kill-switch issues for the final result block
const failedReports = criticGaps.filter(c => c.overall_quality === 'FAIL')
const killSwitchIssues = criticGaps.filter(c => !c.kill_switch_check?.falsifiable)
if (failedReports.length) {
  log(`[WARN] completeness critic FAILED ${failedReports.length} reports after ${reportIter} iter(s): ${failedReports.map(c => `${c.ticker}:${c.horizon}`).join(', ')}`)
}
if (killSwitchIssues.length) {
  log(`[WARN] kill-switch falsifiability issues on ${killSwitchIssues.length} reports: ${killSwitchIssues.map(c => `${c.ticker}:${c.horizon}`).join(', ')}`)
}

// Update report tracking with final critic results
criticGaps.forEach(c => {
  const rt = tracking.reports.find(r => r.ticker === c?.ticker && r.horizon === c?.horizon)
  if (rt) rt.critic_quality = c.overall_quality
})
tracking.metrics.report_iterations = reportIter
tracking.validation_gates.reports = reportValid?.pass ?? false
await trackPhaseEnd('Reports', {
  spawned: reportTargets.length * reportIter,
  succeeded: reportTargets.length * reportIter - failedReports.length,
  failed_count: failedReports.length,
  summary: `${reportIter} iteration(s), ${failedReports.length} critic-FAILed`,
})
await trackPhaseEnd('Completeness Critic', { spawned: reportTargets.length * reportIter, succeeded: reportTargets.length * reportIter, failed_count: 0, summary: `${criticGaps.length} findings` })
await trackPhaseEnd('Validation', { spawned: reportIter, succeeded: reportIter, failed_count: 0, summary: reportValid?.pass ? 'passed' : `failed — ${reportValid?.reason}` })
await persistTracking()

// Persist critic summary (single write at the end of the loop, not per iter)
await agentWithRetry(
  `You are stock-analysis:report-validator. Persist completeness-critic summary to ` +
  `${OUTPUT_DIR}/critic_summary.json with this content: ${JSON.stringify(criticGaps).replace(/`/g,'\\`').slice(0, 8000)}. ` +
  `Also record iteration count: ${reportIter}. Just write the file and return {pass:true,reason:"persisted"} — no validation.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Completeness Critic', label: 'persist:critic', effort: 'low' }
)

if (!reportValid?.pass) {
  log(`[WARN] report validation still failing after ${reportIter} iter(s): ${reportValid?.reason}`)
}

// -----------------------------------------------------------------------------
// PHASE 8 — Best Picks Highlight
// -----------------------------------------------------------------------------
phase('Best Picks')
await trackPhaseStart('Best Picks')
const bestPicksResult = await agentWithRetry(
  `You are stock-analysis:equity-report-writer. Write HIGHLIGHTS_BEST_PICKS.md in 中文 to ` +
  `${OUTPUT_DIR}/HIGHLIGHTS_BEST_PICKS.md. Read ${OUTPUT_DIR}/ranking.json AND ` +
  `${OUTPUT_DIR}/verify_findings.json (adversarial bear-case verdicts) AND ` +
  `${OUTPUT_DIR}/judge_panel.json (multi-framework lens consensus) AND ` +
  `${OUTPUT_DIR}/critic_summary.json (completeness + kill-switch issues). ` +
  `Single-file summary of top-ranked companies: rank, ticker, name, 当前股价, composite_score, ` +
  `conviction, 2-sentence thesis, kill switch, key catalyst. ` +
  `ALSO add columns: 对手方验证 (bear_case_survives — ✅ if survived adversarial verify, ⚠️ if flagged), ` +
  `多框架共识 (panel_consensus — HIGH_CONSENSUS_BUY / MIXED / LOW_CONSENSUS / HIGH_CONSENSUS_AVOID). ` +
  `For any company where bear_case_survives=false OR panel_consensus contains AVOID, surface a ` +
  `⚠️ caution note with the strongest_refutation text. Ranked table format.\n\n` +
  `Return structured result: status="written" if file saved, companies_included=N, and boolean flags ` +
  `confirming required columns (bear_case, panel_consensus, kill_switch, current_price) are present.`,
  { agentType: 'stock-analysis:equity-report-writer', schema: BEST_PICKS_RESULT_SCHEMA, phase: 'Best Picks', label: 'best-picks' }
)

if (!bestPicksResult || bestPicksResult.status === 'failed') {
  log(`[WARN] Best Picks report writer returned null/failed — skipping validation`)
}

const bestPicksValid = await agentWithRetry(
  `You are stock-analysis:report-validator. Validate HIGHLIGHTS_BEST_PICKS.md at ${OUTPUT_DIR}. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate best-picks ` +
  `--output-dir ${OUTPUT_DIR}'. Required: ranked table with required columns, kill switch per ` +
  `company, 当前股价 present.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:best-picks', effort: 'low' }
)
tracking.validation_gates.best_picks = bestPicksValid?.pass ?? false
await trackPhaseEnd('Best Picks', { spawned: 2, succeeded: 2, failed_count: 0, summary: bestPicksValid?.pass ? 'passed' : `failed — ${bestPicksValid?.reason}` })

// Final tracking update
tracking.status = (reportValid?.pass && bestPicksValid?.pass && failedCount === 0 && failedReports.length === 0) ? 'completed' : 'partial'
tracking.completedAt = tracking.startedAt  // best-effort — workflow can't call Date.now()
await persistTracking()

// =============================================================================
// FINAL — compressed return value (the ONLY thing the team-lead context sees)
// =============================================================================
return {
  status: (reportValid?.pass && bestPicksValid?.pass && failedCount === 0 && failedReports.length === 0)
    ? 'completed'
    : 'partial',
  mode: MODE,
  run_id: RUN_ID,
  output_dir: OUTPUT_DIR,
  companies_analyzed: completedCompanies.length,
  companies_failed: failedCount,
  reports_generated: reportTargets.length,
  validation_gates: {
    data: dataValid?.pass,
    score: scoreValid?.pass,
    reports: reportValid?.pass,
    best_picks: bestPicksValid?.pass,
  },
  top_picks: scored.companies.slice(0, 5).map(c => {
    const v = (verifyResults || []).find(r => r?.ticker === c.ticker)
    const j = (judgeResults || []).find(r => r?.ticker === c.ticker)
    return {
      rank: c.rank,
      ticker: c.ticker,
      composite_score: c.composite_score,
      conviction: c.conviction,
      bear_case_survives: v?.survives ?? null,         // false = adversarial verify flagged it
      strongest_refutation: v?.strongest_refutation ?? null,
      panel_consensus: j?.consensus ?? null,           // HIGH_CONSENSUS_BUY | MIXED | LOW_CONSENSUS | HIGH_CONSENSUS_AVOID
      panel_score_spread: j?.score_spread ?? null,
    }
  }),
  quality_findings: {
    adversarial_flagged: flaggedPicks.map(p => ({
      ticker: p.ticker,
      refuted_count: p.refuted_count,
      strongest_refutation: p.strongest_refutation,
    })),
    judge_panel_disagreements: disagreements.map(d => ({
      ticker: d.ticker,
      consensus: d.consensus,
      score_spread: d.score_spread,
    })),
    failed_reports: failedReports.map(c => ({ ticker: c.ticker, horizon: c.horizon, gaps: c.gaps?.length || 0 })),
    kill_switch_issues: killSwitchIssues.map(c => ({
      ticker: c.ticker,
      horizon: c.horizon,
      issues: c.kill_switch_check?.issues || [],
    })),
  },
}
