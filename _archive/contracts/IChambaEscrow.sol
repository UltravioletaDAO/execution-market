// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/**
 * @title IChambaEscrow
 * @notice Interface for the Chamba Escrow contract
 * @dev Secure escrow system for human-executed tasks with:
 *      - Enforced beneficiary-only releases
 *      - Minimum lock period for ALL exits (refund AND cancel)
 *      - Full dispute mechanism (only after timeout)
 *      - Per-depositor operators (not global)
 *      - Per-depositor taskId namespace (prevents squatting)
 *      - Token whitelist support
 *      - Fee-on-transfer token compatibility
 *      - Paginated release history
 */
interface IChambaEscrow {
    // ============ Enums ============

    enum EscrowStatus {
        Active,      // Funds locked, awaiting work
        Completed,   // All funds released to beneficiary
        Refunded,    // Funds returned to depositor (after dispute period)
        Cancelled,   // Escrow cancelled (with beneficiary consent or before acceptance)
        Disputed     // Under dispute review
    }

    enum DisputeStatus {
        None,        // No dispute
        Pending,     // Dispute filed, awaiting resolution
        ResolvedForBeneficiary,  // Beneficiary won
        ResolvedForDepositor     // Depositor won
    }

    // ============ Structs ============

    struct Escrow {
        bytes32 taskId;           // External task identifier
        address depositor;        // Who funded the escrow
        address beneficiary;      // Worker who will receive payment
        address token;            // ERC20 token address
        uint256 amount;           // Total escrowed amount (actual received)
        uint256 released;         // Amount already released
        uint256 createdAt;        // Timestamp of creation
        uint256 acceptedAt;       // Timestamp when beneficiary accepted (0 if not accepted)
        uint256 timeoutDuration;  // Duration in seconds for timeout (from accept)
        uint256 timeout;          // Computed deadline: acceptedAt + timeoutDuration (0 until accepted)
        EscrowStatus status;      // Current status
        DisputeStatus dispute;    // Dispute status
    }

    struct Release {
        uint256 amount;           // Amount released
        uint256 timestamp;        // When released
        string reason;            // Reason for release (e.g., "milestone_1", "completion")
    }

    struct DisputeInfo {
        address initiator;        // Who filed the dispute
        uint256 filedAt;          // When dispute was filed
        string reason;            // Dispute reason
        string resolution;        // Resolution details (set by arbitrator)
    }

    // ============ Events ============

    event EscrowCreated(
        uint256 indexed escrowId,
        bytes32 indexed taskId,
        address indexed depositor,
        address beneficiary,
        address token,
        uint256 amount,
        uint256 timeout
    );

    event EscrowAccepted(
        uint256 indexed escrowId,
        address indexed beneficiary,
        uint256 timestamp
    );

    event EscrowReleased(
        uint256 indexed escrowId,
        address indexed beneficiary,
        uint256 amount,
        uint256 totalReleased,
        string reason
    );

    event EscrowRefunded(
        uint256 indexed escrowId,
        address indexed depositor,
        uint256 amount
    );

    event EscrowCancelled(
        uint256 indexed escrowId,
        address indexed depositor,
        uint256 amount,
        bool beneficiaryConsent
    );

    event CancellationConsent(
        uint256 indexed escrowId,
        address indexed beneficiary
    );

    event DisputeFiled(
        uint256 indexed escrowId,
        address indexed initiator,
        string reason
    );

    event DisputeResolved(
        uint256 indexed escrowId,
        DisputeStatus resolution,
        string details
    );

    event OperatorUpdated(
        address indexed depositor,
        address indexed operator,
        bool authorized
    );

    event ArbitratorUpdated(
        address indexed arbitrator,
        bool authorized
    );

    event TokenWhitelistUpdated(
        address indexed token,
        bool allowed
    );

    // ============ Core Functions ============

    /**
     * @notice Create a new escrow for a task
     * @param taskId External identifier for the task (namespaced by depositor)
     * @param beneficiary Worker who will receive payment
     * @param token ERC20 token to escrow (must be whitelisted)
     * @param amount Amount to escrow (must have prior approval)
     * @param timeout Duration in seconds until refund is allowed
     * @return escrowId The ID of the created escrow
     */
    function createEscrow(
        bytes32 taskId,
        address beneficiary,
        address token,
        uint256 amount,
        uint256 timeout
    ) external returns (uint256 escrowId);

    /**
     * @notice Beneficiary accepts the escrow task
     * @dev Must be called by beneficiary to start the lock period
     * @param escrowId The escrow to accept
     */
    function acceptEscrow(uint256 escrowId) external;

    /**
     * @notice Release funds to beneficiary (partial or full)
     * @dev Only depositor or approved operator can release. Always pays beneficiary.
     * @param escrowId The escrow to release from
     * @param amount Amount to release
     * @param reason Reason for the release (max 200 bytes)
     */
    function releaseEscrow(
        uint256 escrowId,
        uint256 amount,
        string calldata reason
    ) external;

