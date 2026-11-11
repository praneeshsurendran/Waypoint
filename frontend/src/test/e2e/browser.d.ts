export {}

declare global {
  interface Window {
    testGps?: { watches: number; clears: number }
  }
}
