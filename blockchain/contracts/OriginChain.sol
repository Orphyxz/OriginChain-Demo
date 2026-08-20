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
}
