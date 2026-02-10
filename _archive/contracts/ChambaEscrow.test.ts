import { expect } from "chai";
import { ethers } from "hardhat";
import { time, loadFixture } from "@nomicfoundation/hardhat-toolbox/network-helpers";
import { ChambaEscrow, MockERC20 } from "../typechain-types";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";

describe("ChambaEscrow", function () {
  // Constants matching contract
  const TASK_ID = ethers.encodeBytes32String("task-001");
  const ESCROW_AMOUNT = ethers.parseUnits("100", 6); // 100 USDC
  const ONE_WEEK = 7 * 24 * 60 * 60;
  const ONE_HOUR = 60 * 60;
  const ONE_DAY = 24 * ONE_HOUR;
  const MIN_LOCK_PERIOD = ONE_DAY; // 24 hours
  const DISPUTE_WINDOW = 2 * ONE_DAY; // 48 hours

  // Fixture for deployment
  async function deployFixture() {
    const [owner, depositor, worker, operator, arbitrator, other] = await ethers.getSigners();

    // Deploy mock USDC
    const MockERC20 = await ethers.getContractFactory("MockERC20");
    const usdc = await MockERC20.deploy("USD Coin", "USDC", 6);

    // Deploy ChambaEscrow
    const ChambaEscrow = await ethers.getContractFactory("ChambaEscrow");
    const escrow = await ChambaEscrow.deploy();

    // Whitelist USDC
    await escrow.connect(owner).setTokenWhitelist(await usdc.getAddress(), true);

    // Set arbitrator
    await escrow.connect(owner).setArbitrator(arbitrator.address, true);

    // Mint USDC to depositor
    await usdc.mint(depositor.address, ethers.parseUnits("10000", 6));

    // Approve escrow contract
    await usdc.connect(depositor).approve(await escrow.getAddress(), ethers.MaxUint256);

    return { escrow, usdc, owner, depositor, worker, operator, arbitrator, other };
  }

  describe("Deployment", function () {
    it("Should set the right owner", async function () {
      const { escrow, owner } = await loadFixture(deployFixture);
      expect(await escrow.owner()).to.equal(owner.address);
    });

    it("Should start with escrow ID 1", async function () {
      const { escrow } = await loadFixture(deployFixture);
      expect(await escrow.nextEscrowId()).to.equal(1);
    });

    it("Should have correct version", async function () {
      const { escrow } = await loadFixture(deployFixture);
      expect(await escrow.VERSION()).to.equal("1.4.0");
    });
  });

  describe("Create Escrow", function () {
    it("Should create escrow successfully", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      await expect(
        escrow.connect(depositor).createEscrow(
          TASK_ID,
          worker.address,
          await usdc.getAddress(),
          ESCROW_AMOUNT,
          ONE_WEEK
        )
      ).to.emit(escrow, "EscrowCreated");

      const escrowData = await escrow.getEscrow(1);
      expect(escrowData.taskId).to.equal(TASK_ID);
      expect(escrowData.depositor).to.equal(depositor.address);
      expect(escrowData.beneficiary).to.equal(worker.address);
      expect(escrowData.amount).to.equal(ESCROW_AMOUNT);
      expect(escrowData.released).to.equal(0);
      expect(escrowData.status).to.equal(0); // Active
      expect(escrowData.acceptedAt).to.equal(0); // Not accepted yet
    });

    it("Should transfer tokens to escrow", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      const balanceBefore = await usdc.balanceOf(depositor.address);

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      expect(await usdc.balanceOf(await escrow.getAddress())).to.equal(ESCROW_AMOUNT);
      expect(await usdc.balanceOf(depositor.address)).to.equal(balanceBefore - ESCROW_AMOUNT);
    });

    it("Should revert with invalid task ID", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      await expect(
        escrow.connect(depositor).createEscrow(
          ethers.ZeroHash,
          worker.address,
          await usdc.getAddress(),
          ESCROW_AMOUNT,
          ONE_WEEK
        )
      ).to.be.revertedWithCustomError(escrow, "InvalidTaskId");
    });

    it("Should revert with invalid timeout", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      await expect(
        escrow.connect(depositor).createEscrow(
          TASK_ID,
          worker.address,
          await usdc.getAddress(),
          ESCROW_AMOUNT,
          60 // Less than MIN_TIMEOUT (1 hour)
        )
      ).to.be.revertedWithCustomError(escrow, "InvalidTimeout");
    });

    it("Should revert with non-whitelisted token", async function () {
      const { escrow, depositor, worker, other } = await loadFixture(deployFixture);

      // Deploy another token (not whitelisted)
      const MockERC20 = await ethers.getContractFactory("MockERC20");
      const badToken = await MockERC20.deploy("Bad Token", "BAD", 18);

      await expect(
        escrow.connect(depositor).createEscrow(
          TASK_ID,
          worker.address,
          await badToken.getAddress(),
          ESCROW_AMOUNT,
          ONE_WEEK
        )
      ).to.be.revertedWithCustomError(escrow, "TokenNotWhitelisted");
    });

    it("Should revert if beneficiary is self", async function () {
      const { escrow, usdc, depositor } = await loadFixture(deployFixture);

      await expect(
        escrow.connect(depositor).createEscrow(
          TASK_ID,
          depositor.address, // Self as beneficiary
          await usdc.getAddress(),
          ESCROW_AMOUNT,
          ONE_WEEK
        )
      ).to.be.revertedWithCustomError(escrow, "SelfBeneficiary");
    });

    it("Should prevent duplicate task escrows", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      await expect(
        escrow.connect(depositor).createEscrow(
          TASK_ID, // Same task ID
          worker.address,
          await usdc.getAddress(),
          ESCROW_AMOUNT,
          ONE_WEEK
        )
      ).to.be.revertedWithCustomError(escrow, "TaskAlreadyHasEscrow");
    });
  });

  describe("Accept Escrow", function () {
    async function createEscrowFixture() {
      const fixture = await loadFixture(deployFixture);
      const { escrow, usdc, depositor, worker } = fixture;

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      return { ...fixture, escrowId: 1n };
    }

    it("Should allow beneficiary to accept", async function () {
      const { escrow, worker, escrowId } = await loadFixture(createEscrowFixture);

      await expect(escrow.connect(worker).acceptEscrow(escrowId))
        .to.emit(escrow, "EscrowAccepted")
        .withArgs(escrowId, worker.address, await time.latest() + 1);

      const escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.acceptedAt).to.be.gt(0);
    });

    it("Should revert if not beneficiary", async function () {
      const { escrow, depositor, escrowId } = await loadFixture(createEscrowFixture);

      await expect(
        escrow.connect(depositor).acceptEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "OnlyBeneficiary");
    });

    it("Should revert if already accepted", async function () {
      const { escrow, worker, escrowId } = await loadFixture(createEscrowFixture);

      await escrow.connect(worker).acceptEscrow(escrowId);

      await expect(
        escrow.connect(worker).acceptEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "AlreadyAccepted");
    });
  });

  describe("Release Escrow", function () {
    async function acceptedEscrowFixture() {
      const fixture = await loadFixture(deployFixture);
      const { escrow, usdc, depositor, worker } = fixture;

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      // Worker accepts
      await escrow.connect(worker).acceptEscrow(1);

      return { ...fixture, escrowId: 1n };
    }

    it("Should allow depositor to release funds to beneficiary", async function () {
      const { escrow, usdc, depositor, worker, escrowId } = await loadFixture(acceptedEscrowFixture);

      const releaseAmount = ethers.parseUnits("30", 6);

      await expect(
        escrow.connect(depositor).releaseEscrow(escrowId, releaseAmount, "submission")
      )
        .to.emit(escrow, "EscrowReleased")
        .withArgs(escrowId, worker.address, releaseAmount, releaseAmount, "submission");

      // Funds go to beneficiary (worker), not arbitrary address
      expect(await usdc.balanceOf(worker.address)).to.equal(releaseAmount);
    });

    it("Should revert if escrow not accepted yet", async function () {
      const fixture = await loadFixture(deployFixture);
      const { escrow, usdc, depositor, worker } = fixture;

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      // Try to release without acceptance
      await expect(
        escrow.connect(depositor).releaseEscrow(1, ethers.parseUnits("30", 6), "submission")
      ).to.be.revertedWithCustomError(escrow, "NotAcceptedYet");
    });

    it("Should support partial releases (30/70 pattern)", async function () {
      const { escrow, usdc, depositor, worker, escrowId } = await loadFixture(acceptedEscrowFixture);

      const submissionRelease = ethers.parseUnits("30", 6);
      const approvalRelease = ethers.parseUnits("70", 6);

      // First release: submission (30%)
      await escrow.connect(depositor).releaseEscrow(escrowId, submissionRelease, "submission");

      let escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.released).to.equal(submissionRelease);
      expect(escrowData.status).to.equal(0); // Still Active

      // Second release: approval (70%)
      await escrow.connect(depositor).releaseEscrow(escrowId, approvalRelease, "approval");

      escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.released).to.equal(ESCROW_AMOUNT);
      expect(escrowData.status).to.equal(1); // Completed

      // Check release history
      const releases = await escrow.getReleases(escrowId);
      expect(releases.length).to.equal(2);
      expect(releases[0].reason).to.equal("submission");
      expect(releases[1].reason).to.equal("approval");
    });

    it("Should allow depositor's operator to release funds", async function () {
      const { escrow, usdc, depositor, worker, operator, escrowId } = await loadFixture(acceptedEscrowFixture);

      // Depositor authorizes their own operator
      await escrow.connect(depositor).setMyOperator(operator.address, true);

      const releaseAmount = ethers.parseUnits("50", 6);

      await expect(
        escrow.connect(operator).releaseEscrow(escrowId, releaseAmount, "operator release")
      ).to.emit(escrow, "EscrowReleased");

      expect(await usdc.balanceOf(worker.address)).to.equal(releaseAmount);
    });

    it("Should revert if operator not authorized by depositor", async function () {
      const { escrow, owner, operator, escrowId } = await loadFixture(acceptedEscrowFixture);

      // Owner sets operator for themselves (not for depositor)
      await escrow.connect(owner).setMyOperator(operator.address, true);

      // Operator tries to release (but not authorized for this escrow's depositor)
      await expect(
        escrow.connect(operator).releaseEscrow(escrowId, ESCROW_AMOUNT, "unauthorized")
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
    });

    it("Should revert if unauthorized", async function () {
      const { escrow, other, escrowId } = await loadFixture(acceptedEscrowFixture);

      await expect(
        escrow.connect(other).releaseEscrow(escrowId, ESCROW_AMOUNT, "unauthorized")
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
    });

    it("Should revert if amount exceeds remaining", async function () {
      const { escrow, depositor, escrowId } = await loadFixture(acceptedEscrowFixture);

      const excessAmount = ESCROW_AMOUNT + ethers.parseUnits("1", 6);

      await expect(
        escrow.connect(depositor).releaseEscrow(escrowId, excessAmount, "too much")
      ).to.be.revertedWithCustomError(escrow, "InsufficientBalance");
    });

    it("Should revert if reason string too long", async function () {
      const { escrow, depositor, escrowId } = await loadFixture(acceptedEscrowFixture);

      const longReason = "x".repeat(201); // Over 200 bytes

      await expect(
        escrow.connect(depositor).releaseEscrow(escrowId, ethers.parseUnits("10", 6), longReason)
      ).to.be.revertedWithCustomError(escrow, "StringTooLong");
    });
  });

  describe("Refund Escrow", function () {
    async function createEscrowFixture() {
      const fixture = await loadFixture(deployFixture);
      const { escrow, usdc, depositor, worker } = fixture;

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      return { ...fixture, escrowId: 1n };
    }

    it("Should require MIN_LOCK_PERIOD even without acceptance", async function () {
      const { escrow, depositor, escrowId } = await loadFixture(createEscrowFixture);

      // Try to refund immediately
      await expect(
        escrow.connect(depositor).refundEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "MinLockPeriodNotReached");

      // Fast forward past MIN_LOCK_PERIOD
      await time.increase(MIN_LOCK_PERIOD + 1);

      // Now should work
      await expect(escrow.connect(depositor).refundEscrow(escrowId))
        .to.emit(escrow, "EscrowRefunded");
    });

    it("Should require timeout + dispute window after acceptance", async function () {
      const { escrow, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      // Worker accepts
      await escrow.connect(worker).acceptEscrow(escrowId);

      // Fast forward past MIN_LOCK_PERIOD (not enough)
      await time.increase(MIN_LOCK_PERIOD + 1);

      await expect(
        escrow.connect(depositor).refundEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "TimeoutNotReached");

      // Fast forward past timeout + dispute window
      await time.increase(ONE_WEEK + DISPUTE_WINDOW);

      // Now should work
      await expect(escrow.connect(depositor).refundEscrow(escrowId))
        .to.emit(escrow, "EscrowRefunded");
    });

    it("Should refund remaining amount after partial releases", async function () {
      const { escrow, usdc, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      await escrow.connect(worker).acceptEscrow(escrowId);

      const releaseAmount = ethers.parseUnits("30", 6);
      await escrow.connect(depositor).releaseEscrow(escrowId, releaseAmount, "submission");

      await time.increase(ONE_WEEK + DISPUTE_WINDOW + 1);

      const balanceBefore = await usdc.balanceOf(depositor.address);
      const expectedRefund = ESCROW_AMOUNT - releaseAmount;

      await escrow.connect(depositor).refundEscrow(escrowId);

      expect(await usdc.balanceOf(depositor.address)).to.equal(balanceBefore + expectedRefund);
    });
  });

  describe("Cancel Escrow", function () {
    async function createEscrowFixture() {
      const fixture = await loadFixture(deployFixture);
      const { escrow, usdc, depositor, worker } = fixture;

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      return { ...fixture, escrowId: 1n };
    }

    it("Should require MIN_LOCK_PERIOD even before acceptance", async function () {
      const { escrow, depositor, escrowId } = await loadFixture(createEscrowFixture);

      // Try to cancel immediately
      await expect(
        escrow.connect(depositor).cancelEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "MinLockPeriodNotReached");

      // Fast forward past MIN_LOCK_PERIOD
      await time.increase(MIN_LOCK_PERIOD + 1);

      // Now should work
      await expect(escrow.connect(depositor).cancelEscrow(escrowId))
        .to.emit(escrow, "EscrowCancelled");
    });

    it("Should require beneficiary consent after acceptance", async function () {
      const { escrow, usdc, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      await escrow.connect(worker).acceptEscrow(escrowId);

      await time.increase(MIN_LOCK_PERIOD + 1);

      // Try to cancel without consent
      await expect(
        escrow.connect(depositor).cancelEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "BeneficiaryConsentRequired");

      // Beneficiary consents (should emit event)
      await expect(escrow.connect(worker).consentToCancellation(escrowId))
        .to.emit(escrow, "CancellationConsent")
        .withArgs(escrowId, worker.address);

      const balanceBefore = await usdc.balanceOf(depositor.address);

      // Now should work
      await expect(escrow.connect(depositor).cancelEscrow(escrowId))
        .to.emit(escrow, "EscrowCancelled")
        .withArgs(escrowId, depositor.address, ESCROW_AMOUNT, true);

      expect(await usdc.balanceOf(depositor.address)).to.equal(balanceBefore + ESCROW_AMOUNT);
    });

    it("Should prevent cancellation after release", async function () {
      const { escrow, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      await escrow.connect(worker).acceptEscrow(escrowId);

      await escrow.connect(depositor).releaseEscrow(
        escrowId,
        ethers.parseUnits("30", 6),
        "submission"
      );

      await time.increase(MIN_LOCK_PERIOD + 1);

      await expect(
        escrow.connect(depositor).cancelEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "CannotCancelAfterRelease");
    });

    it("Should only allow depositor to cancel", async function () {
      const { escrow, other, escrowId } = await loadFixture(createEscrowFixture);

      await time.increase(MIN_LOCK_PERIOD + 1);

      await expect(
        escrow.connect(other).cancelEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "OnlyDepositor");
    });
  });

  describe("Disputes", function () {
    async function acceptedEscrowFixture() {
      const fixture = await loadFixture(deployFixture);
      const { escrow, usdc, depositor, worker } = fixture;

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      await escrow.connect(worker).acceptEscrow(1);

      return { ...fixture, escrowId: 1n };
    }

    it("Should only allow dispute after timeout (not before)", async function () {
      const { escrow, worker, escrowId } = await loadFixture(acceptedEscrowFixture);

      // Try to file dispute before timeout
      await expect(
        escrow.connect(worker).fileDispute(escrowId, "Work completed but not paid")
      ).to.be.revertedWithCustomError(escrow, "DisputeWindowNotOpen");
    });

    it("Should allow dispute within dispute window after timeout", async function () {
      const { escrow, worker, escrowId } = await loadFixture(acceptedEscrowFixture);

      // Fast forward past timeout
      await time.increase(ONE_WEEK + 1);

      await expect(escrow.connect(worker).fileDispute(escrowId, "Work completed"))
        .to.emit(escrow, "DisputeFiled")
        .withArgs(escrowId, worker.address, "Work completed");

      const escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.status).to.equal(4); // Disputed
      expect(escrowData.dispute).to.equal(1); // Pending
    });

    it("Should reject dispute after dispute window closes", async function () {
      const { escrow, worker, escrowId } = await loadFixture(acceptedEscrowFixture);

      // Fast forward past timeout + dispute window
      await time.increase(ONE_WEEK + DISPUTE_WINDOW + 1);

      await expect(
        escrow.connect(worker).fileDispute(escrowId, "Too late")
      ).to.be.revertedWithCustomError(escrow, "DisputeWindowClosed");
    });

    it("Should allow arbitrator to resolve for beneficiary", async function () {
      const { escrow, usdc, worker, arbitrator, escrowId } = await loadFixture(acceptedEscrowFixture);

      await time.increase(ONE_WEEK + 1);
      await escrow.connect(worker).fileDispute(escrowId, "Work completed");

      await expect(
        escrow.connect(arbitrator).resolveDispute(escrowId, true, "Evidence supports worker")
      ).to.emit(escrow, "DisputeResolved");

      expect(await usdc.balanceOf(worker.address)).to.equal(ESCROW_AMOUNT);

      const escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.status).to.equal(1); // Completed
      expect(escrowData.dispute).to.equal(2); // ResolvedForBeneficiary
    });

    it("Should allow arbitrator to resolve for depositor", async function () {
      const { escrow, usdc, depositor, worker, arbitrator, escrowId } = await loadFixture(acceptedEscrowFixture);

      await time.increase(ONE_WEEK + 1);
      await escrow.connect(worker).fileDispute(escrowId, "Work completed");

      const balanceBefore = await usdc.balanceOf(depositor.address);

      await escrow.connect(arbitrator).resolveDispute(escrowId, false, "No evidence of work");

      expect(await usdc.balanceOf(depositor.address)).to.equal(balanceBefore + ESCROW_AMOUNT);

      const escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.status).to.equal(2); // Refunded
      expect(escrowData.dispute).to.equal(3); // ResolvedForDepositor
    });

    it("Should block refund during pending dispute", async function () {
      const { escrow, depositor, worker, escrowId } = await loadFixture(acceptedEscrowFixture);

      await time.increase(ONE_WEEK + 1);
      await escrow.connect(worker).fileDispute(escrowId, "Work completed");

      await expect(
        escrow.connect(depositor).refundEscrow(escrowId)
      ).to.be.revertedWithCustomError(escrow, "EscrowNotActive");
    });
  });

  describe("Per-Depositor Operators", function () {
    it("Should allow depositor to set their own operator", async function () {
      const { escrow, depositor, operator } = await loadFixture(deployFixture);

      await expect(escrow.connect(depositor).setMyOperator(operator.address, true))
        .to.emit(escrow, "OperatorUpdated")
        .withArgs(depositor.address, operator.address, true);

      expect(await escrow.isOperatorFor(depositor.address, operator.address)).to.be.true;
    });

    it("Should scope operators to depositor", async function () {
      const { escrow, usdc, depositor, worker, operator, other } = await loadFixture(deployFixture);

      // Depositor sets operator
      await escrow.connect(depositor).setMyOperator(operator.address, true);

      // Create escrow
      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );
      await escrow.connect(worker).acceptEscrow(1);

      // Operator can release for depositor
      await escrow.connect(operator).releaseEscrow(1, ethers.parseUnits("10", 6), "partial");

      // 'other' creates their own escrow
      await usdc.mint(other.address, ESCROW_AMOUNT);
      await usdc.connect(other).approve(await escrow.getAddress(), ESCROW_AMOUNT);
      await escrow.connect(other).createEscrow(
        ethers.encodeBytes32String("task-002"),
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );
      await escrow.connect(worker).acceptEscrow(2);

      // Same operator cannot release for 'other' (not their operator)
      await expect(
        escrow.connect(operator).releaseEscrow(2, ethers.parseUnits("10", 6), "should fail")
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
    });

    it("isOperator (deprecated) should return false", async function () {
      const { escrow, depositor, operator } = await loadFixture(deployFixture);

      await escrow.connect(depositor).setMyOperator(operator.address, true);

      // Deprecated function always returns false
      expect(await escrow.isOperator(operator.address)).to.be.false;

      // Use isOperatorFor instead
      expect(await escrow.isOperatorFor(depositor.address, operator.address)).to.be.true;
    });
  });

  describe("Pagination", function () {
    async function manyReleasesFixture() {
      const fixture = await loadFixture(deployFixture);
      const { escrow, usdc, depositor, worker } = fixture;

      const largeAmount = ethers.parseUnits("1000", 6);
      await usdc.mint(depositor.address, largeAmount);

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        largeAmount,
        ONE_WEEK
      );

      await escrow.connect(worker).acceptEscrow(1);

      // Make 10 releases
      for (let i = 0; i < 10; i++) {
        await escrow.connect(depositor).releaseEscrow(
          1,
          ethers.parseUnits("10", 6),
          `release-${i}`
        );
      }

      return { ...fixture, escrowId: 1n };
    }

    it("Should return correct release count", async function () {
      const { escrow, escrowId } = await loadFixture(manyReleasesFixture);

      expect(await escrow.getReleasesCount(escrowId)).to.equal(10);
    });

    it("Should return paginated releases", async function () {
      const { escrow, escrowId } = await loadFixture(manyReleasesFixture);

      // Get first 3
      const slice1 = await escrow.getReleasesSlice(escrowId, 0, 3);
      expect(slice1.length).to.equal(3);
      expect(slice1[0].reason).to.equal("release-0");
      expect(slice1[2].reason).to.equal("release-2");

      // Get next 3
      const slice2 = await escrow.getReleasesSlice(escrowId, 3, 3);
      expect(slice2.length).to.equal(3);
      expect(slice2[0].reason).to.equal("release-3");

      // Get last 4
      const slice3 = await escrow.getReleasesSlice(escrowId, 6, 10);
      expect(slice3.length).to.equal(4);
      expect(slice3[3].reason).to.equal("release-9");
    });
  });

  describe("View Functions", function () {
    async function createEscrowFixture() {
      const fixture = await loadFixture(deployFixture);
      const { escrow, usdc, depositor, worker } = fixture;

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      return { ...fixture, escrowId: 1n };
    }

    it("Should return correct remaining balance", async function () {
      const { escrow, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      expect(await escrow.getRemaining(escrowId)).to.equal(ESCROW_AMOUNT);

      await escrow.connect(worker).acceptEscrow(escrowId);

      const releaseAmount = ethers.parseUnits("40", 6);
      await escrow.connect(depositor).releaseEscrow(escrowId, releaseAmount, "partial");

      expect(await escrow.getRemaining(escrowId)).to.equal(ESCROW_AMOUNT - releaseAmount);
    });

    it("Should return escrow ID by task (namespaced by depositor)", async function () {
      const { escrow, depositor, escrowId } = await loadFixture(createEscrowFixture);

      expect(await escrow.getEscrowByTask(depositor.address, TASK_ID)).to.equal(escrowId);
    });

    it("canRefund should reflect current state", async function () {
      const { escrow, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      // Before MIN_LOCK_PERIOD
      expect(await escrow.canRefund(escrowId)).to.be.false;

      await time.increase(MIN_LOCK_PERIOD + 1);

      // After MIN_LOCK_PERIOD (not accepted)
      expect(await escrow.canRefund(escrowId)).to.be.true;

      await escrow.connect(worker).acceptEscrow(escrowId);

      // After acceptance, need timeout + dispute window
      expect(await escrow.canRefund(escrowId)).to.be.false;

      await time.increase(ONE_WEEK + DISPUTE_WINDOW);
      expect(await escrow.canRefund(escrowId)).to.be.true;
    });

    it("canCancel should reflect current state", async function () {
      const { escrow, worker, escrowId } = await loadFixture(createEscrowFixture);

      // Before MIN_LOCK_PERIOD
      expect(await escrow.canCancel(escrowId)).to.be.false;

      await time.increase(MIN_LOCK_PERIOD + 1);

      // After MIN_LOCK_PERIOD (not accepted)
      expect(await escrow.canCancel(escrowId)).to.be.true;

      await escrow.connect(worker).acceptEscrow(escrowId);

      // After acceptance, need consent
      expect(await escrow.canCancel(escrowId)).to.be.false;

      await escrow.connect(worker).consentToCancellation(escrowId);

      // v1.4.0: lock period is anchored to max(createdAt, acceptedAt),
      // so consent alone is not enough immediately after acceptance.
      expect(await escrow.canCancel(escrowId)).to.be.false;

      await time.increase(MIN_LOCK_PERIOD + 1);
      expect(await escrow.canCancel(escrowId)).to.be.true;
    });

    it("isDisputeWindowOpen should reflect timing", async function () {
      const { escrow, worker, escrowId } = await loadFixture(createEscrowFixture);

      // Not accepted
      expect(await escrow.isDisputeWindowOpen(escrowId)).to.be.false;

      await escrow.connect(worker).acceptEscrow(escrowId);

      // Accepted but before timeout
      expect(await escrow.isDisputeWindowOpen(escrowId)).to.be.false;

      await time.increase(ONE_WEEK + 1);

      // After timeout, within window
      expect(await escrow.isDisputeWindowOpen(escrowId)).to.be.true;

      await time.increase(DISPUTE_WINDOW);

      // After window closes
      expect(await escrow.isDisputeWindowOpen(escrowId)).to.be.false;
    });
  });

  describe("Edge Cases", function () {
    it("Should revert for non-existent escrow", async function () {
      const { escrow } = await loadFixture(deployFixture);

      await expect(escrow.getEscrow(999)).to.be.revertedWithCustomError(escrow, "EscrowNotFound");
    });

    it("Should handle multiple escrows correctly", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      const task1 = ethers.encodeBytes32String("task-001");
      const task2 = ethers.encodeBytes32String("task-002");
      const task3 = ethers.encodeBytes32String("task-003");

      await escrow.connect(depositor).createEscrow(
        task1,
        worker.address,
        await usdc.getAddress(),
        ethers.parseUnits("100", 6),
        ONE_WEEK
      );

      await escrow.connect(depositor).createEscrow(
        task2,
        worker.address,
        await usdc.getAddress(),
        ethers.parseUnits("200", 6),
        ONE_WEEK
      );

      await escrow.connect(depositor).createEscrow(
        task3,
        worker.address,
        await usdc.getAddress(),
        ethers.parseUnits("300", 6),
        ONE_WEEK
      );

      expect(await escrow.nextEscrowId()).to.equal(4);
      expect(await escrow.getEscrowByTask(depositor.address, task2)).to.equal(2);

      const escrow2 = await escrow.getEscrow(2);
      expect(escrow2.amount).to.equal(ethers.parseUnits("200", 6));
    });

    it("Should allow different depositors to use same taskId (namespace)", async function () {
      const { escrow, usdc, depositor, worker, other } = await loadFixture(deployFixture);

      // Same taskId for both depositors
      const sharedTaskId = ethers.encodeBytes32String("shared-task");

      // Depositor creates escrow with sharedTaskId
      await escrow.connect(depositor).createEscrow(
        sharedTaskId,
        worker.address,
        await usdc.getAddress(),
        ethers.parseUnits("100", 6),
        ONE_WEEK
      );

      // Other user creates escrow with SAME taskId (should work due to namespace)
      await usdc.mint(other.address, ethers.parseUnits("200", 6));
      await usdc.connect(other).approve(await escrow.getAddress(), ethers.MaxUint256);

      await escrow.connect(other).createEscrow(
        sharedTaskId,
        worker.address,
        await usdc.getAddress(),
        ethers.parseUnits("200", 6),
        ONE_WEEK
      );

      // Both escrows exist with different IDs
      expect(await escrow.getEscrowByTask(depositor.address, sharedTaskId)).to.equal(1);
      expect(await escrow.getEscrowByTask(other.address, sharedTaskId)).to.equal(2);

      // Different amounts confirm different escrows
      const escrow1 = await escrow.getEscrow(1);
      const escrow2 = await escrow.getEscrow(2);
      expect(escrow1.amount).to.equal(ethers.parseUnits("100", 6));
      expect(escrow2.amount).to.equal(ethers.parseUnits("200", 6));
    });
  });

  // ============ v1.4.0 Timing Fixes ============
  describe("v1.4.0 Timing Fixes", function () {
    it("Should anchor timeout to acceptedAt, not createdAt", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      // Create escrow with 1-week timeout
      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      // Fast forward 3 days (more than MIN_LOCK_PERIOD)
      await time.increase(3 * ONE_DAY);

      // Worker accepts NOW (late acceptance)
      await escrow.connect(worker).acceptEscrow(1);

      // Get escrow data - timeout should be calculated from acceptance
      const escrowData = await escrow.getEscrow(1);
      const acceptedAt = escrowData.acceptedAt;
      const timeout = escrowData.timeout;
      const timeoutDuration = escrowData.timeoutDuration;

      // Verify: timeout = acceptedAt + timeoutDuration (ONE_WEEK)
      expect(timeout).to.equal(acceptedAt + BigInt(ONE_WEEK));
      expect(timeoutDuration).to.equal(ONE_WEEK);

      // Try to refund - should fail because timeout hasn't passed
      // Even though 3 days passed since creation, timeout is fresh from acceptance
      await expect(
        escrow.connect(depositor).refundEscrow(1)
      ).to.be.revertedWithCustomError(escrow, "MinLockPeriodNotReached");

      // After lock period, timeout/dispute checks should become active
      await time.increase(MIN_LOCK_PERIOD + 1);
      await expect(
        escrow.connect(depositor).refundEscrow(1)
      ).to.be.revertedWithCustomError(escrow, "TimeoutNotReached");

      // Fast forward past timeout + dispute window (from acceptance)
      await time.increase(ONE_WEEK + DISPUTE_WINDOW + 1);

      // Now should succeed
      await expect(escrow.connect(depositor).refundEscrow(1))
        .to.emit(escrow, "EscrowRefunded");
    });

    it("Should anchor MIN_LOCK_PERIOD to acceptedAt when accepted late", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      // Create escrow
      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      // Fast forward 23 hours (almost MIN_LOCK_PERIOD from creation)
      await time.increase(23 * ONE_HOUR);

      // Worker accepts NOW
      await escrow.connect(worker).acceptEscrow(1);

      // Worker gives consent to cancel
      await escrow.connect(worker).consentToCancellation(1);

      // Try to cancel - should fail because MIN_LOCK_PERIOD from acceptance hasn't passed
      // In v1.3.0 this would succeed (24h from creation nearly passed)
      // In v1.4.0 this fails (24h from acceptance just started)
      await expect(
        escrow.connect(depositor).cancelEscrow(1)
      ).to.be.revertedWithCustomError(escrow, "MinLockPeriodNotReached");

      // Fast forward past MIN_LOCK_PERIOD from acceptance
      await time.increase(MIN_LOCK_PERIOD + 1);

      // Now should succeed
      await expect(escrow.connect(depositor).cancelEscrow(1))
        .to.emit(escrow, "EscrowCancelled");
    });

    it("Should allow dispute window even with late acceptance", async function () {
      const { escrow, usdc, depositor, worker } = await loadFixture(deployFixture);

      // Create escrow with 1-hour timeout
      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_HOUR
      );

      // Fast forward 2 hours (would be past old timeout)
      await time.increase(2 * ONE_HOUR);

      // Worker accepts NOW
      await escrow.connect(worker).acceptEscrow(1);

      // Dispute window should be open after timeout from acceptance
      expect(await escrow.isDisputeWindowOpen(1)).to.be.false;

      // Fast forward past new timeout (1 hour from acceptance)
      await time.increase(ONE_HOUR + 1);

      // Now dispute window should be open
      expect(await escrow.isDisputeWindowOpen(1)).to.be.true;

      // Worker can file dispute
      await expect(escrow.connect(worker).fileDispute(1, "Late but valid"))
        .to.emit(escrow, "DisputeFiled");
    });

    it("Should allow consentToCancellation even when paused (escape hatch)", async function () {
      const { escrow, usdc, depositor, worker, owner } = await loadFixture(deployFixture);

      // Create escrow
      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      // Worker accepts
      await escrow.connect(worker).acceptEscrow(1);

      // Owner pauses contract
      await escrow.connect(owner).pause();

      // Worker should still be able to consent to cancellation (escape hatch)
      await expect(escrow.connect(worker).consentToCancellation(1))
        .to.emit(escrow, "CancellationConsent");

      // Depositor should still be able to cancel (also escape hatch)
      await time.increase(MIN_LOCK_PERIOD + 1);
      await expect(escrow.connect(depositor).cancelEscrow(1))
        .to.emit(escrow, "EscrowCancelled");
    });

    it("Should update released when resolving dispute for beneficiary", async function () {
      const { escrow, usdc, depositor, worker, arbitrator } = await loadFixture(deployFixture);

      // Create escrow
      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_HOUR
      );

      // Worker accepts
      await escrow.connect(worker).acceptEscrow(1);

      // Fast forward past timeout
      await time.increase(ONE_HOUR + 1);

      // Worker files dispute
      await escrow.connect(worker).fileDispute(1, "Depositor won't pay");

      // Arbitrator resolves for beneficiary
      await escrow.connect(arbitrator).resolveDispute(1, true, "Work was done");

      // Verify: released should equal amount (invariant)
      const escrowData = await escrow.getEscrow(1);
      expect(escrowData.released).to.equal(escrowData.amount);
      expect(escrowData.status).to.equal(1); // Completed
    });
  });

  describe("Pause Functionality", function () {
    it("Should block createEscrow when paused", async function () {
      const { escrow, usdc, owner, depositor, worker } = await loadFixture(deployFixture);

      await escrow.connect(owner).pause();

      await expect(
        escrow.connect(depositor).createEscrow(
          TASK_ID,
          worker.address,
          await usdc.getAddress(),
          ESCROW_AMOUNT,
          ONE_WEEK
        )
      ).to.be.revertedWithCustomError(escrow, "EnforcedPause");
    });

    it("Should allow refundEscrow when paused (escape hatch)", async function () {
      const { escrow, usdc, owner, depositor, worker } = await loadFixture(deployFixture);

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      await time.increase(MIN_LOCK_PERIOD + 1);
      await escrow.connect(owner).pause();

      // Refund should still work (escape hatch)
      await expect(escrow.connect(depositor).refundEscrow(1))
        .to.emit(escrow, "EscrowRefunded");
    });

    it("Should allow cancelEscrow when paused (escape hatch)", async function () {
      const { escrow, usdc, owner, depositor, worker } = await loadFixture(deployFixture);

      await escrow.connect(depositor).createEscrow(
        TASK_ID,
        worker.address,
        await usdc.getAddress(),
        ESCROW_AMOUNT,
        ONE_WEEK
      );

      await time.increase(MIN_LOCK_PERIOD + 1);
      await escrow.connect(owner).pause();

      // Cancel should still work (escape hatch)
      await expect(escrow.connect(depositor).cancelEscrow(1))
        .to.emit(escrow, "EscrowCancelled");
    });
  });
});
