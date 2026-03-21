import { Composition } from "remotion";
import { EMPitchEN } from "./Pitch";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="EMPitchEN"
    component={EMPitchEN}
    durationInFrames={107 * 30}
    fps={30}
    width={1920}
    height={1080}
  />
);
