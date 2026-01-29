// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Ownable2Step, Ownable} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {IChambaEscrow} from "./interfaces/IChambaEscrow.sol";

/**
 * @title ChambaEscrow
 * @notice Secure escrow contract for human-executed tasks
 * @author Ultravioleta DAO
 * @dev Production-ready escrow with comprehensive security features:
 *
 * SECURITY MODEL:
 * - MIN_LOCK_PERIOD applies to ALL exits (refund AND cancel)
 * - Releases ALWAYS go to beneficiary (no arbitrary recipients)
 * - Operators are scoped PER DEPOSITOR (not global)
 * - Disputes only after timeout (prevents griefing freeze)
 * - String lengths capped at 200 bytes (prevents storage bloat)
 * - Paginated release history (prevents DoS on reads)
 *
 * PAUSE POLICY:
 * - Paused: createEscrow, releaseEscrow, acceptEscrow, fileDispute blocked
 * - Not paused: refundEscrow, cancelEscrow (escape hatches for users)
 *
 * @custom:security-contact ultravioletadao@gmail.com
 */
contract ChambaEscrow is IChambaEscrow, ReentrancyGuard, Ownable2Step, Pausable {
    using SafeERC20 for IERC20;

    // ============ Custom Errors (Gas Optimized) ============

    error InvalidTaskId();
    error InvalidBeneficiary();
    error SelfBeneficiary();
    error InvalidAmount();
    error InvalidTimeout();
    error TaskAlreadyHasEscrow();
    error TokenNotContract();
    error TokenNotWhitelisted();
    error ZeroTokensReceived();
    error EscrowNotFound();
    error EscrowNotActive();
    error NotAuthorized();
    error OnlyBeneficiary();
    error OnlyDepositor();
    error OnlyArbitrator();
    error AlreadyAccepted();
    error NotAcceptedYet();
    error MaxReleasesReached();
    error InsufficientBalance();
    error NothingToRefund();
    error MinLockPeriodNotReached();
    error TimeoutNotReached();
    error DisputePending();
    error CannotCancelAfterRelease();
    error BeneficiaryConsentRequired();
    error DisputeAlreadyExists();
    error DisputeWindowClosed();
    error DisputeWindowNotOpen();
    error NoPendingDispute();
    error NothingToDistribute();
    error InvalidOperator();
    error InvalidArbitrator();
    error InvalidToken();
    error InvalidRecipient();
    error BatchTooLarge();
    error CannotWithdrawEscrowed();
    error StringTooLong();
    error InvalidPaginationRange();

    // ============ Constants ============

    string public constant VERSION = "1.4.0";

    uint256 public constant MIN_TIMEOUT = 1 hours;
    uint256 public constant MAX_TIMEOUT = 365 days;

    /// @notice Minimum lock period before ANY exit (refund or cancel)
    /// @dev Applies even before acceptance - protects workers who see task and start offchain
    uint256 public constant MIN_LOCK_PERIOD = 24 hours;

    uint256 public constant DISPUTE_WINDOW = 48 hours;
    uint256 public constant MAX_RELEASES_PER_ESCROW = 100;
    uint256 public constant MAX_BATCH_SIZE = 50;
    uint256 public constant MAX_STRING_LENGTH = 200;

    // ============ State Variables ============

    uint256 private _nextEscrowId;

    mapping(uint256 => Escrow) private _escrows;
    mapping(uint256 => Release[]) private _releases;
    mapping(uint256 => DisputeInfo) private _disputes;

    /// @notice TaskId scoped by depositor to prevent squatting
    /// @dev depositor => taskId => escrowId
    mapping(address => mapping(bytes32 => uint256)) private _taskToEscrow;

    /// @notice Operators scoped by depositor (depositor => operator => authorized)
    /// @dev FIX B: Operators are no longer global, reducing blast radius
    mapping(address => mapping(address => bool)) private _depositorOperators;

    mapping(address => bool) private _arbitrators;
    mapping(address => bool) private _whitelistedTokens;
    mapping(address => uint256) private _totalLocked;
    mapping(uint256 => bool) private _cancellationConsent;

    // ============ Constructor ============

    constructor() Ownable(msg.sender) {
        _nextEscrowId = 1;
    }

    // ============ Modifiers ============

    /// @notice FIX B: Operator check scoped to depositor, not global
    /// @dev Includes escrowExists check to prevent footgun if used without escrowExists modifier
    modifier onlyDepositorOrOperator(uint256 escrowId) {
        if (_escrows[escrowId].createdAt == 0) revert EscrowNotFound();
        Escrow storage escrow = _escrows[escrowId];
        bool _isDepositor = msg.sender == escrow.depositor;
        bool _isOperatorForDepositor = _depositorOperators[escrow.depositor][msg.sender];
        if (!_isDepositor && !_isOperatorForDepositor) revert NotAuthorized();
        _;
    }

    modifier onlyBeneficiary(uint256 escrowId) {
        if (msg.sender != _escrows[escrowId].beneficiary) revert OnlyBeneficiary();
        _;
    }

    modifier onlyArbitrator() {
        if (!_arbitrators[msg.sender]) revert OnlyArbitrator();
        _;
    }

    modifier escrowExists(uint256 escrowId) {
        if (_escrows[escrowId].createdAt == 0) revert EscrowNotFound();
        _;
    }

    modifier escrowActive(uint256 escrowId) {
        if (_escrows[escrowId].status != EscrowStatus.Active) revert EscrowNotActive();
        _;
    }

    modifier tokenWhitelisted(address token) {
        if (!_whitelistedTokens[token]) revert TokenNotWhitelisted();
        _;
    }

    modifier validStringLength(string calldata str) {
        if (bytes(str).length > MAX_STRING_LENGTH) revert StringTooLong();
        _;
    }

    // ============ External Functions ============

    /// @inheritdoc IChambaEscrow
    function createEscrow(
        bytes32 taskId,
        address beneficiary,
        address token,
        uint256 amount,
        uint256 timeout
    )
        external
        nonReentrant
        whenNotPaused
        tokenWhitelisted(token)
        returns (uint256 escrowId)
    {
        if (taskId == bytes32(0)) revert InvalidTaskId();
        if (beneficiary == address(0)) revert InvalidBeneficiary();
        if (beneficiary == msg.sender) revert SelfBeneficiary();
        if (amount == 0) revert InvalidAmount();
        if (timeout < MIN_TIMEOUT || timeout > MAX_TIMEOUT) revert InvalidTimeout();
        // Namespace by depositor prevents taskId squatting
        if (_taskToEscrow[msg.sender][taskId] != 0) revert TaskAlreadyHasEscrow();
        if (token.code.length == 0) revert TokenNotContract();

        escrowId = _nextEscrowId++;

        // Balance-checked transfer for fee-on-transfer tokens
        uint256 balanceBefore = IERC20(token).balanceOf(address(this));
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
        uint256 actualReceived = IERC20(token).balanceOf(address(this)) - balanceBefore;
        if (actualReceived == 0) revert ZeroTokensReceived();

        // FIX: Store duration, timeout computed at acceptance
        // We emit estimated timeout for UX but actual deadline is set on accept
        uint256 estimatedTimeout = block.timestamp + timeout;

        _escrows[escrowId] = Escrow({
            taskId: taskId,
            depositor: msg.sender,
            beneficiary: beneficiary,
            token: token,
            amount: actualReceived,
            released: 0,
            createdAt: block.timestamp,
            acceptedAt: 0,
            timeoutDuration: timeout,  // Store the duration
            timeout: 0,                // Will be set on accept
            status: EscrowStatus.Active,
            dispute: DisputeStatus.None
        });

        _taskToEscrow[msg.sender][taskId] = escrowId;
        _totalLocked[token] += actualReceived;

        emit EscrowCreated(
            escrowId,
            taskId,
            msg.sender,
            beneficiary,
            token,
            actualReceived,
            estimatedTimeout  // For UX - actual deadline set on accept
        );
    }

    /// @inheritdoc IChambaEscrow
    /// @dev FIX F: Added whenNotPaused
    /// @dev FIX v1.4: Timeout now anchored to acceptedAt, not createdAt
    function acceptEscrow(uint256 escrowId)
        external
        nonReentrant
        whenNotPaused
        escrowExists(escrowId)
        escrowActive(escrowId)
        onlyBeneficiary(escrowId)
    {
        Escrow storage escrow = _escrows[escrowId];
        if (escrow.acceptedAt != 0) revert AlreadyAccepted();

        escrow.acceptedAt = block.timestamp;
        // FIX: Timeout deadline computed from acceptance, not creation
        // This ensures worker has full timeoutDuration to complete work
        escrow.timeout = block.timestamp + escrow.timeoutDuration;

        emit EscrowAccepted(escrowId, msg.sender, block.timestamp);
    }

    /// @inheritdoc IChambaEscrow
    /// @dev FIX D: String length validation added
    /// @dev onlyDepositorOrOperator already includes escrowExists check
    function releaseEscrow(
        uint256 escrowId,
        uint256 amount,
        string calldata reason
    )
        external
        nonReentrant
        whenNotPaused
        escrowActive(escrowId)
        onlyDepositorOrOperator(escrowId)
        validStringLength(reason)
    {
        Escrow storage escrow = _escrows[escrowId];

        if (escrow.acceptedAt == 0) revert NotAcceptedYet();
        if (amount == 0) revert InvalidAmount();
        if (_releases[escrowId].length >= MAX_RELEASES_PER_ESCROW) revert MaxReleasesReached();

        uint256 remaining = escrow.amount - escrow.released;
        if (amount > remaining) revert InsufficientBalance();

        escrow.released += amount;
        _totalLocked[escrow.token] -= amount;

        _releases[escrowId].push(Release({
            amount: amount,
            timestamp: block.timestamp,
            reason: reason
        }));

        if (escrow.released == escrow.amount) {
            escrow.status = EscrowStatus.Completed;
            delete _taskToEscrow[escrow.depositor][escrow.taskId];
        }

        // ALWAYS transfer to beneficiary
        IERC20(escrow.token).safeTransfer(escrow.beneficiary, amount);

        emit EscrowReleased(
            escrowId,
            escrow.beneficiary,
            amount,
            escrow.released,
            reason
        );
    }

    /// @inheritdoc IChambaEscrow
    /// @dev Escape hatch - NOT paused so users can exit during emergency
    /// @dev FIX v1.4: MIN_LOCK_PERIOD anchored to max(createdAt, acceptedAt)
    function refundEscrow(uint256 escrowId)
        external
        nonReentrant
        escrowExists(escrowId)
        escrowActive(escrowId)
    {
        Escrow storage escrow = _escrows[escrowId];

        if (msg.sender != escrow.depositor) revert OnlyDepositor();

        // FIX v1.4: MIN_LOCK_PERIOD relative to the later of creation or acceptance
        // This ensures worker always has full protection period after accepting
        uint256 lockStart = escrow.acceptedAt > escrow.createdAt
            ? escrow.acceptedAt
            : escrow.createdAt;
        if (block.timestamp < lockStart + MIN_LOCK_PERIOD) {
            revert MinLockPeriodNotReached();
        }

        // If accepted, require timeout + dispute window
        // Note: timeout is now computed at acceptedAt, so this check is fair
        if (escrow.acceptedAt > 0) {
            if (block.timestamp < escrow.timeout + DISPUTE_WINDOW) {
                revert TimeoutNotReached();
            }
        }

        if (escrow.dispute == DisputeStatus.Pending) revert DisputePending();

        uint256 remaining = escrow.amount - escrow.released;
        if (remaining == 0) revert NothingToRefund();

        escrow.status = EscrowStatus.Refunded;
        _totalLocked[escrow.token] -= remaining;
        delete _taskToEscrow[escrow.depositor][escrow.taskId];

        IERC20(escrow.token).safeTransfer(escrow.depositor, remaining);

        emit EscrowRefunded(escrowId, escrow.depositor, remaining);
    }

    /// @inheritdoc IChambaEscrow
    /// @dev FIX A: MIN_LOCK_PERIOD now applies to cancel too
    /// @dev FIX v1.4: MIN_LOCK_PERIOD anchored to max(createdAt, acceptedAt)
    /// @dev Escape hatch - NOT paused so users can exit during emergency
    function cancelEscrow(uint256 escrowId)
        external
        nonReentrant
        escrowExists(escrowId)
        escrowActive(escrowId)
    {
        Escrow storage escrow = _escrows[escrowId];

        if (msg.sender != escrow.depositor) revert OnlyDepositor();
        if (escrow.released != 0) revert CannotCancelAfterRelease();

        // FIX v1.4: MIN_LOCK_PERIOD relative to the later of creation or acceptance
        uint256 lockStart = escrow.acceptedAt > escrow.createdAt
            ? escrow.acceptedAt
            : escrow.createdAt;
        if (block.timestamp < lockStart + MIN_LOCK_PERIOD) {
            revert MinLockPeriodNotReached();
        }

        // If accepted, require beneficiary consent
        if (escrow.acceptedAt > 0) {
            if (!_cancellationConsent[escrowId]) {
                revert BeneficiaryConsentRequired();
            }
        }

        escrow.status = EscrowStatus.Cancelled;
        _totalLocked[escrow.token] -= escrow.amount;
        delete _taskToEscrow[escrow.depositor][escrow.taskId];
        delete _cancellationConsent[escrowId];

        IERC20(escrow.token).safeTransfer(escrow.depositor, escrow.amount);

        emit EscrowCancelled(escrowId, escrow.depositor, escrow.amount, escrow.acceptedAt > 0);
    }

    /// @inheritdoc IChambaEscrow
    /// @dev FIX v1.4: Removed whenNotPaused - this is an escape hatch
    /// @dev Beneficiary can always consent to cancellation, even during pause
    function consentToCancellation(uint256 escrowId)
        external
        escrowExists(escrowId)
        escrowActive(escrowId)
        onlyBeneficiary(escrowId)
    {
        _cancellationConsent[escrowId] = true;
        emit CancellationConsent(escrowId, msg.sender);
    }

    /// @inheritdoc IChambaEscrow
    /// @dev FIX C: Dispute only after timeout (prevents early griefing freeze)
    /// @dev FIX D: String length validation
    /// @dev FIX F: Added whenNotPaused
    function fileDispute(uint256 escrowId, string calldata reason)
        external
        nonReentrant
        whenNotPaused
        escrowExists(escrowId)
        escrowActive(escrowId)
        validStringLength(reason)
    {
        Escrow storage escrow = _escrows[escrowId];

        bool isParty = msg.sender == escrow.beneficiary || msg.sender == escrow.depositor;
        if (!isParty) revert NotAuthorized();

        if (escrow.acceptedAt == 0) revert NotAcceptedYet();
        if (escrow.dispute != DisputeStatus.None) revert DisputeAlreadyExists();

        // FIX C: Dispute only after timeout to prevent early griefing
        // This prevents beneficiary from freezing escrow at minute 1
        if (block.timestamp < escrow.timeout) revert DisputeWindowNotOpen();
        if (block.timestamp > escrow.timeout + DISPUTE_WINDOW) revert DisputeWindowClosed();

        escrow.dispute = DisputeStatus.Pending;
        escrow.status = EscrowStatus.Disputed;

        _disputes[escrowId] = DisputeInfo({
            initiator: msg.sender,
            filedAt: block.timestamp,
            reason: reason,
            resolution: ""
        });

        emit DisputeFiled(escrowId, msg.sender, reason);
    }

    /// @inheritdoc IChambaEscrow
    /// @dev FIX D: String length validation for details
    function resolveDispute(
        uint256 escrowId,
        bool forBeneficiary,
        string calldata details
    )
        external
        nonReentrant
        onlyArbitrator
        escrowExists(escrowId)
        validStringLength(details)
    {
        Escrow storage escrow = _escrows[escrowId];

        if (escrow.dispute != DisputeStatus.Pending) revert NoPendingDispute();

        uint256 remaining = escrow.amount - escrow.released;
        if (remaining == 0) revert NothingToDistribute();

        if (forBeneficiary) {
            escrow.dispute = DisputeStatus.ResolvedForBeneficiary;
            escrow.status = EscrowStatus.Completed;
            // FIX v1.4: Maintain invariant Completed => released == amount
            escrow.released = escrow.amount;
        } else {
            escrow.dispute = DisputeStatus.ResolvedForDepositor;
            escrow.status = EscrowStatus.Refunded;
        }

        _disputes[escrowId].resolution = details;
        _totalLocked[escrow.token] -= remaining;
        delete _taskToEscrow[escrow.depositor][escrow.taskId];

        address recipient = forBeneficiary ? escrow.beneficiary : escrow.depositor;
        IERC20(escrow.token).safeTransfer(recipient, remaining);

        emit DisputeResolved(escrowId, escrow.dispute, details);
    }

    // ============ View Functions ============

    /// @inheritdoc IChambaEscrow
    function getEscrow(uint256 escrowId)
        external
        view
        escrowExists(escrowId)
        returns (Escrow memory)
    {
        return _escrows[escrowId];
    }

    /// @inheritdoc IChambaEscrow
    function getReleases(uint256 escrowId)
        external
        view
        escrowExists(escrowId)
        returns (Release[] memory)
    {
        return _releases[escrowId];
    }

    /// @notice FIX E: Paginated release history to prevent DoS
    /// @dev FIX v1.4: Overflow-safe calculation
    /// @param escrowId The escrow ID
    /// @param offset Starting index
    /// @param limit Maximum items to return
    /// @return releases Slice of release records
    function getReleasesSlice(uint256 escrowId, uint256 offset, uint256 limit)
        external
        view
        escrowExists(escrowId)
        returns (Release[] memory releases)
    {
        Release[] storage arr = _releases[escrowId];
        uint256 len = arr.length;

        // FIX v1.4: Avoid offset + limit overflow
        if (offset >= len) {
            return new Release[](0);
        }
        uint256 remaining = len - offset;
        uint256 size = limit < remaining ? limit : remaining;

        releases = new Release[](size);
        for (uint256 i = 0; i < size; i++) {
            releases[i] = arr[offset + i];
        }
    }

    /// @notice Get total number of releases for pagination
    function getReleasesCount(uint256 escrowId) external view escrowExists(escrowId) returns (uint256) {
        return _releases[escrowId].length;
    }

    /// @inheritdoc IChambaEscrow
    function getDisputeInfo(uint256 escrowId)
        external
        view
        escrowExists(escrowId)
        returns (DisputeInfo memory)
    {
        return _disputes[escrowId];
    }

    /// @inheritdoc IChambaEscrow
    function getRemaining(uint256 escrowId)
        external
        view
        escrowExists(escrowId)
        returns (uint256)
    {
        Escrow storage escrow = _escrows[escrowId];
        if (escrow.status != EscrowStatus.Active && escrow.status != EscrowStatus.Disputed) {
            return 0;
        }
        return escrow.amount - escrow.released;
    }

    /// @inheritdoc IChambaEscrow
    /// @dev DEPRECATED: Use isOperatorFor(depositor, operator) instead
    /// @dev Kept for interface compatibility, always returns false
    function isOperator(address) external pure returns (bool) {
        return false;
    }

    /// @notice Check if operator is authorized for a specific depositor
    /// @dev FIX B: New function for per-depositor operator check
    function isOperatorFor(address depositor, address operator) external view returns (bool) {
        return _depositorOperators[depositor][operator];
    }

    /// @inheritdoc IChambaEscrow
    function isTokenWhitelisted(address token) external view returns (bool) {
        return _whitelistedTokens[token];
    }

    /// @inheritdoc IChambaEscrow
    function isArbitrator(address arbitrator) external view returns (bool) {
        return _arbitrators[arbitrator];
    }

    /// @notice Get escrow ID by taskId scoped to a depositor
    /// @param depositor Depositor namespace
    /// @param taskId External identifier for the task
    /// @return escrowId Escrow ID or 0 if not found
    function getEscrowByTask(address depositor, bytes32 taskId) external view returns (uint256) {
        return _taskToEscrow[depositor][taskId];
    }

    function nextEscrowId() external view returns (uint256) {
        return _nextEscrowId;
    }

    /// @dev FIX v1.4: MIN_LOCK_PERIOD anchored to max(createdAt, acceptedAt)
    function canRefund(uint256 escrowId) external view escrowExists(escrowId) returns (bool) {
        Escrow storage escrow = _escrows[escrowId];

        if (escrow.status != EscrowStatus.Active) return false;
        if (escrow.dispute == DisputeStatus.Pending) return false;

        // FIX v1.4: Lock start is the later of creation or acceptance
        uint256 lockStart = escrow.acceptedAt > escrow.createdAt
            ? escrow.acceptedAt
            : escrow.createdAt;
        if (block.timestamp < lockStart + MIN_LOCK_PERIOD) return false;

        if (escrow.acceptedAt > 0) {
            return block.timestamp >= escrow.timeout + DISPUTE_WINDOW;
        }

        return true;
    }

    /// @notice Check if cancel is currently allowed
    /// @dev FIX v1.4: MIN_LOCK_PERIOD anchored to max(createdAt, acceptedAt)
    function canCancel(uint256 escrowId) external view escrowExists(escrowId) returns (bool) {
        Escrow storage escrow = _escrows[escrowId];

        if (escrow.status != EscrowStatus.Active) return false;
        if (escrow.released != 0) return false;

        // FIX v1.4: Lock start is the later of creation or acceptance
        uint256 lockStart = escrow.acceptedAt > escrow.createdAt
            ? escrow.acceptedAt
            : escrow.createdAt;
        if (block.timestamp < lockStart + MIN_LOCK_PERIOD) return false;

        if (escrow.acceptedAt > 0) {
            return _cancellationConsent[escrowId];
        }

        return true;
    }

    function isDisputeWindowOpen(uint256 escrowId) external view escrowExists(escrowId) returns (bool) {
        Escrow storage escrow = _escrows[escrowId];
        if (escrow.acceptedAt == 0) return false;
        // FIX C: Window is only open AFTER timeout
        return block.timestamp >= escrow.timeout &&
               block.timestamp <= escrow.timeout + DISPUTE_WINDOW;
    }

    function getTotalLocked(address token) external view returns (uint256) {
        return _totalLocked[token];
    }

    // ============ Admin Functions ============

    /// @notice FIX B: Set operator for the caller (depositor sets their own operators)
    /// @dev Depositors manage their own operators, owner CANNOT set for others (trust-minimized)
    function setMyOperator(address operator, bool authorized) external {
        if (operator == address(0)) revert InvalidOperator();
        _depositorOperators[msg.sender][operator] = authorized;
        emit OperatorUpdated(msg.sender, operator, authorized);
    }

    // NOTE: setOperatorFor (admin override) was intentionally removed to maintain
    // trust-minimized design. Owner cannot authorize operators for depositors.

    function setArbitrator(address arbitrator, bool authorized) external onlyOwner {
        if (arbitrator == address(0)) revert InvalidArbitrator();
        _arbitrators[arbitrator] = authorized;
        emit ArbitratorUpdated(arbitrator, authorized);
    }

    function setTokenWhitelist(address token, bool allowed) external onlyOwner {
        if (token == address(0)) revert InvalidToken();
        if (token.code.length == 0) revert TokenNotContract();
        _whitelistedTokens[token] = allowed;
        emit TokenWhitelistUpdated(token, allowed);
    }

    function setTokenWhitelistBatch(
        address[] calldata tokens,
        bool allowed
    ) external onlyOwner {
        if (tokens.length > MAX_BATCH_SIZE) revert BatchTooLarge();

        for (uint256 i = 0; i < tokens.length; i++) {
            if (tokens[i] == address(0)) revert InvalidToken();
            if (tokens[i].code.length == 0) revert TokenNotContract();
            _whitelistedTokens[tokens[i]] = allowed;
            emit TokenWhitelistUpdated(tokens[i], allowed);
        }
    }

    // ============ Emergency Functions ============

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /// @dev Requires NOT paused - intentional, so owner can't extract during emergency pause
    function emergencyWithdraw(
        address token,
        address to,
        uint256 amount
    ) external onlyOwner whenNotPaused {
        if (to == address(0)) revert InvalidRecipient();

        uint256 balance = IERC20(token).balanceOf(address(this));
        uint256 locked = _totalLocked[token];
        uint256 surplus = balance > locked ? balance - locked : 0;

        if (amount > surplus) revert CannotWithdrawEscrowed();

        IERC20(token).safeTransfer(to, amount);
    }
}
