// Shared API types. Only the fields this app uses are modeled; the EEN API
// returns more. See Open API Specifications/{devices,grouping}_category.yaml.

export interface Coord {
  latitude: number
  longitude: number
}

export interface FloorPlan {
  id: string
  floorId: string
  type: 'png' | 'svg' | 'pdf'
  creator?: string
}

export interface Floor {
  id: string
  name: string
  floorLevel: number
  topLeftCoordinates: Coord
  bottomRightCoordinates: Coord
  floorPlans?: FloorPlan[]
}

export interface DevicePosition {
  latitude: number | null
  longitude: number | null
  azimuth: number | null
  floor: number | null
  rangeInMeters: number | null
  fieldOfView: number | null
}

export type ConnectionStatus =
  | 'online'
  | 'deviceOffline'
  | 'invalidCredentials'
  | 'bridgeOffline'
  | 'off'
  | 'error'
  | 'unknown'

export interface DeviceStatus {
  connectionStatus?: ConnectionStatus
}

export interface Camera {
  id: string
  name: string
  accountId?: string
  bridgeId?: string
  locationId?: string
  devicePosition?: DevicePosition
  status?: DeviceStatus
}

export interface Location {
  id: string
  name: string
}

export interface Paginated<T> {
  results: T[]
  nextPageToken: string
  prevPageToken: string
  totalSize: number
}
