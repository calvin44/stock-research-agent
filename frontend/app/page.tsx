'use client'

import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useWatchlist } from '@/app/hooks/useWatchlist'
import Sidebar from '@/app/components/sidebar/Sidebar'
import ReportPanel from '@/app/components/report/ReportPanel'
import ChatPanel from '@/app/components/chat/ChatPanel'

export default function Home() {
  const { watchlist, hydrated, addTicker, removeTicker, getSession } =
    useWatchlist()
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const handleSelectTicker = (ticker: string) => {
    setSelectedTicker(ticker)
  }

  const handleRemoveTicker = async (ticker: string) => {
    await removeTicker(ticker)
    queryClient.removeQueries({ queryKey: ['research', ticker] })
    queryClient.removeQueries({ queryKey: ['price-history', ticker] })
    if (selectedTicker === ticker) setSelectedTicker(null)
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        watchlist={watchlist}
        hydrated={hydrated}
        selectedTicker={selectedTicker}
        onAddTicker={addTicker}
        onSelectTicker={handleSelectTicker}
        onRemoveTicker={handleRemoveTicker}
      />
      <ReportPanel
        ticker={selectedTicker}
        sessionId={selectedTicker ? getSession(selectedTicker) : null}
      />
      <ChatPanel
        key={selectedTicker}
        ticker={selectedTicker}
        sessionId={selectedTicker ? getSession(selectedTicker) : null}
      />
    </div>
  )
}
