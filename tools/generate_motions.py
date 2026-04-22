"""Generate motion3.json files for Doro.

Built on a parameter map derived from live screenshot exploration
(see tools/param_explorer.py + Desktop/doro_params/). Each motion combines
multiple parameter curves (head angles + body angles + mouth + eyes + bounce +
optionally Exp/AnimLine overlays) for richer visual layering than single-axis
motions. Uses Bezier-style smoothing via dense linear keyframe interpolation.

Cubism parser quirks handled:
- Rounds values to 4 decimals and clamps near-zero to exact 0.0 to avoid
  scientific notation in JSON (parser chokes on 3.67e-16).
- Uses indented JSON format (not compact single-line).
"""
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'assets' / 'dororong' / 'Doro' / 'Motions'


# -------- primitives ---------------------------------------------------------

def _clean(x):
    v = round(float(x), 4)
    if abs(v) < 1e-4:
        return 0.0
    return v


def linear_curve(param_id, keyframes):
    """Linear segments between keyframes. keyframes = [(t, v), ...]."""
    segments = [_clean(keyframes[0][0]), _clean(keyframes[0][1])]
    for t, v in keyframes[1:]:
        segments.extend([0, _clean(t), _clean(v)])
    return {
        'Target': 'Parameter',
        'Id': param_id,
        'Segments': segments,
        '_points': len(keyframes),
    }


def smooth_curve(param_id, keyframes, samples_per_seg=6):
    """Approximate cubic-Hermite easing by inserting eased samples between
    each pair of keyframes. Produces much softer motion than linear_curve.
    Uses smoothstep ease on [0,1] for each segment."""
    def smoothstep(u):
        # smootherstep = 6u^5 - 15u^4 + 10u^3 for extra softness
        return u * u * u * (u * (u * 6 - 15) + 10)

    dense = [keyframes[0]]
    for i in range(len(keyframes) - 1):
        t0, v0 = keyframes[i]
        t1, v1 = keyframes[i + 1]
        for s in range(1, samples_per_seg + 1):
            u = s / samples_per_seg
            eu = smoothstep(u)
            t = t0 + (t1 - t0) * u
            v = v0 + (v1 - v0) * eu
            dense.append((t, v))
    return linear_curve(param_id, dense)


def sine_curve(param_id, duration, amp, cycles, steps=16, offset=0.0, phase=0.0):
    kfs = []
    for i in range(steps + 1):
        t = duration * i / steps
        v = offset + amp * math.sin(2 * math.pi * (cycles * i / steps + phase))
        kfs.append((t, v))
    return linear_curve(param_id, kfs)


def stepped_osc(param_id, duration, low, high, period, steps_per_period=4):
    """Rapid alternation between `low` and `high` — e.g. ParamStep ±10 in run."""
    kfs = [(0.0, low)]
    t = 0.0
    toggle = True
    step_dt = period / steps_per_period
    while t < duration:
        t += step_dt
        toggle = not toggle
        kfs.append((t, high if toggle else low))
    kfs.append((duration, low))
    return linear_curve(param_id, kfs)


def motion(curves, duration, fps=30, loop=False):
    total_segs = sum(c['_points'] - 1 for c in curves)
    total_pts = sum(c['_points'] for c in curves)
    clean = [{k: v for k, v in c.items() if not k.startswith('_')} for c in curves]
    return {
        'Version': 3,
        'Meta': {
            'Duration': float(duration),
            'Fps': fps,
            'Loop': loop,
            'AreBeziersRestricted': True,
            'CurveCount': len(clean),
            'TotalSegmentCount': total_segs,
            'TotalPointCount': total_pts,
            'UserDataCount': 0,
            'TotalUserDataSize': 0,
        },
        'Curves': clean,
    }


# -------- motions ------------------------------------------------------------

MOTIONS = {}


