import { Composition } from "remotion";
import { OWSDemo } from "./OWSDemo";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="OWSDemo"
    component={OWSDemo}
    durationInFrames={75 * 30} // 75 seconds at 30fps
    fps={30}
    width={1920}
    height={1080}
  />
);
