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
  description: 'Unified equity research — screen GICS Level 4 → top-M companies → 11-stage deep-dive → scoring → 3-horizon reports',
  phases: [
    { title: 'Shared Data' },
    { title: 'Screening' },
    { title: 'Walk Chain' },
    { title: 'Per-Company Analysis' },
    { title: 'Scoring' },
    { title: 'Reports' },
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

// =============================================================================
// MAIN
// =============================================================================
const RUN_ID = args.run_id            // YYYYMMDDHHmm — set by team-lead before invocation
const PLUGIN_ROOT = args.plugin_root  // absolute path resolved from platform-paths
const MODE = args.mode                // pipeline | screen | analyze | compare | walk
const TOP_N = args.top_n              // sub-industries (pipeline/screen) or candidates (walk)
const TOTAL_M = args.total_m          // companies to deep-dive (pipeline only)
const TICKERS = args.tickers || []    // analyze/compare modes
const THEME = args.theme              // walk mode
const OUTPUT_DIR = `./reports/${RUN_ID}`

const validModes = ['pipeline', 'screen', 'analyze', 'compare', 'walk']
if (!validModes.includes(MODE)) {
  return { status: 'failed', stage: 0, reason: `Invalid mode: ${MODE}. Expected one of ${validModes.join(', ')}.` }
}

log(`[stock-analysis] mode=${MODE} run_id=${RUN_ID} top_n=${TOP_N} total_m=${TOTAL_M}`)
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
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Shared Data', label: 'validate:data' }
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
    `You are stock-analysis:roadmap-walker. Theme: "${THEME}". top_n=${TOP_N || 7}. ` +
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
  const topSubIndustries = allSubIndustries.slice(0, TOP_N || (MODE === 'screen' ? 30 : 5))

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
      `(${deepdive.companies?.length || 0} candidates). Apply price filter (US < $100, ` +
      `China A-shares < ¥100, all other markets < $100 USD equiv). Score growth/profitability/moat/` +
      `valuation/management/risk/liquidity. Write to ${OUTPUT_DIR}/stage4-${deepdive.code}.json.`,
      {
        agentType: 'stock-analysis:company-screener',
        schema: COMPANY_LIST_SCHEMA,
        phase: 'Screening',
        label: `screen:${deepdive.code}`,
      }
    )
  )

  // Flatten + rank top-M across ALL sub-industries (NOT quota per sub-industry)
  const allCompanies = (watchlist || [])
    .filter(Boolean)
    .flatMap(r => r.companies || [])
    .filter(c => c.price_filter_pass !== false)
    .sort((a, b) => b.score - a.score)
  watchlist = allCompanies.slice(0, TOTAL_M || 10).map((c, i) => ({
    ...c,
    rank: String(i + 1).padStart(3, '0'),
  }))

  log(`[screening] selected top ${watchlist.length} companies for deep-dive`)

  // Stage 4.5 validation
  const screenValid = await agent(
    `You are stock-analysis:report-validator. Validate screening completeness for ${OUTPUT_DIR}. ` +
    `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate screening-completeness ` +
    `--output-dir ${OUTPUT_DIR}'. Required: sub-industry leaderboard ≥10 entries with valid GICS ` +
    `codes, company watchlist ≥10 (or all if MODE=screen and top-n<10), price filter applied.`,
    { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Screening', label: 'validate:screening' }
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
// THE KEY WIN: each company-orchestrator runs 11 stages independently in its own
// context window. The per-stage raw data (financials, NLP, technicals) NEVER enters
// this workflow context — only the compressed completion summary returns.
// -----------------------------------------------------------------------------
phase('Per-Company Analysis')
const companyResults = await parallel(watchlist.map(c => () =>
  agent(
    `You are stock-analysis:company-orchestrator. Manage ALL stages 5-15 for ticker=${c.ticker}. ` +
    `company_rank=${c.rank} run_id=${RUN_ID} plugin_root=${PLUGIN_ROOT} ` +
    `company_dir=${OUTPUT_DIR}/${c.rank}-${c.ticker}/ shared_data_path=${OUTPUT_DIR}/stage1.json. ` +
    `is_a_share=${(c.ticker || '').match(/\.(SH|SZ)$/) ? 'true' : 'false'}. ` +
    `Execute dependency-aware waves: Wave1(5,7,9,13) → Wave2(6,8,10,14) → Wave3(11,12) → ` +
    `Wave4(15 if A-share). Resume from checkpoint files if present. Cap parallel analysts at 3 ` +
    `within your context. Return compressed COMPANY_ORCHESTRATOR_RESULT (status, stages_completed, ` +
    `stages_failed, key_findings, company_dir). NEVER return raw stage data.`,
    {
      agentType: 'stock-analysis:company-orchestrator',
      schema: COMPANY_ORCHESTRATOR_RESULT_SCHEMA,
      phase: 'Per-Company Analysis',
      label: `company:${c.rank}-${c.ticker}`,
    }
  )
))

const completedCompanies = companyResults.filter(Boolean)
const failedCount = watchlist.length - completedCompanies.length
log(`[analysis] ${completedCompanies.length}/${watchlist.length} companies completed analysis`)

if (completedCompanies.length === 0) {
  return { status: 'failed', stage: 'per-company', reason: 'All company-orchestrators failed' }
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
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Scoring', label: 'validate:scoring' }
)
if (!scoreValid?.pass) {
  log(`[WARN] score validation: ${scoreValid?.reason}`)
}

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
    `${OUTPUT_DIR}/${t.rank}-${t.ticker}/. Include 推荐标的排名, 当前股价, dimension breakdown ` +
    `table, methodology attribution, kill switch. Composite weights: see SKILL.md composite-weights.`,
    {
      agentType: 'stock-analysis:equity-report-writer',
      phase: 'Reports',
      label: `report:${t.rank}-${t.ticker}:${t.horizon}`,
    }
  )
))

