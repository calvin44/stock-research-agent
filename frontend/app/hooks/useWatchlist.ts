'use client'

import { useState, useEffect, useRef } from 'react'
import { WatchlistItem } from '@/app/types'
import { deleteChatHistory } from '@/app/lib/api'

const STORAGE_KEY = 'alphaview_watchlist'

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [hydrated, setHydrated] = useState(false)
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true
    const stored = localStorage.getItem(STORAGE_KEY)
    const initial = stored ? JSON.parse(stored) : []
    setWatchlist(initial)
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
    const item = watchlist.find((w) => w.ticker === ticker)
    if (item) {
      deleteChatHistory(item.sessionId)
    }
    save(watchlist.filter((w) => w.ticker !== ticker))
  }

  const getSession = (ticker: string): string | null => {
    return watchlist.find((w) => w.ticker === ticker)?.sessionId ?? null
  }

  return { watchlist, hydrated, addTicker, removeTicker, getSession }
}
