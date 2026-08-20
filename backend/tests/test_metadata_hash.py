from backend.metadata_hash import metadata_hash


def test_canonical_metadata_hash_is_deterministic():
    metadata = {
        "product_code": "OC-DEMO-0001",
        "name": "OriginChain Demo Sneakers",
        "brand": "Origin Labs",
        "batch_number": "B001",
        "description": "Blockchain authentication demo",
    }

    assert metadata_hash(metadata) == metadata_hash(metadata)


def test_dict_order_does_not_change_metadata_hash():
    first = {
        "product_code": "OC-DEMO-0001",
        "name": "OriginChain Demo Sneakers",
        "brand": "Origin Labs",
        "batch_number": "B001",
        "description": "Blockchain authentication demo",
    }
    second = {
        "description": "Blockchain authentication demo",
        "batch_number": "B001",
        "brand": "Origin Labs",
        "name": "OriginChain Demo Sneakers",
        "product_code": "OC-DEMO-0001",
    }

    assert metadata_hash(first) == metadata_hash(second)


def test_modified_metadata_changes_hash():
    original = {
        "product_code": "OC-DEMO-0001",
        "name": "OriginChain Demo Sneakers",
        "brand": "Origin Labs",
        "batch_number": "B001",
        "description": "Blockchain authentication demo",
    }
    modified = {
        **original,
        "brand": "Origin Labs - ALTERED",
    }

    assert metadata_hash(original) != metadata_hash(modified)
