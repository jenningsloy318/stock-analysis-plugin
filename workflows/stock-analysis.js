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
  description: 'Unified equity research — screen GICS Level 4 → top-M companies → 11-stage deep-dive → scoring → adversarial verify → judge panel → 3-horizon reports → completeness critic',
  phases: [
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
        },
      },
    },
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

// =============================================================================
// MAIN
// =============================================================================
const RUN_ID = args.run_id            // YYYYMMDDHHmm — set by team-lead before invocation
const PLUGIN_ROOT = args.plugin_root  // absolute path resolved from platform-paths
const MODE = args.mode                // pipeline | screen | analyze | compare | walk
const TOP_INDUSTRY = args.top_industry  // sub-industries (pipeline/screen) or candidates (walk)
const TOTAL_COMPANY = args.total_company // companies to deep-dive (pipeline only)
const TICKERS = args.tickers || []    // analyze/compare modes
const THEME = args.theme              // walk mode
const UNIVERSE = args.universe || 'US' // 'US' | 'CN' | 'ALL' — listing-exchange filter for screening
const OUTPUT_DIR = `./reports/${RUN_ID}`

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

// -----------------------------------------------------------------------------
// PHASE 1 — Shared Data Collection (all modes)
// -----------------------------------------------------------------------------
phase('Shared Data')
const sharedData = await agent(
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
  return { status: 'failed', stage: 1, reason: 'Shared data collection failed', detail: sharedData?.notes }
}

// Stage 1.5 validation
const dataValid = await agent(
  `You are stock-analysis:report-validator. Validate shared data freshness for ${OUTPUT_DIR}. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate data-freshness ` +
  `--output-dir ${OUTPUT_DIR}'. Return {pass, reason, gates_failed} per schema.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Shared Data', label: 'validate:data', effort: 'low' }
)
if (!dataValid?.pass) {
  return { status: 'failed', stage: 1.5, reason: dataValid?.reason || 'Data validation failed' }
}

// -----------------------------------------------------------------------------
// PHASE 2 — Walk Mode (early branch, replaces screening + per-company)
// -----------------------------------------------------------------------------
if (MODE === 'walk') {
  phase('Walk Chain')
  const walkResult = await agent(
    `You are stock-analysis:roadmap-walker. Theme: "${THEME}". top_industry=${TOP_INDUSTRY || 7}. ` +
    `plugin_root=${PLUGIN_ROOT} output_dir=${OUTPUT_DIR} shared_data_path=${OUTPUT_DIR}/stage1.json. ` +
    `Perform top-down chain decomposition: anchor quantitative dated demand roadmap → ` +
    `reverse-walk finished-product→raw-substrate (≥5 layers) → score 4-element chokepoint ` +
    `checklist per layer → run score_bottleneck_asymmetry.py for each candidate → ` +
    `write walk_roadmap.json, walk_chain.json, walk_candidates.json, walk.md.`,
    { agentType: 'stock-analysis:roadmap-walker', schema: WALK_RESULT_SCHEMA, phase: 'Walk Chain', label: 'roadmap-walker' }
  )

  if (!walkResult) {
    return { status: 'failed', stage: 'walk', reason: 'roadmap-walker returned null' }
  }

  // Walk-mode reports (3 horizons not applicable — single walk report)
  phase('Reports')
  await agent(
    `You are stock-analysis:screening-report-writer. Write final walk report in 中文 ` +
    `to ${OUTPUT_DIR}/WALK_${THEME.replace(/\s+/g,'_')}_${RUN_ID}.md. Read walk_roadmap.json, ` +
    `walk_chain.json, walk_candidates.json. Include 当前股价 for each candidate.`,
    { agentType: 'stock-analysis:screening-report-writer', phase: 'Reports', label: 'walk-report' }
  )

  phase('Validation')
  const walkValid = await agent(
    `You are stock-analysis:report-validator. Validate walk report at ${OUTPUT_DIR}. ` +
    `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate report-quality ` +
    `--output-dir ${OUTPUT_DIR}'.`,
    { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:walk' }
  )
  return {
    status: walkValid?.pass ? 'completed' : 'partial',
    mode: 'walk',
    theme: THEME,
    candidates_found: walkResult.candidates?.length || 0,
    top_candidates: (walkResult.candidates || []).slice(0, 5),
    output_dir: OUTPUT_DIR,
  }
}

