'use client'

import { useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchStoredResearch,
  runResearch,
  fetchPriceHistory,
  seedChat,
  buildAnalysisSeed,
  StockAnalysis,
} from '@/app/lib/api'
import { Skeleton } from '@/components/ui/skeleton'
import PriceChart from './PriceChart'

interface ReportPanelProps {
  ticker: string | null
  sessionId: string | null
}

export default function ReportPanel({ ticker, sessionId }: ReportPanelProps) {
  const queryClient = useQueryClient()

  // loads the stored analysis from the server; shared with ChatPanel's hasAnalysis
  const { data: analysis, isPending } = useQuery({
    queryKey: ['research', ticker],
    queryFn: () => fetchStoredResearch(ticker!),
    enabled: !!ticker,
    staleTime: Infinity,
    retry: false,
  })

  const {
    mutate: analyze,
    isPending: isAnalyzing,
    isError: analyzeFailed,
  } = useMutation({
    mutationFn: () => runResearch(ticker!),
    onSuccess: (fresh) => {
      queryClient.setQueryData(['research', ticker], fresh)
    },
  })

  const { data: priceHistory = [] } = useQuery({
    queryKey: ['price-history', ticker],
    queryFn: () => fetchPriceHistory(ticker!),
    enabled: !!analysis,
    staleTime: 1000 * 60 * 5,
  })

  // server ensures the seed is sent once per session
  useEffect(() => {
    if (!analysis || !sessionId || !ticker) return
    seedChat(sessionId, ticker, buildAnalysisSeed(analysis)).catch(() => {})
  }, [analysis, sessionId, ticker])

  if (!ticker) {
    return (
      <main className="flex-1 flex items-center justify-center bg-[#0f0f0f]">
        <p className="text-[#444] text-sm">Search a ticker and click Analyze</p>
      </main>
    )
  }

  return (
    <main className="flex-1 flex flex-col overflow-hidden bg-[#0f0f0f]">
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1e1e1e] shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#0a2d22] border border-[#0f6e56] flex items-center justify-center text-[11px] font-mono font-semibold text-[#5DCAA5]">
            {ticker.slice(0, 4)}
          </div>
          <div>
            <p className="text-[15px] font-medium text-[#e8e8e8] tracking-tight">
              {analysis?.company_name ?? ticker}
            </p>
            <p className="text-[11px] text-[#555]">
              {analysis
                ? `${analysis.sector} · ${analysis.industry}`
                : 'Click Analyze to load'}
            </p>
          </div>
        </div>
        <button
          onClick={() => analyze()}
          disabled={isAnalyzing}
          className="flex items-center gap-2 px-4 py-2 bg-[#0f6e56] hover:bg-[#1d9e75] disabled:opacity-50 text-[#5DCAA5] text-xs font-medium rounded-lg transition-colors"
        >
          <span className={isAnalyzing ? 'animate-spin' : ''}>↻</span>
          {isAnalyzing ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      {analyzeFailed && (
        <div className="mx-5 mt-3 px-3 py-2 bg-[#2d1515] border border-[#a32d2d] rounded-lg text-[#F09595] text-xs shrink-0">
          Failed to analyze {ticker}. Make sure the backend is running.
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {isAnalyzing || isPending ? (
          <LoadingSkeleton />
        ) : analysis ? (
          <AnalysisContent analysis={analysis} priceHistory={priceHistory} />
        ) : (
          <EmptyState ticker={ticker} onAnalyze={() => analyze()} />
        )}
      </div>
    </main>
  )
}

function EmptyState({
  ticker,
  onAnalyze,
}: {
  ticker: string
  onAnalyze: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 py-20">
      <div className="w-12 h-12 rounded-xl bg-[#0a2d22] border border-[#0f6e56] flex items-center justify-center text-lg font-mono font-semibold text-[#5DCAA5]">
        {ticker.slice(0, 2)}
      </div>
      <p className="text-[#555] text-sm">No analysis yet for {ticker}</p>
      <button
        onClick={onAnalyze}
        className="px-5 py-2 bg-[#0f6e56] hover:bg-[#1d9e75] text-[#5DCAA5] text-sm font-medium rounded-lg transition-colors"
      >
        Run analysis
      </button>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-2">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-16 bg-[#1a1a1a] rounded-lg" />
        ))}
      </div>
      <Skeleton className="h-28 bg-[#1a1a1a] rounded-lg" />
      <Skeleton className="h-24 bg-[#1a1a1a] rounded-lg" />
      <Skeleton className="h-24 bg-[#1a1a1a] rounded-lg" />
      <Skeleton className="h-32 bg-[#1a1a1a] rounded-lg" />
    </div>
  )
}

