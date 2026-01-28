import { Composition } from "remotion";
import { ChambaV18 } from "./ChambaV18";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ChambaV18"
    component={ChambaV18}
    durationInFrames={90 * 30} // 90 seconds at 30fps
    fps={30}
    width={1920}
    height={1080}
  />
);
