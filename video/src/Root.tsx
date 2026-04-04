import { Composition } from 'remotion';
import { WalkthroughVideo, getWalkthroughDuration } from './WalkthroughVideo';
import { useLoadFonts } from './styles/fonts';

const WALKTHROUGH_FRAMES = getWalkthroughDuration();

export const RemotionRoot: React.FC = () => {
  useLoadFonts();
  return (
    <>
      <Composition
        id="MCPMemoryWalkthrough"
        component={WalkthroughVideo}
        durationInFrames={WALKTHROUGH_FRAMES}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{}}
      />
    </>
  );
};
