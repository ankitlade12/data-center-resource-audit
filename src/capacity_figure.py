"""Render the conditional capacity screen at the analysis's final print width."""
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/isi-mpl-cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / "reports/tables").mkdir(parents=True, exist_ok=True)
    summary = json.loads((ROOT / 'reports/local_constraints.json').read_text())
    case = next(row for row in summary['allowances'] if row['year'] == 2029)
    plt.rcParams.update({'font.size': 8, 'pdf.fonttype': 42})
    fig, ax = plt.subplots(figsize=(4.8, 3.5))
    fig.subplots_adjust(left=.14, right=.97, top=.90, bottom=.36)
    low = case['joint_additional_mgd_high_peak']
    high = case['joint_additional_mgd_low_peak']
    ax.axvspan(0, low, facecolor='#deebdf', hatch='..', edgecolor='#a0b5a0',
               label='Passes tested bounds')
    ax.axvspan(low, high, facecolor='#ffedbd', edgecolor='#b3a77f',
               label='Peak-factor sensitive')
    ax.axvspan(high, 1.5, facecolor='#f1dddd', hatch='//', edgecolor='#c2a0a0',
               label='Fails a tested bound')
    q = np.linspace(0, 1.5, 301)
    for factor, style in zip(summary['historical_peak_bounds'], ['-', '--']):
        ax.plot(q, case['peak_margin_mgd'] - q * factor, style, linewidth=1.4,
                label=f'Critical-day factor {factor:.2f}')
    ax.axhline(0, color='black', linewidth=.7)
    ax.axvline(case['annual_only_additional_mgd'], color='black', linestyle=':',
               linewidth=1.4, label='Annual-only limit')
    ax.set(xlim=(0, 1.5), xlabel='Additional average demand (MGD)',
           ylabel='Remaining critical-day margin (MGD)',
           title='2029 municipal-plan sensitivity')
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.5, .015),
               ncol=2, fontsize=7.5, frameon=False)
    destination = ROOT / 'reports/figures'
    destination.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination / 'resource_validation_and_constraints.pdf')
    plt.close(fig)


if __name__ == '__main__':
    main()
