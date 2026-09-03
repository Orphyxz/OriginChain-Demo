// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

contract OriginChain {
    struct ProductUnit {
        bool exists;
        address manufacturer;
        address currentOwner;
        bytes32 metadataHash;
        uint256 registeredAt;
        uint256 transferCount;
    }

    mapping(bytes32 => ProductUnit) private products;
    mapping(bytes32 => address[]) private ownershipHistories;
    mapping(bytes32 => mapping(bytes32 => QualityCommitment)) private qualityCommitments;
    mapping(bytes32 => mapping(bytes32 => bool)) private evidenceCommitments;

    struct QualityCommitment {
        uint8 status;
        bytes32 commitmentHash;
        uint256 recordedAt;
    }

    event ProductRegistered(
        bytes32 indexed productKey,
        address indexed manufacturer,
        bytes32 metadataHash,
        uint256 timestamp
    );

    event OwnershipTransferred(
        bytes32 indexed productKey,
        address indexed previousOwner,
        address indexed newOwner,
        uint256 timestamp
    );

    event QualityStageRecorded(
        bytes32 indexed productKey,
        bytes32 indexed stageKey,
        uint8 status,
        bytes32 commitmentHash,
        address indexed recordedBy,
        uint256 timestamp
    );

    event EvidenceHashRecorded(
        bytes32 indexed productKey,
        bytes32 indexed evidenceHash,
        bytes32 indexed stageKey,
        address recordedBy,
        uint256 timestamp
    );

    function registerProduct(bytes32 productKey, bytes32 metadataHash) external {
        require(productKey != bytes32(0), "Invalid product key");
        require(metadataHash != bytes32(0), "Invalid metadata hash");
        require(!products[productKey].exists, "Product already registered");

        products[productKey] = ProductUnit({
            exists: true,
            manufacturer: msg.sender,
            currentOwner: msg.sender,
            metadataHash: metadataHash,
            registeredAt: block.timestamp,
            transferCount: 0
        });

        ownershipHistories[productKey].push(msg.sender);

        emit ProductRegistered(productKey, msg.sender, metadataHash, block.timestamp);
    }

    function transferOwnership(bytes32 productKey, address newOwner) external {
        ProductUnit storage product = products[productKey];

        require(product.exists, "Product not registered");
        require(msg.sender == product.currentOwner, "Only current owner can transfer");
        require(newOwner != address(0), "Invalid new owner");
        require(newOwner != product.currentOwner, "New owner must differ");

        address previousOwner = product.currentOwner;
        product.currentOwner = newOwner;
        product.transferCount += 1;
        ownershipHistories[productKey].push(newOwner);

        emit OwnershipTransferred(productKey, previousOwner, newOwner, block.timestamp);
    }

    function getProduct(bytes32 productKey)
        external
        view
        returns (
            bool exists,
            address manufacturer,
            address currentOwner,
            bytes32 metadataHash,
            uint256 registeredAt,
            uint256 transferCount
        )
    {
        ProductUnit storage product = products[productKey];

        return (
            product.exists,
            product.manufacturer,
            product.currentOwner,
            product.metadataHash,
            product.registeredAt,
            product.transferCount
        );
    }

    function verifyProduct(bytes32 productKey)
        external
        view
        returns (
            bool exists,
            address manufacturer,
            address currentOwner,
            bytes32 metadataHash,
            uint256 registeredAt,
            uint256 transferCount
        )
    {
        ProductUnit storage product = products[productKey];

        return (
            product.exists,
            product.manufacturer,
            product.currentOwner,
            product.metadataHash,
            product.registeredAt,
            product.transferCount
        );
    }

    function getOwnershipHistory(bytes32 productKey) external view returns (address[] memory) {
        return ownershipHistories[productKey];
    }

    function recordQualityStage(
        bytes32 productKey,
        bytes32 stageKey,
        uint8 status,
        bytes32 commitmentHash
    ) external {
        ProductUnit storage product = products[productKey];
        require(product.exists, "Product not registered");
        require(msg.sender == product.currentOwner, "Only current owner can record quality");
        require(stageKey != bytes32(0), "Invalid stage key");
        require(status >= 1 && status <= 3, "Invalid quality status");
        require(commitmentHash != bytes32(0), "Invalid commitment hash");

        qualityCommitments[productKey][stageKey] = QualityCommitment({
            status: status,
            commitmentHash: commitmentHash,
            recordedAt: block.timestamp
        });

        emit QualityStageRecorded(
            productKey, stageKey, status, commitmentHash, msg.sender, block.timestamp
        );
    }

    function getQualityStage(bytes32 productKey, bytes32 stageKey)
        external
        view
        returns (uint8 status, bytes32 commitmentHash, uint256 recordedAt)
    {
        QualityCommitment storage quality = qualityCommitments[productKey][stageKey];
        return (quality.status, quality.commitmentHash, quality.recordedAt);
    }

    function recordEvidenceHash(bytes32 productKey, bytes32 stageKey, bytes32 evidenceHash) external {
        ProductUnit storage product = products[productKey];
        require(product.exists, "Product not registered");
        require(msg.sender == product.currentOwner, "Only current owner can record evidence");
        require(stageKey != bytes32(0), "Invalid stage key");
        require(evidenceHash != bytes32(0), "Invalid evidence hash");
        require(!evidenceCommitments[productKey][evidenceHash], "Evidence already registered");

        evidenceCommitments[productKey][evidenceHash] = true;
        emit EvidenceHashRecorded(productKey, evidenceHash, stageKey, msg.sender, block.timestamp);
    }

    function isEvidenceRegistered(bytes32 productKey, bytes32 evidenceHash)
        external
        view
        returns (bool)
    {
        return evidenceCommitments[productKey][evidenceHash];
    }
}
