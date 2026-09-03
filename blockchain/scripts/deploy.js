import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import hre from "hardhat";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  const { ethers, networkName } = await hre.network.create();
  const [manufacturer, distributor, retailer] = await ethers.getSigners();
  const network = await ethers.provider.getNetwork();

  const OriginChain = await ethers.getContractFactory("OriginChain");
  const originChain = await OriginChain.deploy();
  await originChain.waitForDeployment();

  const deploymentTransaction = originChain.deploymentTransaction();
  const receipt = await deploymentTransaction.wait();
  const contractAddress = await originChain.getAddress();
  const artifact = await hre.artifacts.readArtifact("OriginChain");

  const deployment = {
    network: networkName,
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

  const deploymentPath = process.env.ORIGINCHAIN_DEPLOYMENT_PATH
    ? path.resolve(process.env.ORIGINCHAIN_DEPLOYMENT_PATH)
    : path.join(currentDirectory, "..", "deployments", "local.json");
  fs.mkdirSync(path.dirname(deploymentPath), { recursive: true });
  fs.writeFileSync(deploymentPath, `${JSON.stringify(deployment, null, 2)}\n`);

  console.log(`OriginChain deployed to ${contractAddress}`);
  console.log(`Network: ${networkName} (${network.chainId.toString()})`);
  console.log(`Transaction: ${deploymentTransaction.hash}`);
  console.log(`Block: ${receipt.blockNumber}`);
  console.log(`Deployment details written to ${deploymentPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
