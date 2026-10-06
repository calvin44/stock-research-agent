'use client'

import { useState, useEffect } from 'react'
import { WatchlistItem } from '@/app/types'

const STORAGE_KEY = 'alphaview_watchlist'

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) setWatchlist(JSON.parse(stored))
    setHydrated(true)
  }, [])

  const save = (items: WatchlistItem[]) => {
    setWatchlist(items)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  }

  const addTicker = (ticker: string) => {
    const upper = ticker.toUpperCase()
    if (watchlist.find((w) => w.ticker === upper)) return
    const item: WatchlistItem = {
      ticker: upper,
      sessionId: crypto.randomUUID(),
    }
    save([...watchlist, item])
  }

  const removeTicker = (ticker: string) => {
    save(watchlist.filter((w) => w.ticker !== ticker))
    localStorage.removeItem(`analysis_${ticker}`)
  }

  const getSession = (ticker: string): string | null => {
    return watchlist.find((w) => w.ticker === ticker)?.sessionId ?? null
  }

  return { watchlist, hydrated, addTicker, removeTicker, getSession }
}
