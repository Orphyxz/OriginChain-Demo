const { expect } = require("chai");
const { ethers } = require("hardhat");
const { anyValue } = require("@nomicfoundation/hardhat-chai-matchers/withArgs");

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

    const OriginChain = await ethers.getContractFactory("OriginChain");
    originChain = await OriginChain.deploy();
    await originChain.waitForDeployment();

    productKey = ethers.keccak256(ethers.toUtf8Bytes("OC-DEMO-0001"));
    metadataHash = ethers.keccak256(
      ethers.toUtf8Bytes(
        JSON.stringify({
          batch: "BATCH-2026-A",
          brand: "OriginChain Demo",
          name: "Demo Product"
        })
      )
    );
  });

  it("registers a product", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);

    const product = await originChain.getProduct(productKey);

    expect(product.exists).to.equal(true);
    expect(product.manufacturer).to.equal(manufacturer.address);
    expect(product.currentOwner).to.equal(manufacturer.address);
    expect(product.metadataHash).to.equal(metadataHash);
    expect(product.transferCount).to.equal(0);
    expect(product.registeredAt).to.be.greaterThan(0);
  });

  it("emits ProductRegistered on registration", async function () {
    await expect(originChain.connect(manufacturer).registerProduct(productKey, metadataHash))
      .to.emit(originChain, "ProductRegistered")
      .withArgs(productKey, manufacturer.address, metadataHash, anyValue);
  });

  it("rejects duplicate registration", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);

    await expect(
      originChain.connect(manufacturer).registerProduct(productKey, metadataHash)
    ).to.be.revertedWith("Product already registered");
  });

  it("records manufacturer and current owner correctly", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);

    const product = await originChain.verifyProduct(productKey);

    expect(product.manufacturer).to.equal(manufacturer.address);
    expect(product.currentOwner).to.equal(manufacturer.address);
  });

  it("transfers ownership to the distributor", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    await originChain.connect(manufacturer).transferOwnership(productKey, distributor.address);

    const product = await originChain.getProduct(productKey);

    expect(product.currentOwner).to.equal(distributor.address);
    expect(product.transferCount).to.equal(1);
  });

  it("emits OwnershipTransferred on transfer", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);

    await expect(originChain.connect(manufacturer).transferOwnership(productKey, distributor.address))
      .to.emit(originChain, "OwnershipTransferred")
      .withArgs(productKey, manufacturer.address, distributor.address, anyValue);
  });

  it("rejects transfer by a non-owner", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);

    await expect(
      originChain.connect(outsider).transferOwnership(productKey, distributor.address)
    ).to.be.revertedWith("Only current owner can transfer");
  });

  it("rejects transfer to the zero address", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);

    await expect(
      originChain.connect(manufacturer).transferOwnership(productKey, ethers.ZeroAddress)
    ).to.be.revertedWith("Invalid new owner");
  });

  it("rejects transfer of an unknown product", async function () {
    const unknownProductKey = ethers.keccak256(ethers.toUtf8Bytes("OC-UNKNOWN-0001"));

    await expect(
      originChain.connect(manufacturer).transferOwnership(unknownProductKey, distributor.address)
    ).to.be.revertedWith("Product not registered");
  });

  it("preserves Manufacturer -> Distributor -> Retailer ownership history", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);
    await originChain.connect(manufacturer).transferOwnership(productKey, distributor.address);
    await originChain.connect(distributor).transferOwnership(productKey, retailer.address);

    const history = await originChain.getOwnershipHistory(productKey);
    const product = await originChain.getProduct(productKey);

    expect(history).to.deep.equal([
      manufacturer.address,
      distributor.address,
      retailer.address
    ]);
    expect(product.currentOwner).to.equal(retailer.address);
    expect(product.transferCount).to.equal(2);
  });

  it("returns the registered metadata hash", async function () {
    await originChain.connect(manufacturer).registerProduct(productKey, metadataHash);

    const product = await originChain.verifyProduct(productKey);

    expect(product.metadataHash).to.equal(metadataHash);
  });

  it("handles unknown product verification without reverting", async function () {
    const unknownProductKey = ethers.keccak256(ethers.toUtf8Bytes("OC-UNKNOWN-0001"));

    const product = await originChain.verifyProduct(unknownProductKey);
    const history = await originChain.getOwnershipHistory(unknownProductKey);

    expect(product.exists).to.equal(false);
    expect(product.manufacturer).to.equal(ethers.ZeroAddress);
    expect(product.currentOwner).to.equal(ethers.ZeroAddress);
    expect(product.metadataHash).to.equal(ethers.ZeroHash);
    expect(product.registeredAt).to.equal(0);
    expect(product.transferCount).to.equal(0);
    expect(history).to.deep.equal([]);
  });
});
