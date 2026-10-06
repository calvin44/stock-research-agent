'use client'

import { useState } from 'react'
import { useWatchlist } from '@/app/hooks/useWatchlist'
import Sidebar from '@/app/components/sidebar/Sidebar'
import ReportPanel from '@/app/components/report/ReportPanel'
import ChatPanel from '@/app/components/chat/ChatPanel'

export default function Home() {
  const { watchlist, hydrated, addTicker, removeTicker, getSession } =
    useWatchlist()
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)

  const handleSelectTicker = (ticker: string) => {
    setSelectedTicker(ticker)
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        watchlist={watchlist}
        hydrated={hydrated}
        selectedTicker={selectedTicker}
        onAddTicker={addTicker}
        onSelectTicker={handleSelectTicker}
        onRemoveTicker={removeTicker}
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
