// Entry point for the opening styles (separate from the project's own Root):
//   npx remotion render src/opening/index.tsx Opening out.mp4 --props=/abs/path/props.json
//   npx remotion still  src/opening/index.tsx Opening out.png --frame=N --props=...
import React from "react";
import { Composition, registerRoot } from "remotion";
import { FPS, H, Opening, OpeningProps, W, openingDefaults } from "./Opening";

const Root: React.FC = () => (
  <Composition
    id="Opening"
    component={Opening as unknown as React.FC<Record<string, unknown>>}
    fps={FPS}
    width={W}
    height={H}
    durationInFrames={150}
    defaultProps={openingDefaults as unknown as Record<string, unknown>}
    calculateMetadata={({ props }) => ({
      durationInFrames: Math.max(1, Math.round(((props as unknown as OpeningProps).durationSec ?? 5) * FPS)),
    })}
  />
);

registerRoot(Root);
