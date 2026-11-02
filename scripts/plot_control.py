"""Plot onboard estimated tilt, commanded joint angles and BAT-node telemetry."""
import argparse
import csv
import math
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    cache=Path(__file__).resolve().parents[1]/'build/plot-cache'
    cache.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR',str(cache))
    os.environ.setdefault('XDG_CACHE_HOME',str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with args.capture.open(newline='') as source:rows=list(csv.DictReader(source))
    start=int(rows[0]['t_us'])
    times=[((int(row['t_us'])-start)%2**32)/1e6 for row in rows]
    tilt=[math.degrees(math.acos(max(-1,min(1,-int(row['obs2_u6'])/1e6)))) for row in rows]
    targets=[[int(row[f'target{i}_urad'])/1e6*180/math.pi for row in rows] for i in range(2)]
    battery=[int(row['battery_mv'])/1000 for row in rows]
    fig,axes=plt.subplots(3,1,figsize=(9,7),sharex=True,layout='constrained',gridspec_kw={'height_ratios':[1.25,1.25,.7]})
    axes[0].plot(times,tilt,color='#1769aa',linewidth=1.4)
    axes[0].axhline(10,color='#999999',linestyle='--',linewidth=.7,label='10-degree tilt reference')
    axes[0].set(ylabel='Estimated base tilt (degrees)',ylim=(0,180))
    axes[0].legend(loc='upper right',fontsize=8)
    for target,color,label in zip(targets,['#bd4d21','#6d419d'],['Lower command','Upper command']):
        axes[1].plot(times,target,color=color,linewidth=1.2,label=label)
    axes[1].set(ylabel='Commanded joint angle (degrees)',ylim=(-85,85),yticks=[-80,-40,0,40,80])
    axes[1].legend(loc='lower left',bbox_to_anchor=(0,1.01),ncol=2,fontsize=8,frameon=False)
    axes[2].plot(times,battery,color='#348454',linewidth=1)
    axes[2].set(ylabel='BAT estimate (V)',xlabel='Seconds from first recorded sensor sample')
    for axis in axes:
        axis.grid(alpha=.18)
        axis.spines[['top','right']].set_visible(False)
    fig.suptitle('First sideways policy trial — trained +/-80-degree range\nEstimated base orientation and commanded targets; no shaft-angle feedback',fontsize=11)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.out,dpi=160)
    plt.close(fig)
    print(args.out)


if __name__=='__main__':main()
