'use client'

import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  sendChatMessage,
  fetchChatHistory,
  fetchStoredResearch,
} from '@/app/lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatPanelProps {
  ticker: string | null
  sessionId: string | null
}

export default function ChatPanel({ ticker, sessionId }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  // same query key as ReportPanel, so this reads the server-stored analysis
  const { data: analysis } = useQuery({
    queryKey: ['research', ticker],
    queryFn: () => fetchStoredResearch(ticker!),
    enabled: !!ticker,
    staleTime: Infinity,
    retry: false,
  })
  const hasAnalysis = !!analysis

  // reset messages and reload history when ticker changes
  useEffect(() => {
    setMessages([])
    setInput('')
    if (!sessionId) return
    let cancelled = false
    fetchChatHistory(sessionId)
      .then((history) => {
        if (!cancelled && history.length > 0) setMessages(history)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [sessionId])

  // scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || !sessionId || !hasAnalysis || loading) return

    const userMessage = input.trim()
    setInput('')
    // show clean message in UI without ticker prefix
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      // ticker prefix added server-side for agent context
      const res = await sendChatMessage(sessionId, userMessage, ticker ?? '')
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.response },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Something went wrong. Please try again.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <aside className="w-72 border-l border-[#1e1e1e] bg-[#0d0d0d] flex flex-col shrink-0">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-[#1e1e1e]">
        <div
          className={`w-1.5 h-1.5 rounded-full transition-colors ${
            hasAnalysis ? 'bg-[#5DCAA5]' : 'bg-[#555]'
          }`}
        />
        <span className="text-[12px] font-medium text-[#d8d8d8]">
          {ticker ? `Research chat · ${ticker}` : 'Research chat'}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-3">
        {!ticker && (
          <p className="text-[11px] text-[#444] text-center mt-4">
            Select a ticker to start chatting
          </p>
        )}

        {ticker && !hasAnalysis && messages.length === 0 && (
          <p className="text-[11px] text-[#444] text-center mt-4">
            Run analysis first to enable chat
          </p>
        )}

        {ticker && hasAnalysis && messages.length === 0 && !loading && (
          <p className="text-[11px] text-[#444] text-center mt-4">
            Ask anything about {ticker}
          </p>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex flex-col gap-1 max-w-[88%] ${
              msg.role === 'user' ? 'self-end' : 'self-start'
            }`}
          >
            <div
              className={`px-3 py-2 rounded-xl text-[11px] leading-relaxed break-words ${
                msg.role === 'user'
                  ? 'bg-[#0f6e56] text-[#c8edd5] rounded-br-sm'
                  : 'bg-[#161616] border border-[#2a2a2a] text-[#c8c8c8] rounded-bl-sm'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="self-start bg-[#161616] border border-[#2a2a2a] rounded-xl rounded-bl-sm px-3 py-2">
            <div className="flex items-center gap-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-1 h-1 rounded-full bg-[#555] animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[#1e1e1e] flex gap-2 items-center">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            !ticker
              ? 'Select a ticker first'
              : !hasAnalysis
                ? 'Run analysis to enable chat'
                : `Ask about ${ticker}…`
          }
          disabled={!ticker || !hasAnalysis || loading}
          className="flex-1 bg-[#141414] border border-[#2a2a2a] rounded-lg px-3 py-2 text-[11px] text-[#e8e8e8] placeholder:text-[#444] outline-none disabled:opacity-40"
        />
        <button
          onClick={handleSend}
          disabled={!ticker || !hasAnalysis || !input.trim() || loading}
          className="w-7 h-7 rounded-lg bg-[#0f6e56] hover:bg-[#1d9e75] disabled:opacity-40 flex items-center justify-center transition-colors shrink-0"
          aria-label="Send message"
        >
          <span className="text-[#5DCAA5] text-xs">↑</span>
        </button>
      </div>
    </aside>
  )
}
