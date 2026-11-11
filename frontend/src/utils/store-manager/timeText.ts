import { formatClock } from '@/utils/calendar'
import type { Order } from '@/types/models'
import { windowEnd } from '@/utils/store-manager/orderView'
import { formatTime12 } from '@/schemas/store-manager/windows'

/** A moment as 12-hour clock text: "5:41 AM". Stored times stay 24-hour. */
export const clock12 = (at: string) => formatTime12(formatClock(at))

/** A receiving window as 12-hour text: "5:30 AM – 7:30 AM". */
export const windowText12 = (order: Pick<Order, 'window' | 'windowEnd'>) =>
  `${formatTime12(order.window)} – ${formatTime12(windowEnd(order))}`
