"""Plot estimated tilt and measured angular rate from a policy-shadow capture."""
import argparse
import csv
import math
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    cache = Path(__file__).resolve().parents[1] / 'build' / 'plot-cache'
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with args.capture.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    start = int(rows[0]['t_us'])
    time = [((int(row['t_us']) - start) % 2**32) / 1e6 for row in rows]
    tilt = [math.degrees(math.acos(max(-1, min(1, -float(row['down_z']))))) for row in rows]
    rate = [math.sqrt(sum(float(row[f'gyro_{axis}_rad_s'])**2 for axis in 'xyz')) for row in rows]
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.3), sharex=True, layout='constrained')
    axes[0].plot(time, tilt, color='#1769aa', linewidth=1.6)
    axes[0].set(ylabel='Estimated tilt (degrees)', ylim=(0, 185), yticks=[0, 45, 90, 135, 180])
    axes[0].axhline(90, color='#999999', linewidth=.6, linestyle='--')
    axes[1].plot(time, rate, color='#bd4d21', linewidth=1.3)
    axes[1].set(xlabel='Seconds from first recorded sensor sample', ylabel='Angular rate norm (rad/s)', ylim=(0, None))
    for axis in axes:
        axis.grid(alpha=.18)
        axis.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Manual robot rotations — motor outputs disabled\nEstimated orientation; no external angle reference', fontsize=12)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=160)
    plt.close(fig)
    print(args.out)


if __name__ == '__main__':
    main()