// -----------------------------------------------------------------------------
// PHASE 3 — Screening (pipeline + screen modes)
// -----------------------------------------------------------------------------
let watchlist = []
if (MODE === 'pipeline' || MODE === 'screen') {
  phase('Screening')

  // Stage 2: sector screener over 3 parallel batches of ~54 GICS Level 4 sub-industries
  const batches = ['0-54', '55-108', '109-163']
  const sectorBatchResults = await parallel(batches.map((range, i) => () =>
    agent(
      `You are stock-analysis:sector-screener. Process GICS Level 4 batch ${range} (i=${i}). ` +
      `Read shared data from ${OUTPUT_DIR}/stage1.json. Score 11 dimensions (Growth, Profitability, ` +
      `Valuation, Macro Fit, Innovation, Regulatory, Capital Flows, RS, Cyclicality, Constituent ` +
      `Quality, Supply/Demand). Write to ${OUTPUT_DIR}/stage2-batch-${i}.json.`,
      {
        agentType: 'stock-analysis:sector-screener',
        schema: SECTOR_SCORES_SCHEMA,
        phase: 'Screening',
        label: `sector:batch${i}`,
      }
    )
  ))

  // Aggregate top-N sub-industries from the 3 batches
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
    si => agent(
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
    deepdive => agent(
      `You are stock-analysis:company-screener. Screen companies in sub-industry ${deepdive.code} ` +
      `(${deepdive.companies?.length || 0} candidates). LISTING UNIVERSE: ${UNIVERSE} — ` +
      (UNIVERSE === 'US' ? `INCLUDE ONLY tickers listed on NYSE/NASDAQ (bare A-Z symbols, e.g. AAPL, BRK.B). ` +
        `EXCLUDE non-US listings: .T (Tokyo), .HK (Hong Kong), .SH/.SZ (China A-shares), .L (London), .TO (Toronto), .DE/.PA/.AS (Europe), .AX (Australia). ` :
       UNIVERSE === 'CN' ? `INCLUDE ONLY .SH and .SZ tickers (China A-shares). EXCLUDE all others. ` :
                            `Accept any listing exchange. `) +
      `Apply price filter (US < $100, China A-shares < ¥100, all other markets < $100 USD equiv). ` +
      `Score growth/profitability/moat/valuation/management/risk/liquidity. ` +
      `Write to ${OUTPUT_DIR}/stage4-${deepdive.code}.json.`,
      {
        agentType: 'stock-analysis:company-screener',
        schema: COMPANY_LIST_SCHEMA,
        phase: 'Screening',
        label: `screen:${deepdive.code}`,
      }
    )
  )

  // Flatten + rank top-M across ALL sub-industries (NOT quota per sub-industry).
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
  const screenValid = await agent(
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
  const horizons = ['long', 'mid', 'short']
  await parallel(horizons.map(h => () =>
    agent(
      `You are stock-analysis:screening-report-writer. Write ${h}-term screening report in 中文 ` +
      `to ${OUTPUT_DIR}/SCREEN_${h}_${RUN_ID}.md. Read stage2 sector scores + stage3 deep-dives + ` +
      `stage4 company watchlist. Include 推荐标的排名 (001, 002, ...) and 当前股价 for each company.`,
      { agentType: 'stock-analysis:screening-report-writer', phase: 'Reports', label: `report:screen:${h}` }
    )
  ))

  phase('Validation')
  const reportsValid = await agent(
    `You are stock-analysis:report-validator. Validate screening reports at ${OUTPUT_DIR}. ` +
    `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate report-quality ` +
    `--output-dir ${OUTPUT_DIR}'.`,
    { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:screen-reports' }
  )

  phase('Best Picks')
  await agent(
    `You are stock-analysis:equity-report-writer. Write HIGHLIGHTS_BEST_PICKS.md in 中文 to ` +
    `${OUTPUT_DIR}/HIGHLIGHTS_BEST_PICKS.md. Top 5 sub-industries with kill switch and 当前股价.`,
    { agentType: 'stock-analysis:equity-report-writer', phase: 'Best Picks', label: 'best-picks' }
  )

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
      agent(stagePrompt(5, 'fundamental-analyst', co,
        `Focus: financial health — DuPont 5-factor, Piotroski F-Score, Lynch category, key ratios. ` +
        `Scripts: fetch_financials.py, calculate_metrics.py.`),
        { agentType: 'stock-analysis:fundamental-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s5` }),
      agent(stagePrompt(7, 'industry-analyst', co,
        `Focus: Porter's Five Forces, TAM/SAM/SOM, moat assessment, BCG matrix, ecosystem mapping. ` +
        `REUSE industry thesis from ${OUTPUT_DIR}/stage3-*.json if present. Scripts: fetch_peer_universe.py.`),
        { agentType: 'stock-analysis:industry-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s7` }),
      agent(stagePrompt(9, 'macro-analyst', co,
        `Focus: Dalio economic cycle, Druckenmiller liquidity, Four-Box, Fed stance, CRP, FX exposure. ` +
        `REUSE macro data from ${sharedDataPath}. Scripts: fetch_global_macro.py, fetch_currency_exposure.py.`),
        { agentType: 'stock-analysis:macro-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s9` }),
      agent(stagePrompt(13, 'alt-data-analyst', co,
        `Focus: digital footprint (web traffic, app rankings), NLP earnings call analysis, channel checks, ` +
        `transaction data. Scripts: fetch_alternatives.py, fetch_news_nlp.py, calculate_candor.py, ` +
        `analyze_earnings_transcript.py.`),
        { agentType: 'stock-analysis:alt-data-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s13` }),
    ])
    return { ...co, isAShare, stages: { 5: s5, 7: s7, 9: s9, 13: s13 } }
  },

  // ─────────────────────────── Wave 2 ───────────────────────────
  // Stages 6 (←5), 8 (←7), 10 (←5+7), 14 (←13)
  async (co) => {
    const [s6, s8, s10, s14] = await Promise.all([
      agent(stagePrompt(6, 'fundamental-analyst', co,
        `Focus: earnings quality — Beneish M-Score, Montier C-Score, accruals quality, cash conversion, ` +
        `capital allocation (Buffett retention test, buyback ROI, M&A track record), CEO quality score. ` +
        `Scripts: fetch_capital_structure.py, calculate_earnings_quality.py, diff_filings.py, ` +
        `audit_capital_allocation.py, score_ceo_quality.py. Read ${OUTPUT_DIR}/${co.rank}-${co.ticker}/stage5.json first.`),
        { agentType: 'stock-analysis:fundamental-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s6` }),
      agent(stagePrompt(8, 'supply-chain-analyst', co,
        `Focus: Tier 1-3 supplier mapping, geographic concentration (HHI), chokepoint identification, ` +
        `disruption scenario modeling, inventory-to-sales analysis. Step 7b: bottleneck asymmetry composite. ` +
        `Scripts: fetch_supply_chain.py, score_bottleneck_asymmetry.py. ` +
        `Read ${OUTPUT_DIR}/${co.rank}-${co.ticker}/stage7.json first.`),
        { agentType: 'stock-analysis:supply-chain-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s8` }),
      agent(stagePrompt(10, 'quant-analyst', co,
        `Focus: valuation — DCF+Monte Carlo, comps, SOTP, LBO floor, reverse DCF, margin of safety. ` +
        `Optionally read ${OUTPUT_DIR}/${co.rank}-${co.ticker}/bottleneck_asymmetry.json from Stage 8 ` +
        `and fold tier/asymmetry-band into valuation as ±15% qualitative adjustment. ` +
        `Scripts: calculate_metrics.py, forecast.py, fetch_private_comps.py. ` +
        `Read stage5.json and stage7.json first.`),
        { agentType: 'stock-analysis:quant-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s10` }),
      agent(stagePrompt(14, 'catalyst-analyst', co,
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
      agent(stagePrompt(11, 'quant-analyst', co,
        `Focus: market regime — Weinstein stage, CANSLIM, Soros reflexivity, Fama-French 5-factor attribution, ` +
        `options signals (IV, max pain, put/call), sentiment, institutional positioning, short interest, ` +
        `activist exposure, liquidity (Amihud), seasonality. Scripts: fetch_technicals.py, compute_factors.py, ` +
        `fetch_cot.py, calculate_options.py, fetch_sentiment.py, fetch_short_interest.py, ` +
        `fetch_activist_exposure.py, compute_liquidity.py, compute_seasonality.py, compute_earnings_edge.py. ` +
        `Read stage10.json first.`),
        { agentType: 'stock-analysis:quant-analyst', schema: STAGE_RESULT_SCHEMA,
          phase: 'Per-Company Analysis', label: `${co.rank}-${co.ticker}:s11` }),
      agent(stagePrompt(12, 'risk-analyst', co,
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
    const s15 = await agent(stagePrompt(15, 'china-market-analyst', co,
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

if (completedCompanies.filter(c => c.status !== 'failed').length === 0) {
  return { status: 'failed', stage: 'per-company', reason: 'All company analyses failed — check {company_dir}/stage*.md for analyst-side errors' }
}

// -----------------------------------------------------------------------------
// PHASE 6 — Scoring & Cross-Check
// -----------------------------------------------------------------------------
phase('Scoring')
const companyDirs = completedCompanies.map(c => c.company_dir).filter(Boolean)
const scored = await agent(
  `You are stock-analysis:scorer. Read all company outputs from these dirs: ` +
  `${JSON.stringify(companyDirs)}. Run 'uv run python ${PLUGIN_ROOT}/scripts/compute_scores.py' ` +
  `for each. Run cross_check.py for contradictions. Run calibrate_conviction.py for Bayesian ` +
  `conviction calibration. Rank by composite score. Write ${OUTPUT_DIR}/ranking.json. ` +
  `mode=${MODE}.`,
  { agentType: 'stock-analysis:scorer', schema: SCORING_RESULT_SCHEMA, phase: 'Scoring', label: 'scorer' }
)

if (!scored?.companies?.length) {
  return { status: 'failed', stage: 16, reason: 'Scorer returned no ranked companies' }
}

// Stage 16.5 validation
const scoreValid = await agent(
  `You are stock-analysis:report-validator. Validate scoring consistency for ${OUTPUT_DIR}/ranking.json. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate score-consistency ` +
  `--output-dir ${OUTPUT_DIR}'. Required: all 11 components present in 1-10 range, composite ` +
  `matches weighted sum, rating bracket consistent, no unresolved contradictions, ranking sorted.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Scoring', label: 'validate:scoring', effort: 'low' }
)
if (!scoreValid?.pass) {
  log(`[WARN] score validation: ${scoreValid?.reason}`)
}

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
const TOP_FOR_VERIFY = Math.min(5, scored.companies.length)
const verifyTargets = scored.companies.slice(0, TOP_FOR_VERIFY)
const LENSES = [
  { key: 'fundamentals', focus: 'unit economics, working capital, accruals quality, capital allocation history, debt maturity, customer concentration' },
  { key: 'macro',        focus: 'interest-rate sensitivity, FX exposure, regulatory risk, geopolitical risk, end-market cyclicality, supply-chain choke risk' },
  { key: 'flow',         focus: 'institutional positioning, short interest, options skew, insider activity, sentiment regime, liquidity, factor exposure' },
]

const verifyResults = await parallel(verifyTargets.map(c => () =>
  parallel(LENSES.map(lens => () =>
    agent(
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
await agent(
  `You are stock-analysis:report-validator. Persist adversarial verification results to ` +
  `${OUTPUT_DIR}/verify_findings.json with this content: ${JSON.stringify(verifyResults || []).replace(/`/g,'\\`').slice(0, 4000)}. ` +
  `Just write the file and return {pass:true,reason:"persisted"} — no validation needed.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Adversarial Verify', label: 'persist:verify', effort: 'low' }
)

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
const FRAMEWORK_LENSES = [
  { lens: 'buffett',      focus: 'durable moat, ROIC vs WACC, reinvestment runway, owner earnings, capital allocation, predictability of FCF over 10y. Conservative on growth.' },
  { lens: 'lynch',        focus: 'category fit (slow grower, stalwart, fast grower, cyclical, turnaround, asset play), PEG, earnings growth durability, niche advantage, simplicity of business' },
  { lens: 'marks',        focus: 'second-level thinking: what is already priced in? cycle stage (boom/bust/recovery), implied vs realistic growth, asymmetric risk/reward, the price you pay relative to consensus' },
  { lens: 'druckenmiller', focus: 'macro fit (rates, liquidity, USD), momentum + relative strength, capital flows, factor tailwind/headwind, concentration risk, when to size up vs trim' },
]

const judgeResults = await parallel(verifyTargets.map(c => () =>
  parallel(FRAMEWORK_LENSES.map(L => () =>
    agent(
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
await agent(
  `You are stock-analysis:report-validator. Persist judge-panel results to ` +
  `${OUTPUT_DIR}/judge_panel.json with this content: ${JSON.stringify(judgeResults || []).replace(/`/g,'\\`').slice(0, 8000)}. ` +
  `Just write the file and return {pass:true,reason:"persisted"} — no validation.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Judge Panel', label: 'persist:judge', effort: 'low' }
)

// -----------------------------------------------------------------------------
// PHASE 7 — Reports (3 horizons × N companies)
// -----------------------------------------------------------------------------
phase('Reports')
const reportTargets = scored.companies.flatMap(c =>
  ['long', 'mid', 'short'].map(horizon => ({ ...c, horizon }))
)

await parallel(reportTargets.map(t => () =>
  agent(
    `You are stock-analysis:equity-report-writer. Write ${t.horizon}-term equity research report ` +
    `for ${t.ticker} (rank ${t.rank}) in 中文 to ${OUTPUT_DIR}/${t.rank}-${t.ticker}/` +
    `${t.rank}-${t.ticker}_${t.horizon}_${RUN_ID}.md. Read all stage outputs from ` +
    `${OUTPUT_DIR}/${t.rank}-${t.ticker}/. ALSO read ${OUTPUT_DIR}/verify_findings.json (adversarial ` +
    `bear-case verdicts) and ${OUTPUT_DIR}/judge_panel.json (4-framework lens scores) — fold these ` +
    `into the report as dedicated "对手方观点 (Bear Case)" and "多框架交叉验证" sections. Include ` +
    `推荐标的排名, 当前股价, dimension breakdown table, methodology attribution, kill switch. ` +
    `Composite weights: see SKILL.md composite-weights.`,
    {
      agentType: 'stock-analysis:equity-report-writer',
      phase: 'Reports',
      label: `report:${t.rank}-${t.ticker}:${t.horizon}`,
    }
  )
))

// -----------------------------------------------------------------------------
// PHASE 7b — Completeness Critic + Kill-Switch Falsifiability Check
//
// One critic per report (3 horizons × N companies). Reads the report and asks:
//  1. What's missing? (modality not run, claim unverified, framework not applied)
//  2. Is the kill switch falsifiable? (measurable + clear trigger)
// Findings persisted to {company_dir}/critic_{horizon}.json — the validator and
// best-picks writer read them. HIGH-severity gaps surface in final result.
// Reference: research-report Pattern "Completeness critic" + "Kill-switch sanity".
// -----------------------------------------------------------------------------
phase('Completeness Critic')
const criticFindings = await parallel(reportTargets.map(t => () =>
  agent(
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
      label: `critic:${t.rank}-${t.ticker}:${t.horizon}`,
    }
  )
))

const criticGaps = (criticFindings || []).filter(Boolean)
const failedReports = criticGaps.filter(c => c.overall_quality === 'FAIL')
const killSwitchIssues = criticGaps.filter(c => !c.kill_switch_check?.falsifiable)
if (failedReports.length) {
  log(`[WARN] completeness critic failed ${failedReports.length} reports: ${failedReports.map(c => `${c.ticker}:${c.horizon}`).join(', ')}`)
}
if (killSwitchIssues.length) {
  log(`[WARN] kill-switch falsifiability issues on ${killSwitchIssues.length} reports: ${killSwitchIssues.map(c => `${c.ticker}:${c.horizon}`).join(', ')}`)
}

// Persist critic summary
await agent(
  `You are stock-analysis:report-validator. Persist completeness-critic summary to ` +
  `${OUTPUT_DIR}/critic_summary.json with this content: ${JSON.stringify(criticGaps).replace(/`/g,'\\`').slice(0, 8000)}. ` +
  `Just write the file and return {pass:true,reason:"persisted"} — no validation.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Completeness Critic', label: 'persist:critic', effort: 'low' }
)

phase('Validation')

// Stage 17.5 validation
const reportValid = await agent(
  `You are stock-analysis:report-validator. Validate all generated reports at ${OUTPUT_DIR}. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate report-quality ` +
  `--output-dir ${OUTPUT_DIR}'. 8 gates: Chinese content, required sections, current price ` +
  `present, source attribution, framework divergence acknowledged, kill switch defined, ` +
  `methodology attribution, no hallucinated figures.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:reports', effort: 'low' }
)
if (!reportValid?.pass) {
  log(`[WARN] report validation failed: ${reportValid?.reason}`)
}

// -----------------------------------------------------------------------------
// PHASE 8 — Best Picks Highlight
// -----------------------------------------------------------------------------
phase('Best Picks')
await agent(
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
  `⚠️ caution note with the strongest_refutation text. Ranked table format.`,
  { agentType: 'stock-analysis:equity-report-writer', phase: 'Best Picks', label: 'best-picks' }
)

const bestPicksValid = await agent(
  `You are stock-analysis:report-validator. Validate HIGHLIGHTS_BEST_PICKS.md at ${OUTPUT_DIR}. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate best-picks ` +
  `--output-dir ${OUTPUT_DIR}'. Required: ranked table with required columns, kill switch per ` +
  `company, 当前股价 present.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:best-picks', effort: 'low' }
)

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
