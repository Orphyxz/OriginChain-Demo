import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";
import hre from "hardhat";

const { ethers } = await hre.network.create();

async function expectRevert(operation, reason) {
  await assert.rejects(operation, (error) => {
    assert.ok(String(error).includes(reason), `Expected revert reason: ${reason}`);
    return true;
  });
}

async function eventFrom(transactionPromise, contract, eventName) {
  const receipt = await (await transactionPromise).wait();
  for (const log of receipt.logs) {
    try {
      const parsed = contract.interface.parseLog(log);
      if (parsed?.name === eventName) return parsed.args;
    } catch {
      // Ignore logs emitted by other contracts.
    }
  }
  assert.fail(`Event ${eventName} was not emitted`);
}

describe("OriginChain", function () {
  let originChain;
  let manufacturer;
  let distributor;
  let retailer;
  let outsider;
  let productKey;
  let metadataHash;

  beforeEach(async function () {
    [manufacturer, distributor, retailer, outsider] = await ethers.getSigners();
    originChain = await ethers.deployContract("OriginChain");
    await originChain.waitForDeployment();
    productKey = ethers.keccak256(ethers.toUtf8Bytes("OC-DEMO-0001"));
    metadataHash = ethers.keccak256(ethers.toUtf8Bytes(JSON.stringify({
      batch: "BATCH-2026-A", brand: "OriginChain Demo", name: "Demo Product"
    })));
  });

  it("registers a product", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    const product = await originChain.getProduct(productKey);
    assert.equal(product.exists, true);
    assert.equal(product.manufacturer, manufacturer.address);
    assert.equal(product.currentOwner, manufacturer.address);
    assert.equal(product.metadataHash, metadataHash);
    assert.equal(product.transferCount, 0n);
    assert.ok(product.registeredAt > 0n);
  });

  it("emits ProductRegistered on registration", async function () {
    const args = await eventFrom(
      originChain.connect(manufacturer).registerProduct(productKey, metadataHash),
      originChain, "ProductRegistered"
    );
    assert.equal(args.productKey, productKey);
    assert.equal(args.manufacturer, manufacturer.address);
    assert.equal(args.metadataHash, metadataHash);
    assert.ok(args.timestamp > 0n);
  });

  it("rejects duplicate registration", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    await expectRevert(
      () => originChain.connect(manufacturer).registerProduct(productKey, metadataHash),
      "Product already registered"
    );
  });

  it("records manufacturer and current owner correctly", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    const product = await originChain.verifyProduct(productKey);
    assert.equal(product.manufacturer, manufacturer.address);
    assert.equal(product.currentOwner, manufacturer.address);
  });

  it("transfers ownership to the distributor", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    await originChain.connect(manufacturer).transferOwnership(productKey, distributor.address);
    const product = await originChain.getProduct(productKey);
    assert.equal(product.currentOwner, distributor.address);
    assert.equal(product.transferCount, 1n);
  });

  it("emits OwnershipTransferred on transfer", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    const args = await eventFrom(
      originChain.connect(manufacturer).transferOwnership(productKey, distributor.address),
      originChain, "OwnershipTransferred"
    );
    assert.equal(args.productKey, productKey);
    assert.equal(args.previousOwner, manufacturer.address);
    assert.equal(args.newOwner, distributor.address);
    assert.ok(args.timestamp > 0n);
  });

  it("rejects transfer by a non-owner", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    await expectRevert(
      () => originChain.connect(outsider).transferOwnership(productKey, distributor.address),
      "Only current owner can transfer"
    );
  });

  it("rejects transfer to the zero address", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    await expectRevert(
      () => originChain.connect(manufacturer).transferOwnership(productKey, ethers.ZeroAddress),
      "Invalid new owner"
    );
  });

  it("rejects transfer of an unknown product", async function () {
    const unknown = ethers.keccak256(ethers.toUtf8Bytes("OC-UNKNOWN-0001"));
    await expectRevert(
      () => originChain.connect(manufacturer).transferOwnership(unknown, distributor.address),
      "Product not registered"
    );
  });

  it("preserves Manufacturer -> Distributor -> Retailer ownership history", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    await originChain.connect(manufacturer).transferOwnership(productKey, distributor.address);
    await originChain.connect(distributor).transferOwnership(productKey, retailer.address);
    const history = await originChain.getOwnershipHistory(productKey);
    const product = await originChain.getProduct(productKey);
    assert.deepEqual([...history], [manufacturer.address, distributor.address, retailer.address]);
    assert.equal(product.currentOwner, retailer.address);
    assert.equal(product.transferCount, 2n);
  });

  it("returns the registered metadata hash", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    assert.equal((await originChain.verifyProduct(productKey)).metadataHash, metadataHash);
  });

  it("handles unknown product verification without reverting", async function () {
    const unknown = ethers.keccak256(ethers.toUtf8Bytes("OC-UNKNOWN-0001"));
    const product = await originChain.verifyProduct(unknown);
    const history = await originChain.getOwnershipHistory(unknown);
    assert.equal(product.exists, false);
    assert.equal(product.manufacturer, ethers.ZeroAddress);
    assert.equal(product.currentOwner, ethers.ZeroAddress);
    assert.equal(product.metadataHash, ethers.ZeroHash);
    assert.equal(product.registeredAt, 0n);
    assert.equal(product.transferCount, 0n);
    assert.deepEqual([...history], []);
  });

  it("records an owner-authorized quality-stage commitment", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    const stageKey = ethers.keccak256(ethers.toUtf8Bytes("MANUFACTURER"));
    const commitment = ethers.keccak256(ethers.toUtf8Bytes("quality snapshot"));
    const args = await eventFrom(
      originChain.connect(manufacturer).recordQualityStage(productKey, stageKey, 1, commitment),
      originChain, "QualityStageRecorded"
    );
    assert.equal(args.productKey, productKey);
    assert.equal(args.stageKey, stageKey);
    assert.equal(args.status, 1n);
    assert.equal(args.commitmentHash, commitment);
    assert.equal(args.recordedBy, manufacturer.address);
    const quality = await originChain.getQualityStage(productKey, stageKey);
    assert.equal(quality.status, 1n);
    assert.equal(quality.commitmentHash, commitment);
    assert.ok(quality.recordedAt > 0n);
  });

  it("rejects quality updates from a non-owner and for an unknown product", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    const stageKey = ethers.keccak256(ethers.toUtf8Bytes("MANUFACTURER"));
    const commitment = ethers.keccak256(ethers.toUtf8Bytes("quality snapshot"));
    await expectRevert(
      () => originChain.connect(outsider).recordQualityStage(productKey, stageKey, 1, commitment),
      "Only current owner can record quality"
    );
    const unknown = ethers.keccak256(ethers.toUtf8Bytes("UNKNOWN"));
    await expectRevert(
      () => originChain.connect(manufacturer).recordQualityStage(unknown, stageKey, 1, commitment),
      "Product not registered"
    );
  });

  it("rejects invalid quality statuses and hashes", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    const stageKey = ethers.keccak256(ethers.toUtf8Bytes("MANUFACTURER"));
    const commitment = ethers.keccak256(ethers.toUtf8Bytes("quality snapshot"));
    await expectRevert(
      () => originChain.recordQualityStage(productKey, stageKey, 0, commitment),
      "Invalid quality status"
    );
    await expectRevert(
      () => originChain.recordQualityStage(productKey, stageKey, 1, ethers.ZeroHash),
      "Invalid commitment hash"
    );
  });

  it("records evidence hashes and rejects duplicates", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    const stageKey = ethers.keccak256(ethers.toUtf8Bytes("MANUFACTURER"));
    const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence bytes"));
    const args = await eventFrom(
      originChain.recordEvidenceHash(productKey, stageKey, evidenceHash),
      originChain, "EvidenceHashRecorded"
    );
    assert.equal(args.productKey, productKey);
    assert.equal(args.evidenceHash, evidenceHash);
    assert.equal(args.stageKey, stageKey);
    assert.equal(args.recordedBy, manufacturer.address);
    assert.equal(await originChain.isEvidenceRegistered(productKey, evidenceHash), true);
    await expectRevert(
      () => originChain.recordEvidenceHash(productKey, stageKey, evidenceHash),
      "Evidence already registered"
    );
  });

  it("restricts evidence registration to the current owner", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    const stageKey = ethers.keccak256(ethers.toUtf8Bytes("MANUFACTURER"));
    const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence bytes"));
    await expectRevert(
      () => originChain.connect(outsider).recordEvidenceHash(productKey, stageKey, evidenceHash),
      "Only current owner can record evidence"
    );
  });
});
