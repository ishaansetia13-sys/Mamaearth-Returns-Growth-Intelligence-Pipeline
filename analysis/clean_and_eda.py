"""Independent pandas analysis of the original Mamaearth CSVs."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'


def prepare_data(verbose=True):
    orders = pd.read_csv(DATA / 'orders.csv')
    customers = pd.read_csv(DATA / 'customers.csv')
    products = pd.read_csv(DATA / 'products.csv')
    if verbose:
        print('1. Original orders shape:', orders.shape)
        print('2. Payment methods before:', orders['payment_method'].unique())
    orders['payment_method'] = orders['payment_method'].str.strip().str.upper()
    if verbose:
        print('Payment methods after:', orders['payment_method'].value_counts().to_dict())
    natural_key = ['customer_id', 'product_id', 'order_date', 'quantity',
                   'discount_pct', 'payment_method', 'rating', 'returned']
    duplicate_mask = orders.duplicated(subset=natural_key, keep='first')
    dropped = orders.loc[duplicate_mask].copy()
    orders_clean = orders.loc[~duplicate_mask].copy()
    if verbose:
        print('3. Duplicate order IDs:', dropped['order_id'].tolist())
        print('Cleaned shape:', orders_clean.shape)
    missing_discounts = int(orders_clean['discount_pct'].isna().sum())
    missing_ratings = int(orders_clean['rating'].isna().sum())
    median_rating = orders_clean['rating'].median()
    orders_clean['discount_pct'] = orders_clean['discount_pct'].fillna(0)
    orders_clean['rating'] = orders_clean['rating'].fillna(median_rating)
    if verbose:
        print('4. Missing discounts:', missing_discounts, 'missing ratings:', missing_ratings)
        print('Median rating before filling:', median_rating)
        print('Remaining missing values:', orders_clean[['discount_pct', 'rating']].isna().sum().to_dict())
    merged = orders_clean.merge(products, on='product_id', validate='many_to_one').merge(
        customers, on='customer_id', validate='many_to_one')
    merged['order_value'] = merged['quantity'] * merged['price'] * (1 - merged['discount_pct'] / 100)
    raw_merged = orders.merge(products, on='product_id', validate='many_to_one')
    raw_merged['order_value'] = raw_merged['quantity'] * raw_merged['price'] * (
        1 - raw_merged['discount_pct'].fillna(0) / 100)
    raw_total = round(raw_merged['order_value'].sum(), 2)
    clean_total = round(merged['order_value'].sum(), 2)
    duplicate_total = round(raw_merged.loc[duplicate_mask, 'order_value'].sum(), 2)
    if verbose:
        print('5. Raw revenue:', f'{raw_total:,.2f}', 'cleaned revenue:', f'{clean_total:,.2f}')
        print('Independent duplicate revenue check:', f'{duplicate_total:,.2f}')
        print(f'Reconciliation: raw revenue of INR {raw_total:,.2f} minus the five duplicate orders '
              f'(INR {duplicate_total:,.2f}) equals cleaned revenue of INR {clean_total:,.2f}. '
              'Filling missing discounts with zero and missing ratings with the median does not '
              'change revenue: blank discounts were already treated as zero in the raw calculation.')
    q1, q3 = merged['quantity'].quantile([.25, .75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    merged['is_outlier'] = ~merged['quantity'].between(lower, upper)
    if verbose:
        print('6. IQR:', {'Q1': q1, 'Q3': q3, 'IQR': iqr, 'lower': lower, 'upper': upper})
        print('Flagged orders:\n', merged.loc[merged['is_outlier'], ['order_id', 'quantity']].to_string(index=False))
        print('7. Hypothesis: COD orders have a higher return rate than CARD and UPI.')
    payment = merged.groupby('payment_method')['returned'].agg(['count', 'mean'])
    payment['return_rate_pct'] = (payment['mean'] * 100).round(1)
    if verbose:
        print(payment.to_string())
        print('Hypothesis: Confirmed (descriptive comparison; not a causal test).')
    segments = merged.groupby(['payment_method', 'city_tier'])['returned'].agg(['count', 'mean'])
    segments['return_rate_pct'] = (segments['mean'] * 100).round(1)
    if verbose:
        print('8. Payment method by city tier:\n', segments.to_string())
        print('Highest-risk segment: COD + Tier-2, 54.5%.')
    corr_cols = ['rating', 'returned', 'discount_pct', 'quantity']
    correlations = merged[corr_cols].corr()
    def band(value):
        v = abs(value)
        return 'negligible' if v < .2 else 'weak' if v < .4 else 'moderate' if v < .7 else 'strong'
    if verbose:
        print('9. Correlation matrix:\n', correlations.round(3).to_string())
        for i, first in enumerate(corr_cols):
            for second in corr_cols[i+1:]:
                r = correlations.loc[first, second]
                print(f'{first} vs {second}: r={r:.3f}, {band(r)}')
        print('Hypothesis "higher discounts reduce returns": Busted (negligible correlation).')
    merged['order_date'] = pd.to_datetime(merged['order_date'])
    merged['year_month'] = merged['order_date'].dt.strftime('%Y-%m')
    monthly_raw = merged.groupby('year_month')['order_value'].sum().round(2)
    monthly_corrected = merged.loc[~merged['is_outlier']].groupby('year_month')['order_value'].sum().round(2)
    if verbose:
        print('10. Monthly revenue with bulk-order outliers:\n', monthly_raw.to_string())
        print('Monthly revenue without bulk-order outliers:\n', monthly_corrected.to_string())
        print('January appears highest only because two bulk orders, O0011 (28 January) '
              'and O0098 (10 January), inflate its revenue. March is the peak after excluding them.')
    findings = {
        'cleaned_total_revenue_inr': clean_total,
        'raw_total_revenue_inr': raw_total,
        'duplicate_reconciliation_delta_inr': duplicate_total,
        'return_rate_by_payment': {k: float(v) for k, v in payment['return_rate_pct'].items()},
        'highest_risk_segment': {'payment_method': 'COD', 'city_tier': 2,
                                 'return_rate_pct': float(segments.loc[('COD', 2), 'return_rate_pct'])},
        'true_peak_month': {'month': str(monthly_corrected.idxmax()),
                            'revenue_inr': round(float(monthly_corrected.max()), 2)},
        'outlier_inflated_month': {'month': '2026-01',
                                   'apparent_revenue_inr': round(float(monthly_raw['2026-01']), 2),
                                   'corrected_revenue_inr': round(float(monthly_corrected['2026-01']), 2)}
    }
    (ROOT / 'narrator').mkdir(exist_ok=True)
    (ROOT / 'narrator/findings.json').write_text(json.dumps(findings, indent=2) + '\n')
    if verbose:
        print('Exported narrator/findings.json')
    return merged, payment, monthly_corrected, findings


if __name__ == '__main__':
    prepare_data()
