from state import TradeTicket
from workflow import create_settlement_graph

def run_production_suite():
    graph = create_settlement_graph()

    test_trades = [
        # 1. Clean Wholesale Interbank Trade (Liquid, Cleared)
        TradeTicket(
            trade_id="TR-WHOLESALE-001",
            counterparty="JPMORGAN CHASE BANK NA",
            amount=5_000_000.0,
            asset_symbol="USD_CBDC",
            jurisdiction="US"
        ),
        # 2. Sanctioned Entity Variant (Real OFAC hit)
        TradeTicket(
            trade_id="TR-SANCTION-002",
            counterparty="VTB BANK PJSC",
            amount=2_500_000.0,
            asset_symbol="USD_CBDC",
            jurisdiction="RU"
        ),
        # 3. High-Value Trade Exceeding Vault Capacity (Forced to Correspondent Rail)
        TradeTicket(
            trade_id="TR-OVERFLOW-003",
            counterparty="GOLDMAN SACHS INTERNATIONAL",
            amount=50_000_000.0,
            asset_symbol="USD_CBDC",
            jurisdiction="GB"
        )
    ]

    current_collateral = 10_000_000.0 # $10M pre-funded in off-exchange vault

    print("=" * 80)
    print("STARTING INSTITUTIONAL DvP SETTLEMENT ENGINE TEST")
    print("=" * 80)

    for trade in test_trades:
        print(f"\n>>> PROCESSING TICKET: {trade.trade_id} | {trade.counterparty} | ${trade.amount:,.2f}")
        initial_state = {
            "trade": trade,
            "collateral_available_usd": current_collateral,
            "compliance_approved": None,
            "assigned_rail": None,
            "estimated_fee_usd": 0.0,
            "audit_log": [],
            "rejection_reason": None
        }

        final_state = graph.invoke(initial_state)

        for log in final_state["audit_log"]:
            print(log)

        # Update remaining collateral if settled on-chain
        if final_state.get("assigned_rail") == "UNIFIED_CBDC_RAIL" and final_state.get("compliance_approved"):
            current_collateral = final_state["collateral_available_usd"]

        print(f"Ending Vault Liquidity: ${current_collateral:,.2f}")
        print("-" * 80)

if __name__ == "__main__":
    run_production_suite()