# idle_breath — gentle breathing standby (6s loop, smooth everywhere)
# Driven: Breath + slight head sway + body sway + blink twice per cycle.
MOTIONS['idle_breath'] = motion([
    sine_curve('ParamBreath', 6.0, amp=0.45, cycles=1.0, steps=24, offset=0.45),
    sine_curve('ParamAngleX', 6.0, amp=3.5, cycles=0.5, steps=24),
    sine_curve('ParamAngleY', 6.0, amp=2.0, cycles=0.5, steps=24, phase=0.25),
    sine_curve('ParamAngleZ', 6.0, amp=1.5, cycles=0.5, steps=24),
    sine_curve('ParamBodyAngleZ', 6.0, amp=1.2, cycles=0.5, steps=24),
    sine_curve('ParamBodyAngleY', 6.0, amp=0.8, cycles=1.0, steps=24, phase=0.1),
    # Blinks: eyes closed briefly at t=2.5s and t=5s
    linear_curve('ParamEyeLOpen', [
        (0.0, 1.0), (2.3, 1.0), (2.45, 0.0), (2.6, 1.0),
        (4.8, 1.0), (4.95, 0.0), (5.1, 1.0), (6.0, 1.0),
    ]),
    linear_curve('ParamEyeROpen', [
        (0.0, 1.0), (2.3, 1.0), (2.45, 0.0), (2.6, 1.0),
        (4.8, 1.0), (4.95, 0.0), (5.1, 1.0), (6.0, 1.0),
    ]),
    # Mouth softly neutral
    linear_curve('ParamMouthForm', [(0.0, 0.2), (6.0, 0.2)]),
], duration=6.0, loop=True)


# nod — yes (1.4s, smoothed double nod)
MOTIONS['nod'] = motion([
    smooth_curve('ParamAngleY', [
        (0.0, 0.0), (0.25, -20.0), (0.55, 3.0),
        (0.85, -18.0), (1.15, 2.0), (1.4, 0.0),
    ]),
    smooth_curve('ParamBodyAngleY', [
        (0.0, 0.0), (0.25, -3.0), (0.55, 0.0),
        (0.85, -3.0), (1.15, 0.0), (1.4, 0.0),
    ]),
    smooth_curve('ParamMouthForm', [(0.0, 0.0), (0.15, 0.7), (1.25, 0.7), (1.4, 0.2)]),
    smooth_curve('ParamEyeSmile', [(0.0, 0.0), (0.2, 0.5), (1.0, 0.5), (1.4, 0.0)]),
    smooth_curve('ParamBrowLY', [(0.0, 0.0), (0.2, 0.3), (1.1, 0.3), (1.4, 0.0)]),
    smooth_curve('ParamBrowRY', [(0.0, 0.0), (0.2, 0.3), (1.1, 0.3), (1.4, 0.0)]),
    smooth_curve('ParamBreath', [(0.0, 0.0), (0.3, 0.5), (1.4, 0.0)]),
], duration=1.4, loop=False)


# shake — no (1.6s, triple shake with body counter-sway)
MOTIONS['shake'] = motion([
    smooth_curve('ParamAngleX', [
        (0.0, 0.0), (0.25, -24.0), (0.55, 22.0),
        (0.85, -20.0), (1.15, 18.0), (1.4, -6.0), (1.6, 0.0),
    ]),
    smooth_curve('ParamAngleZ', [
        (0.0, 0.0), (0.25, 4.0), (0.55, -4.0),
        (0.85, 3.0), (1.15, -3.0), (1.6, 0.0),
    ]),
    smooth_curve('ParamBodyAngleZ', [
        (0.0, 0.0), (0.4, -2.0), (0.9, 2.0), (1.6, 0.0),
    ]),
    smooth_curve('ParamMouthForm', [(0.0, 0.0), (0.15, -0.5), (1.4, -0.5), (1.6, 0.0)]),
    smooth_curve('ParamBrowLY', [(0.0, 0.0), (0.15, -0.5), (1.4, -0.5), (1.6, 0.0)]),
    smooth_curve('ParamBrowRY', [(0.0, 0.0), (0.15, -0.5), (1.4, -0.5), (1.6, 0.0)]),
    smooth_curve('ParamEyeAngle', [(0.0, 0.0), (0.3, -0.3), (0.8, 0.3), (1.6, 0.0)]),
], duration=1.6, loop=False)


