import pandas as pd
from state import TradeTicket
from workflow import create_settlement_graph
from netting_engine import BilateralNettingEngine, RawObligation

def run_empirical_simulation():
    graph = create_settlement_graph()

    # Empirical test pool representing institutional intraday wholesale flows
    raw_tickets = [
        # Legitimate Tier-1 Flow
        ("JPMORGAN CHASE BANK NA", 15_000_000.0, "US"),
        ("BARCLAYS BANK PLC", 8_500_000.0, "GB"),
        ("BNP PARIBAS SA", 12_000_000.0, "FR"),
        ("DEUTSCHE BANK AG", 6_000_000.0, "DE"),
        ("CITIBANK NA", 22_000_000.0, "US"),
        ("UBS AG", 9_000_000.0, "CH"),
        ("HSBC BANK PLC", 14_000_000.0, "GB"),
        
        # Sanctioned Entities / Aliases / FATF Jurisdiction Hits
        ("VTB BANK PJSC", 4_500_000.0, "RU"),
        ("BANK SEPAH", 3_000_000.0, "IR"),
        ("KORYO BANK", 1_500_000.0, "KP"),
        ("SBERBANK OF RUSSIA", 11_000_000.0, "RU"),
        
        # Secondary Flow (Reciprocal obligations for netting)
        ("BARCLAYS BANK PLC", 5_000_000.0, "GB"),
        ("JPMORGAN CHASE BANK NA", 10_000_000.0, "US"),
        ("BNP PARIBAS SA", 7_000_000.0, "FR"),
    ]

    # 1. Bilateral Netting Analysis
    obligations = [
        RawObligation(
            obligation_id=f"OB-{i:03d}",
            payer="OUR_INSTITUTION",
            receiver=cpty,
            asset="USD_CBDC",
            amount=amt
        ) if i % 2 == 0 else
        RawObligation(
            obligation_id=f"OB-{i:03d}",
            payer=cpty,
            receiver="OUR_INSTITUTION",
            asset="USD_CBDC",
            amount=amt
        )
        for i, (cpty, amt, jur) in enumerate(raw_tickets)
    ]

    netting_engine = BilateralNettingEngine()
    netting_metrics = netting_engine.compute_bilateral_netting(obligations)

    # 2. Execution Run through LangGraph Agents
    results = []
    vault_collateral = 25_000_000.0  # $25M initial vault allocation

    for i, (cpty, amt, jur) in enumerate(raw_tickets):
        trade = TradeTicket(
            trade_id=f"TR-{i:03d}",
            counterparty=cpty,
            amount=amt,
            asset_symbol="USD_CBDC",
            jurisdiction=jur
        )

        state_in = {
            "trade": trade,
            "collateral_available_usd": vault_collateral,
            "compliance_approved": None,
            "assigned_rail": None,
            "estimated_fee_usd": 0.0,
            "audit_log": [],
            "rejection_reason": None
        }

        state_out = graph.invoke(state_in)

        # Update collateral balance if on-chain DvP executed
        if state_out.get("assigned_rail") == "UNIFIED_CBDC_RAIL" and state_out.get("compliance_approved"):
            vault_collateral = state_out["collateral_available_usd"]

        results.append({
            "trade_id": trade.trade_id,
            "counterparty": trade.counterparty,
            "amount_usd": trade.amount,
            "jurisdiction": trade.jurisdiction,
            "compliance_approved": state_out.get("compliance_approved", False),
            "rejection_reason": state_out.get("rejection_reason"),
            "assigned_rail": state_out.get("assigned_rail"),
            "fee_usd": state_out.get("estimated_fee_usd", 0.0)
        })

    df = pd.DataFrame(results)
    df.to_csv("empirical_simulation_results.csv", index=False)

    # 3. Print Institutional Summary
    print("\n" + "=" * 80)
    print("EMPIRICAL INSTITUTIONAL SETTLEMENT BENCHMARK")
    print("=" * 80)
    print(f"Gross Trade Volume Submitted:   ${netting_metrics['gross_volume_usd']:,.2f}")
    print(f"Net Settlement Demand:          ${netting_metrics['netted_volume_usd']:,.2f}")
    print(f"Bilateral Netting Efficiency:   {netting_metrics['netting_efficiency_pct']:.2f}% capital freed")
    print("-" * 80)

    cleared = df[df["compliance_approved"] == True]
    blocked = df[df["compliance_approved"] == False]

    print(f"Trades Cleared by RegTech:      {len(cleared)} / {len(df)} (${cleared['amount_usd'].sum():,.2f})")
    print(f"Breaches Caught (OFAC/FATF):    {len(blocked)} / {len(df)} (${blocked['amount_usd'].sum():,.2f})")
    print("-" * 80)
    print("EXECUTION BREAKDOWN BY RAIL:")
    for rail, group in cleared.groupby("assigned_rail"):
        print(f"  * {rail:<26}: {len(group)} trades | ${group['amount_usd'].sum():,.2f} vol | Total Friction: ${group['fee_usd'].sum():,.2f}")

    print("\nREGTECH CIRCUIT BREAKER AUDIT:")
    for _, row in blocked.iterrows():
        print(f"  * [BLOCKED] {row['counterparty']} ({row['jurisdiction']}) -> {row['rejection_reason']}")

if __name__ == "__main__":
    run_empirical_simulation()