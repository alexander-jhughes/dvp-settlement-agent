// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {OffExchangeVault} from "../src/OffExchangeVault.sol";

contract OffExchangeVaultTest is Test {
    OffExchangeVault public vault;

    address public treasury = address(0x111);
    address public oversight = address(0x222);
    address public bankA = address(0xAAA);
    address public bankB = address(0xBBB);

    bytes32 public constant ASSET_USD = bytes32("USD_CBDC");
    bytes32 public constant RAIL_CBDC = bytes32("UNIFIED_CBDC_RAIL");
    bytes32 public constant TRADE_ID = bytes32("TR-001");

    function setUp() public {
        vault = new OffExchangeVault(treasury, oversight);

        // Bank A deposits $1,000,000 collateral
        vm.prank(bankA);
        vault.depositCollateral(ASSET_USD, 1_000_000);
    }

    function test_InitialDeposit() public view {
        assertEq(vault.balances(bankA, ASSET_USD), 1_000_000);
        assertEq(vault.balances(bankB, ASSET_USD), 0);
    }

    function test_SettlementByOversight() public {
        // Oversight agent triggers the settlement
        vm.prank(oversight);
        vault.executeSettlement(TRADE_ID, bankA, bankB, ASSET_USD, 250_000, RAIL_CBDC);

        assertEq(vault.balances(bankA, ASSET_USD), 750_000);
        assertEq(vault.balances(bankB, ASSET_USD), 250_000);
    }

    function test_RevertWhen_CallerNotOversight() public {
        // Treasury tries to settle directly without oversight clearance -> must revert
        vm.prank(treasury);
        vm.expectRevert(abi.encodeWithSelector(OffExchangeVault.Unauthorized.selector, treasury));
        vault.executeSettlement(TRADE_ID, bankA, bankB, ASSET_USD, 250_000, RAIL_CBDC);
    }
}