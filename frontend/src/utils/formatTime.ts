export const formatTime = (date: string) =>
  new Date(date).toLocaleTimeString('en-LK', { hour: '2-digit', minute: '2-digit' })
