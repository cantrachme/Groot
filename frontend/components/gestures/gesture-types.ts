export type GestureName =
  | "none"
  | "open_palm"
  | "fist"
  | "pinch";

export interface GestureState {
  enabled: boolean;
  gesture: GestureName;
  handX: number;
  handY: number;
  pinchDistance: number;
  pinchActive: boolean;
  rotationX: number;
  rotationY: number;
  zoomDelta: number;
  rotationActive: boolean;
  lastUpdate: number;
}
