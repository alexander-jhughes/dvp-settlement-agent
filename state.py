from typing import TypedDict, Optional, List
from dataclasses import dataclass

@dataclass
class TradeTicket:
    trade_id: str
    counterparty: str
    amount: float
    asset_symbol: str
    jurisdiction: str

class SettlementState(TypedDict):
    trade: TradeTicket
    collateral_available_usd: float
    compliance_approved: Optional[bool]
    assigned_rail: Optional[str]
    estimated_fee_usd: float
    audit_log: List[str]
    rejection_reason: Optional[str]