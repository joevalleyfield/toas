## Goal

Project a usable transcript view from history without claiming authority over the exact user-edited surface.

## Scope

- Select a lineage/head from history
- Reconstruct transcript-format blocks from accepted message events
- Ignore non-message records during projection
- Support projection from an explicit node/head

## Behavior

- Projection emits transcript-format blocks
- Only accepted message events become transcript text
- Projection follows one lineage, not the whole DAG
- Projection rebuilds a usable history-backed view, not necessarily the user’s exact edited buffer
- Anchors may be used as optimization but are not required for correctness

## Non-Goals

- No automatic rewrite of `session.md`
- No claim of lossless recovery for user-edited phrasing after later rewrites
- No branch picker UI yet

## Done When

- A transcript view can be rebuilt from history alone
- Replaying a lineage produces stable message blocks
- Non-message records do not leak into transcript output
