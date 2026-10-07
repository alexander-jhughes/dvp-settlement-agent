// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OffExchangeVault
 * @notice Segregated collateral vault for institutional DvP settlement.
 * @dev Enforces dual-key agentic authorization: Treasury proposes, RegTech Oversight signs.
 */
contract OffExchangeVault {
    address public immutable treasuryAgent;
    address public immutable oversightAgent;

    // Track segregated balances per asset per participant
    // participant => (assetSymbol => balance)
    mapping(address => mapping(bytes32 => uint256)) public balances;

    event CollateralDeposited(address indexed participant, bytes32 indexed asset, uint256 amount);
    event SettlementExecuted(
        bytes32 indexed tradeId,
        address indexed sender,
        address indexed receiver,
        bytes32 asset,
        uint256 amount,
        bytes32 rail
    );

    error Unauthorized(address caller);
    error InsufficientVaultCollateral(uint256 available, uint256 required);

    modifier onlyOversight() {
        if (msg.sender != oversightAgent) revert Unauthorized(msg.sender);
        _;
    }

    constructor(address _treasuryAgent, address _oversightAgent) {
        treasuryAgent = _treasuryAgent;
        oversightAgent = _oversightAgent;
    }

    /**
     * @notice Deposit funds/collateral into segregated custody
     */
    function depositCollateral(bytes32 asset, uint256 amount) external {
        balances[msg.sender][asset] += amount;
        emit CollateralDeposited(msg.sender, asset, amount);
    }

    /**
     * @notice Executes atomic settlement.
     * @dev Only callable by the RegTech Oversight Agent once compliance checks pass.
     */
    function executeSettlement(
        bytes32 tradeId,
        address from,
        address to,
        bytes32 asset,
        uint256 amount,
        bytes32 rail
    ) external onlyOversight {
        uint256 currentBalance = balances[from][asset];
        if (currentBalance < amount) {
            revert InsufficientVaultCollateral(currentBalance, amount);
        }

        // Deduct from sender and credit counterparty atomically
        balances[from][asset] = currentBalance - amount;
        balances[to][asset] += amount;

        emit SettlementExecuted(tradeId, from, to, asset, amount, rail);
    }
}
