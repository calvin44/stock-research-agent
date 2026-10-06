export interface WatchlistItem {
  ticker: string
  sessionId: string
}

export interface AppState {
  watchlist: WatchlistItem[]
  selectedTicker: string | null
}
