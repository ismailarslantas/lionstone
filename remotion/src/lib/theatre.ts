/**
 * Theatre.js keyframes for Remotion titles.
 *
 * Only `@theatre/core` (Apache-2.0) is used. Theatre's visual editor, `@theatre/studio`,
 * is AGPL: it is NOT a dependency of Lionstone. If you author keyframes with it, do that in
 * your own separate project and paste the exported state JSON here.
 *
 * Remotion renders frames out of order and in parallel, so the hook never plays the
 * sequence: it sets `sequence.position = frame / fps` and reads the values for that frame.
 */
import { useEffect, useMemo, useState } from "react";
import { getProject, ISheetObject, UnknownShorthandCompoundProps } from "@theatre/core";
import { continueRender, delayRender, useCurrentFrame, useVideoConfig } from "remotion";

type Key = { at: number; value: number; hold?: boolean };

/**
 * Build a Theatre project state from plain keyframes, so you can write tracks by hand.
 * `tracks` maps a numeric prop name to keyframes in seconds; easing is a smooth bezier
 * (ease-in-out) unless `hold` is set. A state exported by Theatre Studio works too.
 */
export function theatreState(
  sheet: string,
  object: string,
  tracks: Record<string, Key[]>,
  length: number,
) {
  const trackIdByPropPath: Record<string, string> = {};
  const trackData: Record<string, unknown> = {};
  for (const [prop, keys] of Object.entries(tracks)) {
    const id = `t_${prop}`;
    trackIdByPropPath[JSON.stringify([prop])] = id;
    trackData[id] = {
      type: "BasicKeyframedTrack",
      keyframes: keys.map((k, i) => ({
        id: `${id}_${i}`,
        position: k.at,
        value: k.value,
        handles: [0.5, 1, 0.5, 0],
        connectedRight: true,
        type: k.hold ? "hold" : "bezier",
      })),
    };
  }
  return {
    sheetsById: {
      [sheet]: {
        staticOverrides: { byObject: {} },
        sequence: {
          type: "PositionalSequence",
          length,
          subUnitsPerUnit: 30,
          tracksByObject: { [object]: { trackIdByPropPath, trackData } },
        },
      },
    },
    definitionVersion: "0.4.0",
    revisionHistory: [],
  };
}

/** The values of one Theatre object at the current Remotion frame. */
export function useTheatreSequence<P extends UnknownShorthandCompoundProps>(opts: {
  project: string;
  state: unknown;
  sheet: string;
  object: string;
  props: P;
  /** seconds to shift the sequence by (e.g. a title that starts later) */
  offset?: number;
}): ISheetObject<P>["value"] {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { sheet, obj, ready } = useMemo(() => {
    const project = getProject(opts.project, { state: opts.state as never });
    const sh = project.sheet(opts.sheet);
    return { sheet: sh, obj: sh.object(opts.object, opts.props), ready: project.ready };
    // the project is keyed by its id; props are its initial values
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts.project, opts.sheet, opts.object]);
  const [handle] = useState(() => delayRender("Theatre.js project"));
  useEffect(() => {
    ready.then(() => continueRender(handle));
  }, [ready, handle]);
  sheet.sequence.position = Math.max(0, frame / fps - (opts.offset ?? 0));
  return obj.value;
}
