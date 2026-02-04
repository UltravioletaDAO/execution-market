import { Composition } from "remotion";
import { EMV34 } from "./EMV34";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="EMV34"
    component={EMV34}
    durationInFrames={100 * 30} // 100 seconds at 30fps
    fps={30}
    width={1920}
    height={1080}
  />
);
