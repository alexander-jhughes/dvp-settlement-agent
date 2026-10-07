import json
from pathlib import Path
from web3 import Web3

# 1. Connect to local Anvil node
RPC_URL = "http://127.0.0.1:8545"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise ConnectionError("Failed to connect to local Anvil RPC node at 127.0.0.1:8545")

# 2. Deployment Details & Keys
VAULT_ADDRESS = Web3.to_checksum_address("0x5FbDB2315678afecb367f032d93F642f64180aa3")

# Anvil Default Accounts
BANK_A_ADDRESS = Web3.to_checksum_address("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
BANK_A_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

OVERSIGHT_ADDRESS = Web3.to_checksum_address("0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
OVERSIGHT_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"

BANK_B_ADDRESS = Web3.to_checksum_address("0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC")

# 3. Load Contract ABI from Forge artifacts
artifact_path = Path("contracts/out/OffExchangeVault.sol/OffExchangeVault.json")
with open(artifact_path, "r") as f:
    artifact = json.load(f)

vault_contract = w3.eth.contract(address=VAULT_ADDRESS, abi=artifact["abi"])


def seed_vault_collateral(amount: int, asset: str = "USD_CBDC"):
    """Seeds participant collateral into the vault."""
    asset_bytes = Web3.to_bytes(text=asset).ljust(32, b"\0")
    tx = vault_contract.functions.depositCollateral(asset_bytes, amount).build_transaction({
        "from": BANK_A_ADDRESS,
        "nonce": w3.eth.get_transaction_count(BANK_A_ADDRESS),
        "gas": 200000,
        "gasPrice": w3.eth.gas_price
    })
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=BANK_A_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[OnChain] Seeded ${amount:,.2f} collateral into vault for Bank A.")


def settle_onchain(trade_id: str, amount: int, asset: str = "USD_CBDC", rail: str = "UNIFIED_CBDC_RAIL"):
    """Settles trade on-chain via the authorized Oversight Agent signature."""
    trade_bytes = Web3.to_bytes(text=trade_id).ljust(32, b"\0")
    asset_bytes = Web3.to_bytes(text=asset).ljust(32, b"\0")
    rail_bytes = Web3.to_bytes(text=rail).ljust(32, b"\0")

    tx = vault_contract.functions.executeSettlement(
        trade_bytes,
        BANK_A_ADDRESS,
        BANK_B_ADDRESS,
        asset_bytes,
        amount,
        rail_bytes
    ).build_transaction({
        "from": OVERSIGHT_ADDRESS,
        "nonce": w3.eth.get_transaction_count(OVERSIGHT_ADDRESS),
        "gas": 300000,
        "gasPrice": w3.eth.gas_price
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=OVERSIGHT_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print(f"[OnChain] Atomic DvP Settlement Confirmed in Block #{receipt.blockNumber}")
    print(f"[OnChain] Transaction Hash: {tx_hash.hex()}")
    return tx_hash.hex()


def query_balances(asset: str = "USD_CBDC"):
    """Queries on-chain balances for verification."""
    asset_bytes = Web3.to_bytes(text=asset).ljust(32, b"\0")
    bal_a = vault_contract.functions.balances(BANK_A_ADDRESS, asset_bytes).call()
    bal_b = vault_contract.functions.balances(BANK_B_ADDRESS, asset_bytes).call()
    print(f"[OnChain Balance] Bank A: ${bal_a:,.2f} | Bank B: ${bal_b:,.2f}")
    return bal_a, bal_b


if __name__ == "__main__":
    print("Testing On-Chain Bridge Execution...")
    seed_vault_collateral(5_000_000)
    query_balances()
    settle_onchain(trade_id="TR-ONCHAIN-001", amount=1_500_000)
    query_balances()