    /**
     * @notice Refund remaining funds to depositor
     * @dev Only allowed after MIN_LOCK_PERIOD, timeout, AND dispute window
     * @param escrowId The escrow to refund
     */
    function refundEscrow(uint256 escrowId) external;

    /**
     * @notice Cancel escrow (requires beneficiary consent after acceptance)
     * @dev Only allowed after MIN_LOCK_PERIOD
     * @param escrowId The escrow to cancel
     */
    function cancelEscrow(uint256 escrowId) external;

    /**
     * @notice Beneficiary consents to cancellation
     * @param escrowId The escrow to consent cancellation for
     */
    function consentToCancellation(uint256 escrowId) external;

    // ============ Dispute Functions ============

    /**
     * @notice File a dispute (only during dispute window after timeout)
     * @param escrowId The escrow to dispute
     * @param reason Reason for the dispute (max 200 bytes)
     */
    function fileDispute(uint256 escrowId, string calldata reason) external;

    /**
     * @notice Resolve a dispute (arbitrator only)
     * @param escrowId The escrow with dispute
     * @param forBeneficiary True to release to beneficiary, false to refund depositor
     * @param details Resolution details (max 200 bytes)
     */
    function resolveDispute(
        uint256 escrowId,
        bool forBeneficiary,
        string calldata details
    ) external;

    // ============ View Functions ============

    /**
     * @notice Get escrow details
     * @param escrowId The escrow ID
     * @return escrow The escrow struct
     */
    function getEscrow(uint256 escrowId) external view returns (Escrow memory escrow);

    /**
     * @notice Get release history for an escrow (all releases)
     * @param escrowId The escrow ID
     * @return releases Array of release records
     */
    function getReleases(uint256 escrowId) external view returns (Release[] memory releases);

    /**
     * @notice Get paginated release history for an escrow
     * @param escrowId The escrow ID
     * @param offset Starting index
     * @param limit Maximum items to return
     * @return releases Slice of release records
     */
    function getReleasesSlice(
        uint256 escrowId,
        uint256 offset,
        uint256 limit
    ) external view returns (Release[] memory releases);

    /**
     * @notice Get total number of releases for pagination
     * @param escrowId The escrow ID
     * @return count Number of releases
     */
    function getReleasesCount(uint256 escrowId) external view returns (uint256 count);

    /**
     * @notice Get dispute info for an escrow
     * @param escrowId The escrow ID
     * @return info The dispute information
     */
    function getDisputeInfo(uint256 escrowId) external view returns (DisputeInfo memory info);

    /**
     * @notice Get remaining balance in escrow
     * @param escrowId The escrow ID
     * @return remaining The amount still available
     */
    function getRemaining(uint256 escrowId) external view returns (uint256 remaining);

    /**
     * @notice Get escrow ID by taskId scoped to a depositor
     * @param depositor Depositor namespace
     * @param taskId External identifier for the task
     * @return escrowId Escrow ID or 0 if not found
     */
    function getEscrowByTask(address depositor, bytes32 taskId) external view returns (uint256 escrowId);

    /**
     * @notice Get the next escrow ID that will be assigned
     * @return nextId The next escrow ID
     */
    function nextEscrowId() external view returns (uint256 nextId);

    /**
     * @notice Check if refund is currently allowed
     * @param escrowId The escrow ID
     * @return True if refund is allowed
     */
    function canRefund(uint256 escrowId) external view returns (bool);

    /**
     * @notice Check if cancel is currently allowed
     * @param escrowId The escrow ID
     * @return True if cancel is allowed
     */
    function canCancel(uint256 escrowId) external view returns (bool);

    /**
     * @notice Check if dispute window is currently open
     * @param escrowId The escrow ID
     * @return True if dispute window is open
     */
    function isDisputeWindowOpen(uint256 escrowId) external view returns (bool);

    /**
     * @notice Get total locked amount for a token
     * @param token Token address
     * @return amount Total locked amount
     */
    function getTotalLocked(address token) external view returns (uint256 amount);

    // ============ Operator Functions ============

    /**
     * @notice DEPRECATED: Use isOperatorFor(depositor, operator) instead
     * @dev Kept for interface compatibility, always returns false
     * @param operator Address to check (ignored)
     * @return Always returns false
     */
    function isOperator(address operator) external pure returns (bool);

    /**
     * @notice Check if operator is authorized for a specific depositor
     * @param depositor The depositor who may have authorized the operator
     * @param operator Address to check
     * @return True if authorized
     */
    function isOperatorFor(address depositor, address operator) external view returns (bool);

    /**
     * @notice Set operator for the caller (depositor sets their own operators)
     * @param operator Address to authorize/deauthorize
     * @param authorized True to authorize, false to revoke
     */
    function setMyOperator(address operator, bool authorized) external;

    // ============ Token/Arbitrator Functions ============

    /**
     * @notice Check if token is whitelisted
     * @param token Token address to check
     * @return True if whitelisted
     */
    function isTokenWhitelisted(address token) external view returns (bool);

    /**
     * @notice Check if address is authorized arbitrator
     * @param arbitrator Address to check
     * @return True if authorized
     */
    function isArbitrator(address arbitrator) external view returns (bool);
}