// Stage 17.5 validation
phase('Validation')
const reportValid = await agent(
  `You are stock-analysis:report-validator. Validate all generated reports at ${OUTPUT_DIR}. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate report-quality ` +
  `--output-dir ${OUTPUT_DIR}'. 8 gates: Chinese content, required sections, current price ` +
  `present, source attribution, framework divergence acknowledged, kill switch defined, ` +
  `methodology attribution, no hallucinated figures.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:reports' }
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
  `${OUTPUT_DIR}/HIGHLIGHTS_BEST_PICKS.md. Read ${OUTPUT_DIR}/ranking.json. Single-file summary ` +
  `of top-ranked companies: rank, ticker, name, 当前股价, composite_score, conviction, ` +
  `2-sentence thesis, kill switch, key catalyst. Ranked table format.`,
  { agentType: 'stock-analysis:equity-report-writer', phase: 'Best Picks', label: 'best-picks' }
)

const bestPicksValid = await agent(
  `You are stock-analysis:report-validator. Validate HIGHLIGHTS_BEST_PICKS.md at ${OUTPUT_DIR}. ` +
  `Run 'uv run python ${PLUGIN_ROOT}/scripts/validate_report.py --gate best-picks ` +
  `--output-dir ${OUTPUT_DIR}'. Required: ranked table with required columns, kill switch per ` +
  `company, 当前股价 present.`,
  { agentType: 'stock-analysis:report-validator', schema: VALIDATION_SCHEMA, phase: 'Validation', label: 'validate:best-picks' }
)

// =============================================================================
// FINAL — compressed return value (the ONLY thing the team-lead context sees)
// =============================================================================
return {
  status: (reportValid?.pass && bestPicksValid?.pass && failedCount === 0) ? 'completed'
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
  top_picks: scored.companies.slice(0, 5).map(c => ({
    rank: c.rank,
    ticker: c.ticker,
    composite_score: c.composite_score,
    conviction: c.conviction,
  })),
}
