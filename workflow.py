from langgraph.graph import StateGraph, START, END
from state import SettlementState
from agents import treasury_agent, oversight_agent
from onchain_bridge import settle_onchain

def execution_node(state: SettlementState) -> dict:
    trade = state["trade"]
    rail = state["assigned_rail"]
    fee = state.get("estimated_fee_usd", 0.0)

    # 1. On-Chain CBDC Rail Execution
    if rail == "UNIFIED_CBDC_RAIL":
        remaining_collateral = state["collateral_available_usd"] - (trade.amount + fee)
        try:
            tx_hash = settle_onchain(
                trade_id=trade.trade_id,
                amount=int(trade.amount),
                asset=trade.asset_symbol,
                rail=rail
            )
            return {
                "collateral_available_usd": remaining_collateral,
                "audit_log": [
                    f"[ExecutionNode] ATOMIC DVP COMPLETE via {rail}.",
                    f"[ExecutionNode] Tx Hash: {tx_hash}",
                    f"[ExecutionNode] Settled: ${trade.amount:,.2f} | Fee: ${fee:,.2f} | Remaining Collateral: ${remaining_collateral:,.2f}"
                ]
            }
        except Exception as e:
            return {
                "audit_log": [
                    f"[ExecutionNode] ON-CHAIN EXECUTION FAILED: {str(e)}",
                    f"[ExecutionNode] Rollback initiated. Vault liquidity untouched."
                ]
            }

    # 2. Legacy Correspondent Rail Execution (External RTGS / SWIFT Nostro-Vostro)
    return {
        "collateral_available_usd": state["collateral_available_usd"],  # Vault collateral untouched
        "audit_log": [
            f"[ExecutionNode] DISPATCHED VIA {rail} (SWIFT MT202 / Fedwire).",
            f"[ExecutionNode] Value: ${trade.amount:,.2f} | Estimated SOFR Drag & Tariffs: ${fee:,.2f}",
            f"[ExecutionNode] Vault Collateral Reserved: $0.00 (External settlement)."
        ]
    }

def abort_node(state: SettlementState) -> dict:
    trade = state["trade"]
    reason = state.get("rejection_reason", "Compliance failure")
    return {
        "audit_log": [
            f"[AbortNode] CIRCUIT BREAKER TRIGGERED for {trade.trade_id}.",
            f"[AbortNode] REASON: {reason}",
            f"[AbortNode] Rollback complete. Zero capital moved."
        ]
    }

def route_post_oversight(state: SettlementState) -> str:
    if state.get("compliance_approved") is True:
        return "execution"
    return "abort"

def create_settlement_graph():
    builder = StateGraph(SettlementState)

    builder.add_node("treasury", treasury_agent)
    builder.add_node("oversight", oversight_agent)
    builder.add_node("execution", execution_node)
    builder.add_node("abort", abort_node)

    builder.add_edge(START, "treasury")
    builder.add_edge("treasury", "oversight")
    builder.add_conditional_edges(
        "oversight",
        route_post_oversight,
        {
            "execution": "execution",
            "abort": "abort"
        }
    )
    builder.add_edge("execution", END)
    builder.add_edge("abort", END)

    return builder.compile()