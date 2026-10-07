import simpy
import random
import pandas as pd
from state import TradeIntent
from workflow import create_settlement_graph

# Setup random seed for reproducible research runs
random.seed(42)

app = create_settlement_graph()

class SettlementSimulation:
    def __init__(self, env: simpy.Environment, initial_collateral: float):
        self.env = env
        self.collateral = initial_collateral
        self.records = []

    def process_trade(self, trade: TradeIntent):
        arrival_time = self.env.now

        # Prepare initial state for the LangGraph engine
        state = {
            "trade": trade,
            "collateral_available_usd": self.collateral,
            "assigned_rail": None,
            "estimated_fee_usd": None,
            "compliance_approved": None,
            "rejection_reason": None,
            "audit_log": []
        }

        # Invoke the LangGraph workflow
        result = app.invoke(state)

        # Update running vault collateral
        self.collateral = result["collateral_available_usd"]

        # Log metrics for econometric benchmarking
        self.records.append({
            "timestamp": arrival_time,
            "trade_id": trade.trade_id,
            "amount": trade.amount,
            "asset_symbol": trade.asset_symbol,
            "jurisdiction": trade.counterparty_jurisdiction,
            "risk_score": trade.counterparty_risk_score,
            "assigned_rail": result.get("assigned_rail"),
            "fee": result.get("estimated_fee_usd", 0.0),
            "approved": result.get("compliance_approved", False),
            "rejection_reason": result.get("rejection_reason"),
            "vault_balance_after": self.collateral
        })

def trade_generator(env: simpy.Environment, sim: SettlementSimulation, num_trades: int = 100):
    assets = ["USD_CBDC", "AED_CBDC", "USDC", "UNAPPROVED_TOKEN"]
    jurisdictions = ["AE", "UK", "US", "HIGH_RISK_JURISDICTION"]
    
    for i in range(num_trades):
        # Transaction arrival interval (1 to 5 simulated minutes)
        yield env.timeout(random.uniform(1.0, 5.0))

        # Synthetic trade generation
        amount = round(random.uniform(50_000, 1_500_000), 2)
        asset = random.choices(assets, weights=[0.4, 0.3, 0.2, 0.1])[0]
        jurisdiction = random.choices(jurisdictions, weights=[0.4, 0.3, 0.2, 0.1])[0]
        risk_score = round(random.uniform(0.05, 0.95), 2)
        is_whitelisted = (asset != "UNAPPROVED_TOKEN")
        priority = "URGENT" if random.random() > 0.6 else "STANDARD"

        trade = TradeIntent(
            trade_id=f"TR-SIM-{i+1:04d}",
            counterparty_id=f"CPTY_{random.randint(100, 999)}",
            counterparty_jurisdiction=jurisdiction,
            counterparty_risk_score=risk_score,
            amount=amount,
            asset_symbol=asset,
            is_whitelisted_asset=is_whitelisted,
            priority=priority
        )

        sim.process_trade(trade)

def run_simulation(num_trades: int = 100, starting_collateral: float = 20_000_000.0) -> pd.DataFrame:
    env = simpy.Environment()
    sim = SettlementSimulation(env, initial_collateral=starting_collateral)
    env.process(trade_generator(env, sim, num_trades=num_trades))
    env.run()
    return pd.DataFrame(sim.records)

if __name__ == "__main__":
    print("Running Intraday Settlement Simulation (100 synthetic trades)...")
    df = run_simulation(num_trades=100)
    print(f"\nSimulation complete. Processed {len(df)} transactions.")
    print("\nSettlement Outcome Distribution:")
    print(df["approved"].value_counts(normalize=True).rename({True: "Approved", False: "Halted / Rejected"}))
    print(f"\nFinal Vault Balance: ${df['vault_balance_after'].iloc[-1]:,.2f}")
    df.to_csv("simulation_results.csv", index=False)
    print("Metrics written to simulation_results.csv")