from collections import defaultdict
from dataclasses import dataclass

@dataclass
class RawObligation:
    obligation_id: str
    payer: str
    receiver: str
    asset: str
    amount: float

class BilateralNettingEngine:
    def __init__(self):
        pass

    def compute_bilateral_netting(self, obligations: list[RawObligation]) -> dict:
        """
        Calculates gross settlement demand vs bilaterally netted exposure per counterparty pair.
        Reduces gross collateral requirements across reciprocal currency flows.
        """
        gross_volume = sum(o.amount for o in obligations)
        pair_balances = defaultdict(float) # key: (min_bank, max_bank, asset), value: net balance relative to min_bank

        for o in obligations:
            # Deterministic ordering for pair key
            if o.payer < o.receiver:
                key = (o.payer, o.receiver, o.asset)
                pair_balances[key] -= o.amount
            else:
                key = (o.receiver, o.payer, o.asset)
                pair_balances[key] += o.amount

        netted_settlements = []
        netted_volume = 0.0

        for (bank1, bank2, asset), net_bal in pair_balances.items():
            if round(net_bal, 2) == 0.0:
                continue
            if net_bal < 0:
                # bank1 owes bank2
                payer, receiver = bank1, bank2
                amt = abs(net_bal)
            else:
                # bank2 owes bank1
                payer, receiver = bank2, bank1
                amt = net_bal

            netted_volume += amt
            netted_settlements.append({
                "payer": payer,
                "receiver": receiver,
                "asset": asset,
                "net_amount": amt
            })

        liquidity_savings_pct = ((gross_volume - netted_volume) / gross_volume * 100) if gross_volume > 0 else 0.0

        return {
            "gross_volume_usd": gross_volume,
            "netted_volume_usd": netted_volume,
            "liquidity_freed_usd": gross_volume - netted_volume,
            "netting_efficiency_pct": liquidity_savings_pct,
            "net_settlement_instructions": netted_settlements
        }


if __name__ == "__main__":
    # Test realistic intraday batch between Bank A and Bank B
    batch = [
        RawObligation("OB-01", "Bank_A", "Bank_B", "USD_CBDC", 12_500_000.0),
        RawObligation("OB-02", "Bank_B", "Bank_A", "USD_CBDC", 8_000_000.0),
        RawObligation("OB-03", "Bank_A", "Bank_B", "USD_CBDC", 3_500_000.0),
        RawObligation("OB-04", "Bank_B", "Bank_A", "USD_CBDC", 5_000_000.0),
    ]

    engine = BilateralNettingEngine()
    result = engine.compute_bilateral_netting(batch)

    print("\n--- INTRADAY BILATERAL NETTING RUN ---")
    print(f"Gross Volume:         ${result['gross_volume_usd']:,.2f}")
    print(f"Netted Final Volume:  ${result['netted_volume_usd']:,.2f}")
    print(f"Liquidity Saved:      ${result['liquidity_freed_usd']:,.2f} ({result['netting_efficiency_pct']:.1f}% reduction)")
    print("Settlement Instruction:", result['net_settlement_instructions'])