import time
import sys
from state import TradeTicket
from workflow import create_settlement_graph
from netting_engine import BilateralNettingEngine, RawObligation

def banner(title):
    print("\n\033[1;36m" + "="*80)
    print(f" {title}")
    print("="*80 + "\033[0m\n")

def run_interactive_pipeline():
    banner("DVP SETTLEMENT ENGINE: AUTONOMOUS ROUTING & REGTECH DEMONSTRATION")
    print("\033[3mInitializing LangGraph Dual-Agent State Orchestrator...\033[0m\n")
    time.sleep(1.0)

    # 1. Bilateral Netting Phase
    banner("PHASE 1: INTRADAY BILATERAL OBLIGATION NETTING")
    raw_stream = [
        RawObligation("OB-101", "CLEARFLOW_VAULT", "BARCLAYS_LON", "USD_CBDC", 14_500_000.0),
        RawObligation("OB-102", "BARCLAYS_LON", "CLEARFLOW_VAULT", "USD_CBDC", 9_000_000.0),
        RawObligation("OB-103", "CLEARFLOW_VAULT", "JPM_NY", "USD_CBDC", 20_000_000.0),
        RawObligation("OB-104", "JPM_NY", "CLEARFLOW_VAULT", "USD_CBDC", 16_500_000.0),
    ]

    netting = BilateralNettingEngine()
    metrics = netting.compute_bilateral_netting(raw_stream)

    print(f"Gross Wholesale Submissions:  \033[1m${metrics['gross_volume_usd']:,.2f}\033[0m across 4 orders")
    print(f"Net Bilateral Exposure:       \033[1;32m${metrics['netted_volume_usd']:,.2f}\033[0m")
    print(f"Trapped Capital Freed:        \033[1;32m${metrics['liquidity_freed_usd']:,.2f} ({metrics['netting_efficiency_pct']:.1f}% reduction)\033[0m")
    time.sleep(1.2)

    # 2. Agentic Routing & Screening Phase
    banner("PHASE 2: DUAL-AGENT DVP ROUTING & REGTECH CIRCUIT BREAKER")
    graph = create_settlement_graph()

    tickets = [
        TradeTicket("TR-001", "BARCLAYS BANK PLC", 5_500_000.0, "USD_CBDC", "GB"),
        TradeTicket("TR-002", "VTB BANK PJSC", 3_500_000.0, "USD_CBDC", "RU"),
        TradeTicket("TR-003", "CITIBANK NA", 45_000_000.0, "USD_CBDC", "US"),
    ]

    vault_collateral = 10_000_000.0

    for t in tickets:
        print(f"\n\033[1m>>> Processing Ticket {t.trade_id} | Counterparty: {t.counterparty} | ${t.amount:,.2f}\033[0m")
        state_in = {
            "trade": t,
            "collateral_available_usd": vault_collateral,
            "compliance_approved": None,
            "assigned_rail": None,
            "estimated_fee_usd": 0.0,
            "audit_log": [],
            "rejection_reason": None
        }

        out = graph.invoke(state_in)
        for log in out["audit_log"]:
            if any(k in log for k in ["BREACH", "CIRCUIT", "FAILED"]):
                print(f"  \033[1;31m{log}\033[0m")
            elif any(k in log for k in ["ALLOCATED", "PASSED", "ATOMIC"]):
                print(f"  \033[1;32m{log}\033[0m")
            elif any(k in log for k in ["INSUFFICIENT", "LEGACY"]):
                print(f"  \033[1;33m{log}\033[0m")
            else:
                print(f"  \033[0;37m{log}\033[0m")
            time.sleep(0.3)

        if out.get("assigned_rail") == "UNIFIED_CBDC_RAIL" and out.get("compliance_approved"):
            vault_collateral = out["collateral_available_usd"]

    banner("DEMONSTRATION COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    run_interactive_pipeline()
