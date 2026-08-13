export type GestureName =
  | "none"
  | "open_palm"
  | "fist"
  | "pinch"
  | "point"
  | "thumbs_up"
  | "thumbs_down"
  | "two_fingers"
  | "swipe_left"
  | "swipe_right";

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
