import { Composition } from "remotion";
import { ChambaVideo } from "./ChambaVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ChambaVideo"
        component={ChambaVideo}
        durationInFrames={80 * 30} // 80 seconds at 30fps
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
