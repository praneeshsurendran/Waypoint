import { createContext, useContext } from 'react'

export interface RouteMetadata {
  path: string
  title: string
}
export const RouteMetadataContext = createContext<readonly RouteMetadata[]>([])
export const useRouteMetadata = () => useContext(RouteMetadataContext)
