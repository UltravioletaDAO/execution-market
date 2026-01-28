import { expect } from "chai";
import { ethers } from "hardhat";
import { time, loadFixture } from "@nomicfoundation/hardhat-toolbox/network-helpers";
import { ChambaEscrow, MockERC20 } from "../typechain-types";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";

describe("ChambaEscrow", function () {
  // Constants
  const TASK_ID = ethers.encodeBytes32String("task-001");
  const ESCROW_AMOUNT = ethers.parseUnits("100", 6); // 100 USDC
  const ONE_WEEK = 7 * 24 * 60 * 60; // 7 days in seconds
  const ONE_HOUR = 60 * 60;

  // Fixture for deployment
  async function deployFixture() {
    const [owner, depositor, worker, operator, other] = await ethers.getSigners();

    // Deploy mock USDC
    const MockERC20 = await ethers.getContractFactory("MockERC20");
    const usdc = await MockERC20.deploy("USD Coin", "USDC", 6);

    // Deploy ChambaEscrow
    const ChambaEscrow = await ethers.getContractFactory("ChambaEscrow");
    const escrow = await ChambaEscrow.deploy();

    // Mint USDC to depositor
    await usdc.mint(depositor.address, ethers.parseUnits("10000", 6));

    // Approve escrow contract
    await usdc.connect(depositor).approve(await escrow.getAddress(), ethers.MaxUint256);

    return { escrow, usdc, owner, depositor, worker, operator, other };
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
      ).to.be.revertedWith("ChambaEscrow: invalid task ID");
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
      ).to.be.revertedWith("ChambaEscrow: invalid timeout");
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
      ).to.be.revertedWith("ChambaEscrow: task already has escrow");
    });
  });

  describe("Release Escrow", function () {
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

    it("Should allow depositor to release funds", async function () {
      const { escrow, usdc, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      const releaseAmount = ethers.parseUnits("30", 6); // 30 USDC (30%)

      await expect(
        escrow.connect(depositor).releaseEscrow(escrowId, worker.address, releaseAmount, "submission")
      )
        .to.emit(escrow, "EscrowReleased")
        .withArgs(escrowId, worker.address, releaseAmount, releaseAmount, "submission");

      expect(await usdc.balanceOf(worker.address)).to.equal(releaseAmount);

      const escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.released).to.equal(releaseAmount);
      expect(escrowData.status).to.equal(0); // Still Active
    });

    it("Should support partial releases (30/70 pattern)", async function () {
      const { escrow, usdc, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      const submissionRelease = ethers.parseUnits("30", 6); // 30%
      const approvalRelease = ethers.parseUnits("70", 6); // 70%

      // First release: submission (30%)
      await escrow.connect(depositor).releaseEscrow(
        escrowId,
        worker.address,
        submissionRelease,
        "submission"
      );

      let escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.released).to.equal(submissionRelease);
      expect(escrowData.status).to.equal(0); // Still Active

      // Second release: approval (70%)
      await escrow.connect(depositor).releaseEscrow(
        escrowId,
        worker.address,
        approvalRelease,
        "approval"
      );

      escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.released).to.equal(ESCROW_AMOUNT);
      expect(escrowData.status).to.equal(1); // Completed

      // Check release history
      const releases = await escrow.getReleases(escrowId);
      expect(releases.length).to.equal(2);
      expect(releases[0].reason).to.equal("submission");
      expect(releases[1].reason).to.equal("approval");
    });

    it("Should allow operator to release funds", async function () {
      const { escrow, usdc, owner, depositor, worker, operator, escrowId } = await loadFixture(createEscrowFixture);

      // Authorize operator
      await escrow.connect(owner).setOperator(operator.address, true);

      const releaseAmount = ethers.parseUnits("50", 6);

      await expect(
        escrow.connect(operator).releaseEscrow(escrowId, worker.address, releaseAmount, "operator release")
      ).to.emit(escrow, "EscrowReleased");

      expect(await usdc.balanceOf(worker.address)).to.equal(releaseAmount);
    });

    it("Should revert if unauthorized", async function () {
      const { escrow, worker, other, escrowId } = await loadFixture(createEscrowFixture);

      await expect(
        escrow.connect(other).releaseEscrow(escrowId, worker.address, ESCROW_AMOUNT, "unauthorized")
      ).to.be.revertedWith("ChambaEscrow: not authorized");
    });

    it("Should revert if amount exceeds remaining", async function () {
      const { escrow, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      const excessAmount = ESCROW_AMOUNT + ethers.parseUnits("1", 6);

      await expect(
        escrow.connect(depositor).releaseEscrow(escrowId, worker.address, excessAmount, "too much")
      ).to.be.revertedWith("ChambaEscrow: insufficient balance");
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

    it("Should allow depositor to refund before any releases", async function () {
      const { escrow, usdc, depositor, escrowId } = await loadFixture(createEscrowFixture);

      const balanceBefore = await usdc.balanceOf(depositor.address);

      await expect(escrow.connect(depositor).refundEscrow(escrowId))
        .to.emit(escrow, "EscrowRefunded")
        .withArgs(escrowId, depositor.address, ESCROW_AMOUNT);

      expect(await usdc.balanceOf(depositor.address)).to.equal(balanceBefore + ESCROW_AMOUNT);

      const escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.status).to.equal(2); // Refunded
    });

    it("Should require timeout after partial release", async function () {
      const { escrow, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      // Make a partial release
      await escrow.connect(depositor).releaseEscrow(
        escrowId,
        worker.address,
        ethers.parseUnits("30", 6),
        "submission"
      );

      // Try to refund before timeout
      await expect(
        escrow.connect(depositor).refundEscrow(escrowId)
      ).to.be.revertedWith("ChambaEscrow: timeout not reached");

      // Fast forward past timeout
      await time.increase(ONE_WEEK + 1);

      // Now refund should work
      await expect(escrow.connect(depositor).refundEscrow(escrowId))
        .to.emit(escrow, "EscrowRefunded");
    });

    it("Should refund remaining amount after partial releases", async function () {
      const { escrow, usdc, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      const releaseAmount = ethers.parseUnits("30", 6);
      await escrow.connect(depositor).releaseEscrow(
        escrowId,
        worker.address,
        releaseAmount,
        "submission"
      );

      await time.increase(ONE_WEEK + 1);

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

    it("Should allow depositor to cancel before any releases", async function () {
      const { escrow, usdc, depositor, escrowId } = await loadFixture(createEscrowFixture);

      const balanceBefore = await usdc.balanceOf(depositor.address);

      await expect(escrow.connect(depositor).cancelEscrow(escrowId))
        .to.emit(escrow, "EscrowCancelled")
        .withArgs(escrowId, depositor.address, ESCROW_AMOUNT);

      expect(await usdc.balanceOf(depositor.address)).to.equal(balanceBefore + ESCROW_AMOUNT);

      const escrowData = await escrow.getEscrow(escrowId);
      expect(escrowData.status).to.equal(3); // Cancelled
    });

    it("Should prevent cancellation after release", async function () {
      const { escrow, depositor, worker, escrowId } = await loadFixture(createEscrowFixture);

      await escrow.connect(depositor).releaseEscrow(
        escrowId,
        worker.address,
        ethers.parseUnits("30", 6),
        "submission"
      );

      await expect(
        escrow.connect(depositor).cancelEscrow(escrowId)
      ).to.be.revertedWith("ChambaEscrow: cannot cancel after release");
    });

    it("Should only allow depositor to cancel", async function () {
      const { escrow, other, escrowId } = await loadFixture(createEscrowFixture);

      await expect(
        escrow.connect(other).cancelEscrow(escrowId)
      ).to.be.revertedWith("ChambaEscrow: only depositor can cancel");
    });
  });

  describe("Operator Management", function () {
    it("Should allow owner to set operators", async function () {
      const { escrow, owner, operator } = await loadFixture(deployFixture);

      await expect(escrow.connect(owner).setOperator(operator.address, true))
        .to.emit(escrow, "OperatorUpdated")
        .withArgs(operator.address, true);

      expect(await escrow.isOperator(operator.address)).to.be.true;
    });

    it("Should allow batch operator setting", async function () {
      const { escrow, owner, operator, other } = await loadFixture(deployFixture);

      await escrow.connect(owner).setOperatorsBatch([operator.address, other.address], true);

      expect(await escrow.isOperator(operator.address)).to.be.true;
      expect(await escrow.isOperator(other.address)).to.be.true;
    });

    it("Should prevent non-owner from setting operators", async function () {
      const { escrow, depositor, operator } = await loadFixture(deployFixture);

      await expect(
        escrow.connect(depositor).setOperator(operator.address, true)
      ).to.be.revertedWithCustomError(escrow, "OwnableUnauthorizedAccount");
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

      const releaseAmount = ethers.parseUnits("40", 6);
      await escrow.connect(depositor).releaseEscrow(
        escrowId,
        worker.address,
        releaseAmount,
        "partial"
      );

      expect(await escrow.getRemaining(escrowId)).to.equal(ESCROW_AMOUNT - releaseAmount);
    });

    it("Should return escrow ID by task", async function () {
      const { escrow, escrowId } = await loadFixture(createEscrowFixture);

      expect(await escrow.getEscrowByTask(TASK_ID)).to.equal(escrowId);
    });

    it("Should correctly report timeout status", async function () {
      const { escrow, escrowId } = await loadFixture(createEscrowFixture);

      expect(await escrow.isTimedOut(escrowId)).to.be.false;

      await time.increase(ONE_WEEK + 1);

      expect(await escrow.isTimedOut(escrowId)).to.be.true;
    });
  });

  describe("Edge Cases", function () {
    it("Should revert for non-existent escrow", async function () {
      const { escrow } = await loadFixture(deployFixture);

      await expect(escrow.getEscrow(999)).to.be.revertedWith("ChambaEscrow: escrow does not exist");
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
      expect(await escrow.getEscrowByTask(task2)).to.equal(2);

      const escrow2 = await escrow.getEscrow(2);
      expect(escrow2.amount).to.equal(ethers.parseUnits("200", 6));
    });
  });
});