function AnalysisContent({
  analysis,
  priceHistory,
}: {
  analysis: StockAnalysis
  priceHistory: { date: string; close: number }[]
}) {
  const price = analysis.price_snapshot
  const fund = analysis.fundamentals

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-2">
        <MetricCard
          label="Price"
          value={`${price.currency === 'USD' ? '$' : ''}${price.current_price.toLocaleString()}`}
          change={price.day_change_pct}
          changeLabel="today"
        />
        <MetricCard
          label="Market cap"
          value={fund.market_cap}
          sub={`P/E ${fund.pe_ratio?.toFixed(1) ?? '—'}×`}
        />
        <MetricCard
          label="Revenue TTM"
          value={fund.revenue_ttm}
          sub="trailing 12mo"
        />
        <MetricCard
          label="Profit margin"
          value={`${((fund.profit_margin ?? 0) * 100).toFixed(1)}%`}
          sub="net margin"
        />
      </div>

      {priceHistory.length > 0 && <PriceChart data={priceHistory} />}

      <Section title="Business summary">
        <p className="text-[12px] text-[#999] leading-relaxed">
          {analysis.business_summary}
        </p>
      </Section>

      <Section title="Bull and bear case">
        <div className="flex flex-wrap gap-1.5">
          {analysis.bull_case?.map((item, i) => (
            <span
              key={i}
              className="text-[10px] px-2 py-1 rounded bg-[#0a2d22] text-[#5DCAA5] border border-[#0f6e56]"
            >
              {item}
            </span>
          ))}
          {analysis.bear_case?.map((item, i) => (
            <span
              key={i}
              className="text-[10px] px-2 py-1 rounded bg-[#2d1515] text-[#F09595] border border-[#a32d2d]"
            >
              {item}
            </span>
          ))}
        </div>
      </Section>

      <Section title="Recent news">
        <div className="space-y-2">
          {analysis.recent_news?.slice(0, 4).map((news, i) => (
            <div key={i} className="flex items-start gap-2">
              <div
                className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${
                  news.sentiment === 'positive'
                    ? 'bg-[#5DCAA5]'
                    : news.sentiment === 'negative'
                      ? 'bg-[#F09595]'
                      : 'bg-[#555]'
                }`}
              />
              <p className="text-[11px] text-[#888] leading-relaxed flex-1">
                {news.headline}
              </p>
              <span
                className={`text-[9px] px-1.5 py-0.5 rounded shrink-0 font-medium ${
                  news.sentiment === 'positive'
                    ? 'bg-[#0a2d22] text-[#5DCAA5]'
                    : news.sentiment === 'negative'
                      ? 'bg-[#2d1515] text-[#F09595]'
                      : 'bg-[#1e1e1e] text-[#666]'
                }`}
              >
                {news.sentiment}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Competitive position">
        <p className="text-[12px] text-[#999] leading-relaxed">
          {analysis.competitive_position}
        </p>
      </Section>

      <Section title="Key catalysts">
        <div className="space-y-1">
          {analysis.key_catalysts?.map((catalyst, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-[#5DCAA5] text-[10px] mt-0.5 shrink-0">
                →
              </span>
              <p className="text-[11px] text-[#888]">{catalyst}</p>
            </div>
          ))}
        </div>
      </Section>

      <div className="text-[10px] text-[#444] leading-relaxed pb-4">
        {analysis.disclaimer}
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
  change,
  changeLabel,
  sub,
}: {
  label: string
  value: string
  change?: number
  changeLabel?: string
  sub?: string
}) {
  return (
    <div className="bg-[#141414] rounded-lg p-3">
      <p className="text-[10px] text-[#555] uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className="text-[16px] font-medium text-[#e8e8e8] font-mono tracking-tight">
        {value}
      </p>
      {change !== undefined && (
        <p
          className={`text-[10px] mt-0.5 font-mono ${change >= 0 ? 'text-[#5DCAA5]' : 'text-[#F09595]'}`}
        >
          {change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}% {changeLabel}
        </p>
      )}
      {sub && <p className="text-[10px] text-[#555] mt-0.5">{sub}</p>}
    </div>
  )
}

function Section({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-[#141414] border border-[#1e1e1e] rounded-xl p-4">
      <p className="text-[10px] font-medium text-[#555] uppercase tracking-widest mb-3">
        {title}
      </p>
      {children}
    </div>
  )
}
