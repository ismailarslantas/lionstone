import React from "react";
import { useVideoConfig } from "remotion";
import { Frame, centered } from "../lib/Frame";
import type { EffectProps } from "../lib/schema";
import { theatreState, useTheatreSequence } from "../lib/theatre";

const GOLD = "#E8A33D";

/**
 * Keyframed title driven by a Theatre.js sequence: the word drops in with an overshoot,
 * its tracking tightens, a gold rule draws under it, then everything lifts away.
 * Edit the keyframes below (seconds), or paste a state exported from Theatre Studio.
 */
export const TheatreKeyframedTitle: React.FC<EffectProps> = (p) => {
  const { height } = useVideoConfig();
  const a = p.enter;
  const b = p.enter + p.hold;
  const z = b + p.exit;
  const v = useTheatreSequence({
    // one project per timing, because a Theatre project's state is fixed once created
    project: `LionstoneTheatreTitle-${a}-${p.hold}-${p.exit}`,
    sheet: "Title",
    object: "Word",
    props: { y: 0, opacity: 1, tracking: 0, rule: 1, sub: 1 },
    state: theatreState("Title", "Word", {
      y: [{ at: 0, value: -0.12 }, { at: a * 0.7, value: 0.012 }, { at: a, value: 0 },
          { at: b, value: 0 }, { at: z, value: -0.05 }],
      opacity: [{ at: 0, value: 0 }, { at: a * 0.4, value: 1 }, { at: b, value: 1 },
                { at: z, value: 0 }],
      tracking: [{ at: 0, value: 0.4 }, { at: a, value: 0.04 }, { at: b, value: 0.02 },
                 { at: z, value: 0.12 }],
      rule: [{ at: a * 0.5, value: 0 }, { at: a * 1.3, value: 1 }, { at: b, value: 1 },
             { at: z, value: 0 }],
      sub: [{ at: a * 0.8, value: 0 }, { at: a * 1.4, value: 1 }, { at: b, value: 1 },
            { at: z - p.exit * 0.4, value: 0 }],
    }, z),
  });
  return (
    <Frame p={p}>
      <div style={centered}>
        <div
          style={{
            fontSize: height * 0.09,
            fontWeight: 800,
            letterSpacing: `${v.tracking}em`,
            opacity: v.opacity,
            transform: `translateY(${v.y * height}px)`,
          }}
        >
          {p.text}
        </div>
        <div
          style={{
            width: height * 0.32 * v.rule,
            height: Math.max(2, height * 0.006),
            background: GOLD,
            marginTop: height * 0.018,
            opacity: v.opacity,
          }}
        />
        {p.subtext ? (
          <div
            style={{
              fontSize: height * 0.03,
              marginTop: height * 0.02,
              letterSpacing: "0.2em",
              color: GOLD,
              opacity: v.sub,
            }}
          >
            {p.subtext}
          </div>
        ) : null}
      </div>
    </Frame>
  );
};
