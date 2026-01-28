import { Composition } from "remotion";
import { ChambaV34 } from "./ChambaV34";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ChambaV34"
    component={ChambaV34}
    durationInFrames={100 * 30} // 100 seconds at 30fps
    fps={30}
    width={1920}
    height={1080}
  />
);