# dance — 3s loop, full-body groove with stepped feet + sway + bounce
# Uses all of: AngleX/Z, BodyAngleZ, Step, Bounce1-4, Breath, MouthForm, EyeSmile
MOTIONS['dance'] = motion([
    sine_curve('ParamAngleX', 3.0, amp=20.0, cycles=2.0, steps=24),
    sine_curve('ParamAngleZ', 3.0, amp=10.0, cycles=2.0, steps=24, phase=0.25),
    sine_curve('ParamAngleY', 3.0, amp=6.0, cycles=4.0, steps=24),
    sine_curve('ParamBodyAngleZ', 3.0, amp=6.0, cycles=2.0, steps=24),
    sine_curve('ParamBodyAngleY', 3.0, amp=3.0, cycles=4.0, steps=24),
    stepped_osc('ParamStep', 3.0, low=-8.0, high=8.0, period=0.375),  # 8 steps
    sine_curve('ParamBounceInput1', 3.0, amp=0.8, cycles=4.0, steps=24, offset=0.0),
    sine_curve('ParamBounceInput2', 3.0, amp=0.6, cycles=4.0, steps=24, phase=0.25),
    sine_curve('ParamBounceInput3', 3.0, amp=0.4, cycles=2.0, steps=24),
    sine_curve('ParamBreath', 3.0, amp=0.5, cycles=2.0, steps=24, offset=0.5),
    linear_curve('ParamMouthForm', [(0.0, 1.0), (3.0, 1.0)]),
    linear_curve('ParamMouthOpenY', [
        (0.0, 0.0), (0.5, 0.4), (1.0, 0.0), (1.5, 0.4),
        (2.0, 0.0), (2.5, 0.4), (3.0, 0.0),
    ]),
    linear_curve('ParamEyeSmile', [(0.0, 0.7), (3.0, 0.7)]),
    linear_curve('ParamBrowLY', [(0.0, 0.3), (3.0, 0.3)]),
    linear_curve('ParamBrowRY', [(0.0, 0.3), (3.0, 0.3)]),
], duration=3.0, loop=True)


# surprised — 1.4s one-shot, wide eyes + open mouth + body flinch
MOTIONS['surprised'] = motion([
    smooth_curve('ParamEyeLOpen', [(0.0, 1.0), (0.08, 1.5), (0.8, 1.3), (1.4, 1.0)]),
    smooth_curve('ParamEyeROpen', [(0.0, 1.0), (0.08, 1.5), (0.8, 1.3), (1.4, 1.0)]),
    smooth_curve('ParamBrowLY', [(0.0, 0.0), (0.08, 1.0), (0.9, 0.9), (1.4, 0.0)]),
    smooth_curve('ParamBrowRY', [(0.0, 0.0), (0.08, 1.0), (0.9, 0.9), (1.4, 0.0)]),
    smooth_curve('ParamMouthOpenY', [(0.0, 0.0), (0.1, 0.9), (0.7, 0.5), (1.4, 0.0)]),
    smooth_curve('ParamMouthForm', [(0.0, 0.0), (0.1, -0.3), (0.8, -0.1), (1.4, 0.2)]),
    smooth_curve('ParamAngleY', [(0.0, 0.0), (0.1, -10.0), (0.5, -5.0), (1.4, 0.0)]),
    smooth_curve('ParamAngleX', [(0.0, 0.0), (0.15, 3.0), (0.4, -3.0), (1.4, 0.0)]),
    smooth_curve('ParamAngleZ', [(0.0, 0.0), (0.1, 4.0), (0.4, -4.0), (1.4, 0.0)]),
    smooth_curve('ParamBodyAngleZ', [(0.0, 0.0), (0.08, -5.0), (0.3, 4.0), (1.4, 0.0)]),
    smooth_curve('ParamBounceInput1', [(0.0, 0.0), (0.1, 1.0), (0.4, -0.3), (1.4, 0.0)]),
    smooth_curve('ParamBreath', [(0.0, 0.0), (0.1, 1.0), (0.8, 0.3), (1.4, 0.0)]),
], duration=1.4, loop=False)


