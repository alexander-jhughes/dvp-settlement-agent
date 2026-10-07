import yfinance as yf

class InstitutionalCostModel:
    def __init__(self, sofr_rate_pct: float = 4.80):
        self.sofr_rate = sofr_rate_pct / 100.0
        self.eth_usd_cache = 3200.0

    def calculate_legacy_cost(self, notional_usd: float, settlement_lag_hours: float = 24.0) -> dict:
        """
        Legacy Correspondent Banking Model:
        1. Swift MT103 / MT202 messaging charges: ~$15.00 fixed
        2. Intermediary / Nostro-Vostro routing fee: 2 bps (0.0002) of notional, capped at $250
        3. Bilateral Credit Risk / Liquidity drag: SOFR opportunity cost for settlement delay
        """
        swift_fee = 15.00
        routing_fee = min(notional_usd * 0.0002, 250.0)
        
        # Capital drag during settlement transit: Notional * SOFR * (Hours / (360 * 24))
        liquidity_drag = notional_usd * self.sofr_rate * (settlement_lag_hours / (360.0 * 24.0))
        total_cost = swift_fee + routing_fee + liquidity_drag

        return {
            "rail": "LEGACY_CORRESPONDENT_RAIL",
            "fixed_swift_fee": swift_fee,
            "routing_charge": routing_fee,
            "liquidity_drag_usd": liquidity_drag,
            "total_cost_usd": total_cost,
            "bps_effective": (total_cost / notional_usd) * 10000
        }

    def calculate_onchain_cost(self, notional_usd: float, gas_used: int = 145000, gwei: float = 20.0) -> dict:
        """
        Atomic Vault / CBDC Settlement Model:
        1. On-Chain L1 Execution Gas Cost: gas_used * gwei * 1e-9 * ETH_USD
        2. Pre-funded Collateral Lock Drag: Assumes 15-minute escrow turnover
        """
        gas_eth = gas_used * (gwei * 1e-9)
        gas_usd = gas_eth * self.eth_usd_cache
        
        # 15 minutes liquidity lock time in escrow
        turnover_hours = 0.25
        collateral_drag = notional_usd * self.sofr_rate * (turnover_hours / (360.0 * 24.0))
        total_cost = gas_usd + collateral_drag

        return {
            "rail": "UNIFIED_CBDC_RAIL",
            "gas_cost_usd": gas_usd,
            "collateral_drag_usd": collateral_drag,
            "total_cost_usd": total_cost,
            "bps_effective": (total_cost / notional_usd) * 10000
        }


if __name__ == "__main__":
    cm = InstitutionalCostModel()
    notional = 10_000_000.0 # $10M wholesale trade
    
    legacy = cm.calculate_legacy_cost(notional, settlement_lag_hours=48.0)
    onchain = cm.calculate_onchain_cost(notional)
    
    print(f"\n--- Cost Benchmark for ${notional:,.2f} Wholesale Trade ---")
    print(f"Legacy Rail:  ${legacy['total_cost_usd']:,.2f} ({legacy['bps_effective']:.2f} bps) [Drag: ${legacy['liquidity_drag_usd']:,.2f}]")
    print(f"On-Chain DvP: ${onchain['total_cost_usd']:,.2f} ({onchain['bps_effective']:.2f} bps) [Gas: ${onchain['gas_cost_usd']:,.2f}, Drag: ${onchain['collateral_drag_usd']:,.2f}]")