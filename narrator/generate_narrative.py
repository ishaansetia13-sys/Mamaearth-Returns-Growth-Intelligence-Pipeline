"""SCR insight narrator. Works without an API key; Gemini is optional."""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate_scr_narrative_offline(findings: dict) -> dict:
    f = findings
    rates = f['return_rate_by_payment']
    risk = f['highest_risk_segment']
    peak = f['true_peak_month']
    jan = f['outlier_inflated_month']
    month = {'01': 'January', '02': 'February', '03': 'March', '04': 'April',
             '05': 'May', '06': 'June'}[peak['month'][-2:]]
    narrative = (
        'Situation\n'
        f'The cleaned order data shows revenue of INR {f["cleaned_total_revenue_inr"]:,.2f}. '
        f'After removing unusual bulk orders, {month} is the strongest month at '
        f'INR {peak["revenue_inr"]:,.2f}. This gives us a more useful view of normal sales.\n\n'
        'Complication\n'
        f'COD orders have a {rates["COD"]:.1f}% return rate, compared with '
        f'{rates["CARD"]:.1f}% for card and {rates["UPI"]:.1f}% for UPI. '
        f'The highest-risk group is COD customers in Tier-{risk["city_tier"]} cities, '
        f'where the return rate is {risk["return_rate_pct"]:.1f}%. '
        f'The original revenue of INR {f["raw_total_revenue_inr"]:,.2f} also included '
        f'five duplicate orders worth INR {f["duplicate_reconciliation_delta_inr"]:,.2f}. '
        f'January appeared to lead at INR {jan["apparent_revenue_inr"]:,.2f}, but '
        f'falls to INR {jan["corrected_revenue_inr"]:,.2f} without the two bulk orders.\n\n'
        'Resolution\n'
        'The operations team should review COD orders in Tier-2 cities first and check '
        'whether delivery confirmation or customer communication can reduce returns. '
        'The finance team should use deduplicated revenue and keep unusual bulk orders '
        'separate when comparing monthly performance. These findings show where to '
        'investigate; they do not by themselves prove what causes returns.'
    )
    return {'status': 'success', 'narrative': narrative, 'tokens': 0}


def generate_scr_narrative(findings: dict) -> dict:
    key = os.getenv('GEMINI_API_KEY')
    if not key:
        return generate_scr_narrative_offline(findings)
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30000))
        system = ('You are a senior data analyst writing for Mamaearth\'s regional ops and finance heads. '
                  'Write three labeled sections: Situation, Complication, Resolution. '
                  'Every number must come from the supplied findings and appear with exactly the same value. '
                  'Do not invent statistics. Use plain English and about 250 words. '
                  'Include the cleaned revenue, COD rate, Tier-2 COD rate, duplicate delta, '
                  'and March peak revenue explicitly.')
        # Zero temperature reduces variation in this factual business report.
        response = client.models.generate_content(
            model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
            contents='Write the SCR report using these verified findings:\n' + json.dumps(findings, indent=2),
            config=types.GenerateContentConfig(system_instruction=system, temperature=0.0,
                                               max_output_tokens=1200))
        narrative = response.text or ''
        tokens = getattr(getattr(response, 'usage_metadata', None), 'total_token_count', None)
        return {'status': 'success', 'narrative': narrative, 'tokens': tokens}
    except Exception as err:
        return {'status': 'error', 'narrative': None, 'message': str(err)}


def check_numbers(narrative: str, findings: dict) -> bool:
    plain = narrative.replace(',', '')
    peak = findings['true_peak_month']
    checks = {
        'cleaned revenue': f'{findings["cleaned_total_revenue_inr"]:.2f}',
        'COD return rate': f'{findings["return_rate_by_payment"]["COD"]:.1f}',
        'Tier-2 COD return rate': f'{findings["highest_risk_segment"]["return_rate_pct"]:.1f}',
        'duplicate reconciliation': f'{findings["duplicate_reconciliation_delta_inr"]:.2f}',
        'March peak revenue': f'{peak["revenue_inr"]:.2f}'
    }
    ok = True
    for label, value in checks.items():
        passed = value in plain and (label != 'March peak revenue' or 'March' in narrative)
        print(f'{label}: {"PASS" if passed else "FAIL"}')
        ok = ok and passed
    return ok


if __name__ == '__main__':
    findings = json.loads((ROOT / 'narrator/findings.json').read_text())
    result = generate_scr_narrative(findings)
    if result['status'] == 'error':
        print('Gemini request failed; using the offline version:', result['message'])
        result = generate_scr_narrative_offline(findings)
    elif not check_numbers(result['narrative'], findings):
        print('Gemini omitted a required figure; using the checked offline version.')
        result = generate_scr_narrative_offline(findings)
    print('\n' + result['narrative'] + '\n')
    assert check_numbers(result['narrative'], findings)
    (ROOT / 'narrator/sample_output.txt').write_text(result['narrative'] + '\n')
    print('Saved checked narrative to narrator/sample_output.txt')
