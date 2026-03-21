import { Composition } from "remotion";
import { EMPitch } from "./Pitch";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="EMPitch"
    component={EMPitch}
    durationInFrames={97 * 30}
    fps={30}
    width={1920}
    height={1080}
  />
);
