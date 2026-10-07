from state import SettlementState
from compliance_engine import InstitutionalComplianceEngine
from cost_engine import InstitutionalCostModel

compliance_screener = InstitutionalComplianceEngine()
cost_model = InstitutionalCostModel(sofr_rate_pct=4.80)

def treasury_agent(state: SettlementState) -> dict:
    """
    Evaluates intraday capital requirements, calculating SOFR opportunity cost 
    and gas friction before assigning optimal routing.
    """
    trade = state["trade"]
    available_liquidity = state["collateral_available_usd"]

    # Calculate empirical costs across both rails
    legacy_cost = cost_model.calculate_legacy_cost(trade.amount, settlement_lag_hours=48.0)
    onchain_cost = cost_model.calculate_onchain_cost(trade.amount)

    # Route evaluation
    if trade.amount <= available_liquidity:
        assigned_rail = "UNIFIED_CBDC_RAIL"
        estimated_fee = onchain_cost["total_cost_usd"]
        decision_log = (
            f"[TreasuryAgent] ALLOCATED: ${trade.amount:,.2f} on UNIFIED_CBDC_RAIL. "
            f"Cost: ${estimated_fee:,.2f} (Saved ${legacy_cost['total_cost_usd'] - estimated_fee:,.2f} vs Legacy transit drag)."
        )
    else:
        assigned_rail = "LEGACY_CORRESPONDENT_RAIL"
        estimated_fee = legacy_cost["total_cost_usd"]
        decision_log = (
            f"[TreasuryAgent] INSUFFICIENT ESCROW COLLATERAL (${available_liquidity:,.2f} < ${trade.amount:,.2f}). "
            f"Fallen back to LEGACY_CORRESPONDENT_RAIL. Transit Cost: ${estimated_fee:,.2f}."
        )

    return {
        "assigned_rail": assigned_rail,
        "estimated_fee_usd": round(estimated_fee, 2),
        "audit_log": [decision_log]
    }

def oversight_agent(state: SettlementState) -> dict:
    """
    RegTech Agent: Enforces deterministic US Treasury OFAC SDN matching 
    and FATF jurisdictional restrictions.
    """
    trade = state["trade"]
    screening = compliance_screener.screen_entity(trade.counterparty, trade.jurisdiction)

    if not screening["passed"]:
        return {
            "compliance_approved": False,
            "rejection_reason": f"REGTECH BREACH: {screening['reason']}",
            "audit_log": [
                f"[OversightAgent] BREACH DETECTED: {trade.counterparty} ({trade.jurisdiction})",
                f"[OversightAgent] MATCH DETAIL: {screening['matched_record'] or 'Jurisdiction Block'}",
                f"[OversightAgent] CIRCUIT BREAKER TRIPPED for Trade ID: {trade.trade_id}"
            ]
        }

    return {
        "compliance_approved": True,
        "audit_log": [
            f"[OversightAgent] PASSED: {trade.counterparty} verified against OFAC SDN database."
        ]
    }