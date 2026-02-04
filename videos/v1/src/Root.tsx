import { Composition } from "remotion";
import { EMVideo } from "./EMVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="EMVideo"
        component={EMVideo}
        durationInFrames={80 * 30} // 80 seconds at 30fps
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
