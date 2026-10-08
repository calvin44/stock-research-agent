const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface StockAnalysis {
  ticker: string
  company_name: string
  sector: string
  industry: string
  exchange: string
  price_snapshot: {
    current_price: number
    currency: string
    day_change_pct: number
    week_52_high: number
    week_52_low: number
    avg_volume: number
  }
  fundamentals: {
    market_cap: string
    pe_ratio: number
    forward_pe: number
    revenue_ttm: string
    profit_margin: number
    debt_to_equity: number
    dividend_yield: number
    analyst_rating: string
  }
  recent_news: {
    headline: string
    summary: string
    sentiment: 'positive' | 'negative' | 'neutral'
    date: string
    source_url: string
  }[]
  business_summary: string
  competitive_position: string
  key_catalysts: string[]
  bull_case: string[]
  bear_case: string[]
  data_sources: string[]
  disclaimer: string
}

export interface DocumentRecord {
  doc_id: string
  filename: string
  company: string
  report_type: string
  fiscal_year: string
  status: 'pending' | 'processing' | 'indexed' | 'failed'
  total_chunks: number
  error: string
  created_at: string
  updated_at: string
}

export interface PriceHistory {
  date: string
  close: number
}

// frontend/app/lib/api.ts

export function buildAnalysisSeed(analysis: StockAnalysis): string {
  return `I've just completed a research analysis for ${analysis.ticker} (${analysis.company_name}).

Key findings:
- Price: ${analysis.price_snapshot.currency === 'USD' ? '$' : ''}${analysis.price_snapshot.current_price.toLocaleString()} (${analysis.price_snapshot.day_change_pct > 0 ? '+' : ''}${analysis.price_snapshot.day_change_pct}% today)
- Market cap: ${analysis.fundamentals.market_cap} | P/E: ${analysis.fundamentals.pe_ratio?.toFixed(1)}x
- Revenue TTM: ${analysis.fundamentals.revenue_ttm} | Margin: ${((analysis.fundamentals.profit_margin ?? 0) * 100).toFixed(1)}%
- Bull case: ${analysis.bull_case?.join(', ')}
- Bear case: ${analysis.bear_case?.join(', ')}
- Summary: ${analysis.business_summary}
- Competitive position: ${analysis.competitive_position}

The user can now ask follow-up questions about this analysis.`
}

// returns the stored analysis, or null if none has been run yet
export async function fetchStoredResearch(
  ticker: string,
): Promise<StockAnalysis | null> {
  const res = await fetch(`${API_URL}/research/${ticker}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Failed to fetch research for ${ticker}`)
  return res.json()
}

// runs fresh research and stores it on the server
export async function runResearch(ticker: string): Promise<StockAnalysis> {
  const res = await fetch(`${API_URL}/research/${ticker}`, { method: 'POST' })
  if (!res.ok) throw new Error(`Failed to run research for ${ticker}`)
  return res.json()
}

// sends the analysis seed once per session; server ignores repeats
export async function seedChat(
  sessionId: string,
  ticker: string,
  message: string,
): Promise<{ sent: boolean }> {
  const res = await fetch(`${API_URL}/chat/seed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, ticker, message }),
  })
  if (!res.ok) throw new Error('Failed to seed chat')
  return res.json()
}

export async function sendChatMessage(
  sessionId: string,
  message: string,
  ticker: string = '',
): Promise<{ session_id: string; response: string }> {
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, ticker }),
  })
  if (!res.ok) throw new Error('Failed to send message')
  return res.json()
}

export async function fetchDocuments(
  company: string,
): Promise<DocumentRecord[]> {
  const res = await fetch(`${API_URL}/reports/?company=${company}`)
  if (!res.ok) throw new Error('Failed to fetch documents')
  return res.json()
}

export async function fetchDocumentStatus(
  docId: string,
): Promise<DocumentRecord> {
  const res = await fetch(`${API_URL}/reports/${docId}/status`)
  if (!res.ok) throw new Error('Failed to fetch document status')
  return res.json()
}

export async function uploadDocument(
  file: File,
  company: string,
  reportType: string,
  fiscalYear: string,
): Promise<{ doc_id: string }> {
  const form = new FormData()
  form.append('file', file)
  form.append('company', company)
  form.append('report_type', reportType)
  form.append('fiscal_year', fiscalYear)
  const res = await fetch(`${API_URL}/reports/upload`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error('Failed to upload document')
  return res.json()
}

export async function fetchPriceHistory(
  ticker: string,
): Promise<PriceHistory[]> {
  const res = await fetch(`${API_URL}/price-history/${ticker}`)
  if (!res.ok) throw new Error('Failed to fetch price history')
  return res.json()
}

export async function fetchChatHistory(
  sessionId: string,
): Promise<{ role: 'user' | 'assistant'; content: string }[]> {
  const res = await fetch(`${API_URL}/chat/history/${sessionId}`)
  if (!res.ok) return []
  return res.json()
}

export async function deleteChatHistory(sessionId: string): Promise<void> {
  const res = await fetch(`${API_URL}/chat/history/${sessionId}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete chat history')
}

export async function deleteResearch(ticker: string): Promise<void> {
  const res = await fetch(`${API_URL}/research/${ticker}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Failed to delete analysis for ${ticker}`)
}
