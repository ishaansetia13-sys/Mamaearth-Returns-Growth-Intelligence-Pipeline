"""Regenerate both charts directly from the original CSVs."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from clean_and_eda import prepare_data

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'visualizations'
OUT.mkdir(exist_ok=True)
_, payment, monthly, _ = prepare_data(verbose=False)

rates = payment['return_rate_pct'].sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(7, 4.5))
bars = ax.bar(rates.index, rates.values)
ax.set_ylim(0, max(rates.values) + 12)
ax.set_ylabel('Return rate (%)')
ax.set_title('COD Returns at 44.4% — Around 3x Card')
for bar, value in zip(bars, rates.values):
    ax.text(bar.get_x() + bar.get_width()/2, value + 1, f'{value:.1f}%', ha='center')
fig.tight_layout()
fig.savefig(OUT / 'return_rate_by_payment.png', dpi=160)
plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(monthly.index, monthly.values, marker='o')
ax.set_xlabel('Month')
ax.set_ylabel('Revenue (INR)')
ax.set_title('March Is the Revenue Peak After Excluding Bulk Orders')
ax.tick_params(axis='x', rotation=30)
fig.tight_layout()
fig.savefig(OUT / 'monthly_revenue_trend.png', dpi=160)
plt.close(fig)
print('Saved both charts in visualizations/.')
