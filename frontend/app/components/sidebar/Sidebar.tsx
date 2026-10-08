'use client'

import { useState, useRef } from 'react'
import { WatchlistItem } from '@/app/types'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

interface SidebarProps {
  watchlist: WatchlistItem[]
  hydrated: boolean
  selectedTicker: string | null
  onAddTicker: (ticker: string) => void
  onSelectTicker: (ticker: string) => void
  onRemoveTicker: (ticker: string) => Promise<void>
}

export default function Sidebar({
  watchlist,
  hydrated,
  selectedTicker,
  onAddTicker,
  onSelectTicker,
  onRemoveTicker,
}: SidebarProps) {
  const [query, setQuery] = useState('')
  const [pendingDelete, setPendingDelete] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const confirmDelete = async (e: React.MouseEvent) => {
    if (!pendingDelete) return
    // keep the dialog open until the server finishes
    e.preventDefault()
    setDeleting(true)
    setDeleteError('')
    try {
      await onRemoveTicker(pendingDelete)
      setPendingDelete(null)
    } catch {
      setDeleteError(`Could not delete ${pendingDelete}. Try again.`)
    } finally {
      setDeleting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && query.trim()) {
      onAddTicker(query.trim())
      onSelectTicker(query.trim().toUpperCase())
      setQuery('')
    }
  }

  return (
    <aside className="w-52 flex flex-col border-r border-[#1e1e1e] bg-[#0d0d0d] shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-4 border-b border-[#1e1e1e]">
        <div className="w-6 h-6 rounded-md bg-[#0f6e56] flex items-center justify-center">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <polyline
              points="1,9 4,5 7,7 11,2"
              stroke="#5DCAA5"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <span className="text-sm font-medium text-[#e8e8e8] tracking-tight">
          Alphaview
        </span>
      </div>

      {/* Search */}
      <div className="px-3 pt-3 pb-2">
        <Input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          onKeyDown={handleKeyDown}
          placeholder="Search ticker…"
          className="bg-[#161616] border-[#2a2a2a] text-[#e8e8e8] placeholder:text-[#444] text-xs h-8"
        />
        {query && (
          <div className="mt-1 bg-[#161616] border border-[#2a2a2a] rounded-lg overflow-hidden">
            <div
              className="px-3 py-2 text-xs text-[#888] cursor-pointer hover:bg-[#1e1e1e]"
              onClick={() => {
                onAddTicker(query)
                onSelectTicker(query.toUpperCase())
                setQuery('')
              }}
            >
              <span className="text-[#5DCAA5] font-mono font-medium">
                {query}
              </span>
              <span className="ml-2 text-[#555]">— press Enter to add</span>
            </div>
          </div>
        )}
      </div>

      {/* Watchlist */}
      <div className="flex-1 overflow-y-auto px-3 flex flex-col gap-1">
        {!hydrated ? null : watchlist.length === 0 ? (
          <p className="text-[11px] text-[#444] px-1 py-2">
            Search a ticker to get started
          </p>
        ) : (
          watchlist.map((item) => (
            <div
              key={item.ticker}
              onClick={() => onSelectTicker(item.ticker)}
              className={`flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer group transition-colors ${
                selectedTicker === item.ticker
                  ? 'bg-[#161616] border border-[#1e1e1e]'
                  : 'hover:bg-[#111]'
              }`}
            >
              <div className="w-7 h-7 rounded-md bg-[#0a2d22] border border-[#0f6e56] flex items-center justify-center text-[9px] font-mono font-semibold text-[#5DCAA5] shrink-0">
                {item.ticker.slice(0, 4)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[12px] font-medium text-[#d8d8d8] truncate">
                  {item.ticker}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setDeleteError('')
                  setPendingDelete(item.ticker)
                }}
                className="opacity-0 group-hover:opacity-100 text-[#555] hover:text-[#888] text-xs transition-opacity"
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>

      <AlertDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open && !deleting) setPendingDelete(null)
        }}
      >
        <AlertDialogContent className="bg-[#0d0d0d] border-[#2a2a2a] text-[#e8e8e8]">
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {pendingDelete}?</AlertDialogTitle>
            <AlertDialogDescription className="text-[#888]">
              This deletes the chat history and saved analysis for{' '}
              {pendingDelete}. Adding it back will require running Analyze
              again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {deleteError && (
            <p className="text-xs text-[#F09595]">{deleteError}</p>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel
              disabled={deleting}
              className="bg-transparent border-[#2a2a2a] text-[#888] hover:bg-[#1e1e1e] hover:text-[#e8e8e8]"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleting}
              className="bg-[#a32d2d] hover:bg-[#c03a3a] text-white"
            >
              {deleting ? 'Removing…' : 'Remove'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Upload button */}
      <div className="px-3 py-3 border-t border-[#1e1e1e]">
        <button className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-dashed border-[#2a2a2a] text-[#555] text-xs hover:bg-[#111] hover:text-[#888] transition-colors">
          <span>↑</span>
          Upload report
        </button>
      </div>
    </aside>
  )
}
