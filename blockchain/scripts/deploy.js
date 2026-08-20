const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const [manufacturer, distributor, retailer] = await hre.ethers.getSigners();
  const network = await hre.ethers.provider.getNetwork();

  const OriginChain = await hre.ethers.getContractFactory("OriginChain");
  const originChain = await OriginChain.deploy();
  await originChain.waitForDeployment();

  const deploymentTransaction = originChain.deploymentTransaction();
  const receipt = await deploymentTransaction.wait();
  const contractAddress = await originChain.getAddress();
  const artifact = await hre.artifacts.readArtifact("OriginChain");

  const deployment = {
    network: hre.network.name,
    chainId: network.chainId.toString(),
    contractName: "OriginChain",
    contractAddress,
    deployer: manufacturer.address,
    demoActors: {
      manufacturer: manufacturer.address,
      distributor: distributor.address,
      retailer: retailer.address
    },
    transactionHash: deploymentTransaction.hash,
    blockNumber: receipt.blockNumber,
    abiPath: "blockchain/artifacts/contracts/OriginChain.sol/OriginChain.json",
    abi: artifact.abi
  };

  const deploymentsDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(deploymentsDir, { recursive: true });
  fs.writeFileSync(
    path.join(deploymentsDir, "local.json"),
    `${JSON.stringify(deployment, null, 2)}\n`
  );

  console.log(`OriginChain deployed to ${contractAddress}`);
  console.log(`Network: ${hre.network.name} (${network.chainId.toString()})`);
  console.log(`Transaction: ${deploymentTransaction.hash}`);
  console.log(`Block: ${receipt.blockNumber}`);
  console.log("Deployment details written to deployments/local.json");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
