// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title IChambaEscrow
 * @notice Interface for the Chamba Escrow contract
 * @dev Escrow system for human-executed tasks with partial releases
 */
interface IChambaEscrow {
    // ============ Enums ============

    enum EscrowStatus {
        Active,      // Funds locked, awaiting work
        Completed,   // All funds released to worker(s)
        Refunded,    // Funds returned to depositor
        Cancelled    // Escrow cancelled before work started
    }

    // ============ Structs ============

    struct Escrow {
        bytes32 taskId;          // External task identifier
        address depositor;       // Who funded the escrow
        address beneficiary;     // Primary intended recipient (worker)
        address token;           // ERC20 token address
        uint256 amount;          // Total escrowed amount
        uint256 released;        // Amount already released
        uint256 createdAt;       // Timestamp of creation
        uint256 timeout;         // Timestamp after which refund is allowed
        EscrowStatus status;     // Current status
    }

    struct Release {
        address recipient;       // Who received the release
        uint256 amount;          // Amount released
        uint256 timestamp;       // When released
        string reason;           // Reason for release (e.g., "submission", "approval")
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

    event EscrowReleased(
        uint256 indexed escrowId,
        address indexed recipient,
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
        uint256 amount
    );

    event OperatorUpdated(
        address indexed operator,
        bool authorized
    );

    // ============ Functions ============

    /**
     * @notice Create a new escrow for a task
     * @param taskId External identifier for the task
     * @param beneficiary Primary intended recipient (worker)
     * @param token ERC20 token to escrow
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
     * @notice Release funds from escrow (partial or full)
     * @param escrowId The escrow to release from
     * @param recipient Who should receive the funds
     * @param amount Amount to release
     * @param reason Reason for the release
     */
    function releaseEscrow(
        uint256 escrowId,
        address recipient,
        uint256 amount,
        string calldata reason
    ) external;

    /**
     * @notice Refund remaining funds to depositor
     * @dev Only allowed after timeout or by depositor before work starts
     * @param escrowId The escrow to refund
     */
    function refundEscrow(uint256 escrowId) external;

    /**
     * @notice Cancel escrow before any releases (full refund)
     * @param escrowId The escrow to cancel
     */
    function cancelEscrow(uint256 escrowId) external;

    /**
     * @notice Get escrow details
     * @param escrowId The escrow ID
     * @return escrow The escrow struct
     */
    function getEscrow(uint256 escrowId) external view returns (Escrow memory escrow);

    /**
     * @notice Get release history for an escrow
     * @param escrowId The escrow ID
     * @return releases Array of release records
     */
    function getReleases(uint256 escrowId) external view returns (Release[] memory releases);

    /**
     * @notice Get remaining balance in escrow
     * @param escrowId The escrow ID
     * @return remaining The amount still available
     */
    function getRemaining(uint256 escrowId) external view returns (uint256 remaining);

    /**
     * @notice Check if address is authorized operator
     * @param operator Address to check
     * @return isOperator True if authorized
     */
    function isOperator(address operator) external view returns (bool isOperator);
}