# standup — 2.6s stretch / yawn / lean back
MOTIONS['standup'] = motion([
    smooth_curve('ParamBodyAngleY', [(0.0, -5.0), (0.6, 0.0), (1.5, 4.0), (2.2, 0.0), (2.6, 0.0)]),
    smooth_curve('ParamAngleY', [(0.0, 5.0), (0.7, -15.0), (1.3, -20.0), (2.0, 0.0), (2.6, 3.0)]),
    smooth_curve('ParamAngleZ', [(0.0, 0.0), (0.8, 8.0), (1.6, -8.0), (2.3, 3.0), (2.6, 0.0)]),
    smooth_curve('ParamAngleX', [(0.0, 0.0), (0.9, -5.0), (1.7, 5.0), (2.6, 0.0)]),
    smooth_curve('ParamMouthOpenY', [(0.0, 0.0), (0.9, 0.9), (1.5, 0.4), (2.1, 0.0), (2.6, 0.0)]),
    smooth_curve('ParamBreath', [(0.0, 0.0), (0.9, 1.0), (1.7, 0.4), (2.6, 0.0)]),
    smooth_curve('ParamEyeLOpen', [(0.0, 1.0), (1.0, 0.3), (1.5, 0.6), (2.0, 1.0), (2.6, 1.0)]),
    smooth_curve('ParamEyeROpen', [(0.0, 1.0), (1.0, 0.3), (1.5, 0.6), (2.0, 1.0), (2.6, 1.0)]),
    smooth_curve('ParamBodyAngleZ', [(0.0, 0.0), (0.7, -3.0), (1.5, 3.0), (2.6, 0.0)]),
    smooth_curve('ParamBounceInput1', [(0.0, 0.0), (1.0, 0.8), (1.7, -0.2), (2.6, 0.0)]),
], duration=2.6, loop=False)


# struggle — 1.3s one-shot, full-body struggle with tongue + frown
MOTIONS['struggle'] = motion([
    sine_curve('ParamAngleX', 1.3, amp=24.0, cycles=4.0, steps=20),
    sine_curve('ParamAngleY', 1.3, amp=14.0, cycles=3.0, steps=20, phase=0.1),
    sine_curve('ParamAngleZ', 1.3, amp=10.0, cycles=3.5, steps=20),
    sine_curve('ParamBodyAngleZ', 1.3, amp=7.0, cycles=4.0, steps=20),
    sine_curve('ParamBounceInput1', 1.3, amp=0.8, cycles=4.0, steps=20),
    sine_curve('ParamBounceInput2', 1.3, amp=0.6, cycles=3.0, steps=20, phase=0.5),
    smooth_curve('ParamMouthOpenY', [(0.0, 0.0), (0.15, 0.9), (0.5, 0.3), (0.9, 0.9), (1.3, 0.1)]),
    smooth_curve('ParamTongueOut', [(0.0, 0.0), (0.3, 1.0), (0.9, 0.7), (1.3, 0.0)]),
    smooth_curve('ParamBrowLY', [(0.0, 0.0), (0.2, -0.8), (1.1, -0.8), (1.3, 0.0)]),
    smooth_curve('ParamBrowRY', [(0.0, 0.0), (0.2, -0.8), (1.1, -0.8), (1.3, 0.0)]),
    smooth_curve('ParamMouthForm', [(0.0, 0.0), (0.2, -0.5), (1.0, -0.5), (1.3, 0.0)]),
    smooth_curve('ParamEyeLOpen', [(0.0, 1.0), (0.2, 1.3), (1.0, 1.2), (1.3, 1.0)]),
    smooth_curve('ParamEyeROpen', [(0.0, 1.0), (0.2, 1.3), (1.0, 1.2), (1.3, 1.0)]),
], duration=1.3, loop=False)


