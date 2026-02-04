import { Composition } from "remotion";
import { EMV18 } from "./EMV18";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="EMV18"
    component={EMV18}
    durationInFrames={90 * 30} // 90 seconds at 30fps
    fps={30}
    width={1920}
    height={1080}
  />
);
