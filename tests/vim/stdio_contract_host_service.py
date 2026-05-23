from __future__ import annotations

import json
import sys
import time


def emit(obj: dict, split_at: int | None = None, delay: float = 0.0) -> None:
    raw = json.dumps(obj) + "\n"
    if split_at and 0 < split_at < len(raw):
        sys.stdout.write(raw[:split_at])
        sys.stdout.flush()
        if delay > 0:
            time.sleep(delay)
        sys.stdout.write(raw[split_at:])
    else:
        sys.stdout.write(raw)
    sys.stdout.flush()


def main() -> int:
    for line in sys.stdin:
      line = line.strip()
      if not line:
        continue
      req = json.loads(line)
      rid = req.get('request_id', 'sc-req')
      payload = req.get('payload', {})
      run_id = payload.get('run_id', 'sc-run')
      scenario = payload.get('scenario', 'baseline')
      host_speed = str(payload.get('host_speed', 'fast')).lower()
      if host_speed == 'slow':
          """Human-interaction speed: a few seconds total stream time."""
          inter_event = 0.01
          split_delay = 0.003
      elif host_speed == 'sim_slow':
          """Automated-test speed: ~200-400ms total with still-visible pacing."""
          inter_event = 0.001
          split_delay = 0.0005
      else:
          inter_event = 0.0
          split_delay = 0.001

      seq = 1

      def frame(kind: str, **extra: object) -> dict:
          nonlocal seq
          out = {
              'protocol_version': 1,
              'request_id': rid,
              'ok': True,
              'payload': {
                  'kind': kind,
                  'run_id': run_id,
                  'seq': seq,
                  'emit_mono_ns': time.monotonic_ns(),
                  **extra,
              },
          }
          seq += 1
          return out

      emit(frame('push_ack'), split_at=11, delay=split_delay)
      if scenario == 'baseline':
          emit(frame('push_event', chunk='## TOAS:ASSISTANT\n'), split_at=21, delay=split_delay)
          time.sleep(inter_event)
          emit(frame('push_event', chunk='# Handoff\n'), split_at=9, delay=split_delay)
      elif scenario == 'hostile_noise':
          emit(frame('push_event', chunk='## TOAS:ASSISTANT\n'))
          time.sleep(inter_event)
          sys.stdout.write('NOISE NOT JSON\n')
          sys.stdout.flush()
          time.sleep(inter_event)
          emit(frame('push_event', chunk='# Handoff\n'), delay=split_delay)
      elif scenario == 'burst':
          for i in range(200):
              emit(frame('push_event', chunk=f'chunk-{i:03d}\n'), split_at=25, delay=split_delay)
              if inter_event:
                  time.sleep(inter_event)
      else:
          emit(frame('push_event', chunk=f'unknown:{scenario}\n'), delay=split_delay)

      emit(frame('push_complete', complete=True), split_at=7)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