# run_plus — 1.0s loop, richer replacement for author's raw Idle.motion3.json.
# Keeps ParamStep ±10 stepping (the core gait) and AnimLine/AnimLoading overlay
# but layers in BodyAngleZ sway, Bounce1 sync, Breath pumping, forward lean.
MOTIONS['run_plus'] = motion([
    stepped_osc('ParamStep', 1.0, low=-10.0, high=10.0, period=0.125),  # 8 flips/sec
    stepped_osc('AnimLine', 1.0, low=0.0, high=1.0, period=0.08),
    sine_curve('AnimLoading1', 1.0, amp=1.0, cycles=1.0, steps=12),
    sine_curve('AnimLoading2', 1.0, amp=1.0, cycles=2.0, steps=12, offset=0.3),
    sine_curve('ParamBodyAngleZ', 1.0, amp=5.0, cycles=4.0, steps=16),
    sine_curve('ParamBodyAngleY', 1.0, amp=3.0, cycles=4.0, steps=16),
    sine_curve('ParamBounceInput1', 1.0, amp=0.9, cycles=4.0, steps=16),
    sine_curve('ParamBounceInput2', 1.0, amp=0.7, cycles=4.0, steps=16, phase=0.5),
    sine_curve('ParamBreath', 1.0, amp=0.5, cycles=4.0, steps=16, offset=0.5),
    linear_curve('ParamAngleY', [(0.0, -5.0), (1.0, -5.0)]),  # slight forward lean
    sine_curve('ParamAngleZ', 1.0, amp=3.0, cycles=4.0, steps=16, phase=0.5),
    linear_curve('ParamEyeSmile', [(0.0, 0.3), (1.0, 0.3)]),
    linear_curve('ParamMouthForm', [(0.0, 0.5), (1.0, 0.5)]),
    linear_curve('ParamMouthOpenY', [
        (0.0, 0.2), (0.25, 0.1), (0.5, 0.2), (0.75, 0.1), (1.0, 0.2),
    ]),
], duration=1.0, loop=True)


# cheer — celebratory bounce with star eyes and body up-thrust.
# Used as reaction for pet_head / pomodoro_break / wake.
MOTIONS['cheer'] = motion([
    smooth_curve('ParamBodyAngleY', [(0.0, 0.0), (0.2, -2.0), (0.4, 6.0),
                                     (0.8, -1.0), (1.2, 5.0), (1.6, 0.0)]),
    smooth_curve('ParamAngleY', [(0.0, 0.0), (0.3, 15.0), (0.8, 10.0),
                                 (1.2, 15.0), (1.6, 0.0)]),
    smooth_curve('ParamAngleZ', [(0.0, 0.0), (0.4, 6.0), (0.8, -6.0),
                                 (1.2, 4.0), (1.6, 0.0)]),
    smooth_curve('ParamBodyAngleZ', [(0.0, 0.0), (0.4, 3.0), (0.8, -3.0),
                                     (1.2, 2.0), (1.6, 0.0)]),
    smooth_curve('ParamBounceInput1', [(0.0, 0.0), (0.4, 1.0), (0.8, -0.3),
                                       (1.2, 1.0), (1.6, 0.0)]),
    smooth_curve('ParamMouthOpenY', [(0.0, 0.0), (0.4, 0.7), (0.8, 0.3),
                                     (1.2, 0.7), (1.6, 0.0)]),
    smooth_curve('ParamMouthForm', [(0.0, 0.5), (0.3, 1.0), (1.3, 1.0), (1.6, 0.5)]),
    smooth_curve('ParamEyeSmile', [(0.0, 0.0), (0.3, 1.0), (1.3, 1.0), (1.6, 0.0)]),
    smooth_curve('ParamBrowLY', [(0.0, 0.0), (0.3, 0.8), (1.3, 0.8), (1.6, 0.0)]),
    smooth_curve('ParamBrowRY', [(0.0, 0.0), (0.3, 0.8), (1.3, 0.8), (1.6, 0.0)]),
    smooth_curve('ParamBreath', [(0.0, 0.0), (0.4, 1.0), (0.8, 0.2),
                                 (1.2, 0.9), (1.6, 0.0)]),
], duration=1.6, loop=False)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in MOTIONS.items():
        path = OUT_DIR / f'{name}.motion3.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        meta = data['Meta']
        print(f'  -> {path.relative_to(ROOT)}  '
              f'({meta["Duration"]}s{" loop" if meta["Loop"] else ""}, '
              f'{meta["CurveCount"]} curves, {meta["TotalPointCount"]} pts)')
    print(f'Done. {len(MOTIONS)} motions written.')


if __name__ == '__main__':
    main()
