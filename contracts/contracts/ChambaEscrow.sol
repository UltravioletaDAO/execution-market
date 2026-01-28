// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {IChambaEscrow} from "./interfaces/IChambaEscrow.sol";

/**
 * @title ChambaEscrow
 * @notice Escrow contract for human-executed tasks with partial release support
 * @dev Supports USDC and other ERC20 tokens with configurable release schedules
 *
 * Key features:
 * - Partial releases (e.g., 30% on submission, 70% on approval)
 * - Timeout-based refund mechanism
 * - Operator system for authorized release managers
 * - Full release history tracking
 * - Emergency pause capability
 *
 * Audited: 2026-01-27 by Ultravioleta DAO
 * @custom:security-contact ultravioletadao@gmail.com
 */
contract ChambaEscrow is IChambaEscrow, ReentrancyGuard, Ownable, Pausable {
    using SafeERC20 for IERC20;

    // ============ Constants ============

    /// @notice Contract version
    string public constant VERSION = "1.0.0";

    // ============ State Variables ============

    /// @notice Counter for escrow IDs
    uint256 private _nextEscrowId;

    /// @notice Minimum timeout duration (1 hour)
    uint256 public constant MIN_TIMEOUT = 1 hours;

    /// @notice Maximum timeout duration (365 days)
    uint256 public constant MAX_TIMEOUT = 365 days;

    /// @notice Mapping of escrow ID to escrow data
    mapping(uint256 => Escrow) private _escrows;

    /// @notice Mapping of escrow ID to release history
    mapping(uint256 => Release[]) private _releases;

    /// @notice Mapping of task ID to escrow ID (for lookups)
    mapping(bytes32 => uint256) private _taskToEscrow;

    /// @notice Authorized operators who can release funds
    mapping(address => bool) private _operators;

    /// @notice Total locked balance per token (for emergency withdraw safety)
    mapping(address => uint256) private _totalLocked;

    // ============ Constructor ============

    constructor() Ownable(msg.sender) {
        _nextEscrowId = 1; // Start from 1, 0 reserved for "not found"
    }

    // ============ Modifiers ============

    modifier onlyDepositorOrOperator(uint256 escrowId) {
        Escrow storage escrow = _escrows[escrowId];
        require(
            msg.sender == escrow.depositor || _operators[msg.sender],
            "ChambaEscrow: not authorized"
        );
        _;
    }

    modifier escrowExists(uint256 escrowId) {
        require(_escrows[escrowId].createdAt != 0, "ChambaEscrow: escrow does not exist");
        _;
    }

    modifier escrowActive(uint256 escrowId) {
        require(
            _escrows[escrowId].status == EscrowStatus.Active,
            "ChambaEscrow: escrow not active"
        );
        _;
    }

    // ============ External Functions ============

    /**
     * @inheritdoc IChambaEscrow
     */
    function createEscrow(
        bytes32 taskId,
        address beneficiary,
        address token,
        uint256 amount,
        uint256 timeout
    ) external nonReentrant whenNotPaused returns (uint256 escrowId) {
        // Validations
        require(taskId != bytes32(0), "ChambaEscrow: invalid task ID");
        require(beneficiary != address(0), "ChambaEscrow: invalid beneficiary");
        require(token != address(0), "ChambaEscrow: invalid token");
        require(amount > 0, "ChambaEscrow: amount must be positive");
        require(
            timeout >= MIN_TIMEOUT && timeout <= MAX_TIMEOUT,
            "ChambaEscrow: invalid timeout"
        );
        require(
            _taskToEscrow[taskId] == 0,
            "ChambaEscrow: task already has escrow"
        );

        // Generate escrow ID
        escrowId = _nextEscrowId++;

        // Calculate absolute timeout
        uint256 timeoutTimestamp = block.timestamp + timeout;

        // Create escrow
        _escrows[escrowId] = Escrow({
            taskId: taskId,
            depositor: msg.sender,
            beneficiary: beneficiary,
            token: token,
            amount: amount,
            released: 0,
            createdAt: block.timestamp,
            timeout: timeoutTimestamp,
            status: EscrowStatus.Active
        });

        // Map task to escrow
        _taskToEscrow[taskId] = escrowId;

        // Track total locked
        _totalLocked[token] += amount;

        // Transfer tokens from depositor
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        emit EscrowCreated(
            escrowId,
            taskId,
            msg.sender,
            beneficiary,
            token,
            amount,
            timeoutTimestamp
        );
    }

    /**
     * @inheritdoc IChambaEscrow
     */
    function releaseEscrow(
        uint256 escrowId,
        address recipient,
        uint256 amount,
        string calldata reason
    )
        external
        nonReentrant
        whenNotPaused
        escrowExists(escrowId)
        escrowActive(escrowId)
        onlyDepositorOrOperator(escrowId)
    {
        Escrow storage escrow = _escrows[escrowId];

        // Validations
        require(recipient != address(0), "ChambaEscrow: invalid recipient");
        require(amount > 0, "ChambaEscrow: amount must be positive");

        uint256 remaining = escrow.amount - escrow.released;
        require(amount <= remaining, "ChambaEscrow: insufficient balance");

        // Update state
        escrow.released += amount;
        _totalLocked[escrow.token] -= amount;

        // Record release
        _releases[escrowId].push(Release({
            recipient: recipient,
            amount: amount,
            timestamp: block.timestamp,
            reason: reason
        }));

        // Check if fully released
        if (escrow.released == escrow.amount) {
            escrow.status = EscrowStatus.Completed;
        }

        // Transfer tokens
        IERC20(escrow.token).safeTransfer(recipient, amount);

        emit EscrowReleased(
            escrowId,
            recipient,
            amount,
            escrow.released,
            reason
        );
    }

    /**
     * @inheritdoc IChambaEscrow
     */
    function refundEscrow(uint256 escrowId)
        external
        nonReentrant
        escrowExists(escrowId)
        escrowActive(escrowId)
    {
        Escrow storage escrow = _escrows[escrowId];

        // Only depositor or operator can refund
        require(
            msg.sender == escrow.depositor || _operators[msg.sender],
            "ChambaEscrow: not authorized"
        );

        // Check timeout if work has started (releases > 0)
        if (escrow.released > 0) {
            require(
                block.timestamp >= escrow.timeout,
                "ChambaEscrow: timeout not reached"
            );
        }

        uint256 remaining = escrow.amount - escrow.released;
        require(remaining > 0, "ChambaEscrow: nothing to refund");

        // Update state
        escrow.status = EscrowStatus.Refunded;
        _totalLocked[escrow.token] -= remaining;

        // Transfer remaining funds back to depositor
        IERC20(escrow.token).safeTransfer(escrow.depositor, remaining);

        emit EscrowRefunded(escrowId, escrow.depositor, remaining);
    }

    /**
     * @inheritdoc IChambaEscrow
     */
    function cancelEscrow(uint256 escrowId)
        external
        nonReentrant
        escrowExists(escrowId)
        escrowActive(escrowId)
    {
        Escrow storage escrow = _escrows[escrowId];

        // Only depositor can cancel
        require(
            msg.sender == escrow.depositor,
            "ChambaEscrow: only depositor can cancel"
        );

        // Can only cancel if no releases have been made
        require(
            escrow.released == 0,
            "ChambaEscrow: cannot cancel after release"
        );

        // Update state
        escrow.status = EscrowStatus.Cancelled;
        _totalLocked[escrow.token] -= escrow.amount;

        // Transfer full amount back to depositor
        IERC20(escrow.token).safeTransfer(escrow.depositor, escrow.amount);

        emit EscrowCancelled(escrowId, escrow.depositor, escrow.amount);
    }

    // ============ View Functions ============

    /**
     * @inheritdoc IChambaEscrow
     */
    function getEscrow(uint256 escrowId)
        external
        view
        escrowExists(escrowId)
        returns (Escrow memory)
    {
        return _escrows[escrowId];
    }

    /**
     * @inheritdoc IChambaEscrow
     */
    function getReleases(uint256 escrowId)
        external
        view
        escrowExists(escrowId)
        returns (Release[] memory)
    {
        return _releases[escrowId];
    }

    /**
     * @inheritdoc IChambaEscrow
     */
    function getRemaining(uint256 escrowId)
        external
        view
        escrowExists(escrowId)
        returns (uint256)
    {
        Escrow storage escrow = _escrows[escrowId];
        if (escrow.status != EscrowStatus.Active) {
            return 0;
        }
        return escrow.amount - escrow.released;
    }

    /**
     * @inheritdoc IChambaEscrow
     */
    function isOperator(address operator) external view returns (bool) {
        return _operators[operator];
    }

    /**
     * @notice Get escrow ID by task ID
     * @param taskId The task identifier
     * @return escrowId The associated escrow ID (0 if not found)
     */
    function getEscrowByTask(bytes32 taskId) external view returns (uint256) {
        return _taskToEscrow[taskId];
    }

    /**
     * @notice Get the next escrow ID that will be assigned
     * @return The next escrow ID
     */
    function nextEscrowId() external view returns (uint256) {
        return _nextEscrowId;
    }

    /**
     * @notice Check if timeout has been reached
     * @param escrowId The escrow to check
     * @return True if timeout reached
     */
    function isTimedOut(uint256 escrowId)
        external
        view
        escrowExists(escrowId)
        returns (bool)
    {
        return block.timestamp >= _escrows[escrowId].timeout;
    }

    /**
     * @notice Get total locked balance for a token
     * @param token Token address to check
     * @return Total amount locked in active escrows
     */
    function getTotalLocked(address token) external view returns (uint256) {
        return _totalLocked[token];
    }

    // ============ Admin Functions ============

    /**
     * @notice Set operator authorization
     * @param operator Address to authorize/deauthorize
     * @param authorized Whether to authorize
     */
    function setOperator(address operator, bool authorized) external onlyOwner {
        require(operator != address(0), "ChambaEscrow: invalid operator");
        _operators[operator] = authorized;
        emit OperatorUpdated(operator, authorized);
    }

    /**
     * @notice Batch set operators
     * @param operators Array of operator addresses
     * @param authorized Whether to authorize
     */
    function setOperatorsBatch(
        address[] calldata operators,
        bool authorized
    ) external onlyOwner {
        for (uint256 i = 0; i < operators.length; i++) {
            require(operators[i] != address(0), "ChambaEscrow: invalid operator");
            _operators[operators[i]] = authorized;
            emit OperatorUpdated(operators[i], authorized);
        }
    }

    // ============ Emergency Functions ============

    /**
     * @notice Pause the contract
     * @dev Only owner can pause. Prevents new escrows and releases.
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause the contract
     * @dev Only owner can unpause.
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice Emergency withdrawal of stuck tokens (not escrowed funds)
     * @dev Only for tokens accidentally sent to contract, not for escrowed funds.
     *      Cannot withdraw more than the surplus (balance - locked).
     * @param token Token to withdraw
     * @param to Recipient address
     * @param amount Amount to withdraw
     */
    function emergencyWithdraw(
        address token,
        address to,
        uint256 amount
    ) external onlyOwner {
        require(to != address(0), "ChambaEscrow: invalid recipient");

        // Calculate surplus (tokens not in escrow)
        uint256 balance = IERC20(token).balanceOf(address(this));
        uint256 locked = _totalLocked[token];
        uint256 surplus = balance > locked ? balance - locked : 0;

        require(amount <= surplus, "ChambaEscrow: cannot withdraw escrowed funds");

        IERC20(token).safeTransfer(to, amount);
    }
}
