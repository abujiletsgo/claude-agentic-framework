"""Test file with intentionally complex function for review system testing."""


def mega_processor(data, mode, flags, options, context):
    """An intentionally complex function to trigger complexity analyzer."""
    result = []
    errors = []
    warnings = []

    if not data:
        return result, errors, warnings

    if mode == "strict":
        if flags.get("validate"):
            for item in data:
                if isinstance(item, dict):
                    if "id" in item and "value" in item:
                        if item["value"] > 0:
                            if item["value"] < 1000:
                                if options.get("transform"):
                                    if context.get("user_role") == "admin":
                                        result.append(item["value"] * 2)
                                    elif context.get("user_role") == "manager":
                                        result.append(item["value"] * 1.5)
                                    else:
                                        result.append(item["value"])
                                else:
                                    result.append(item["value"])
                            else:
                                warnings.append(f"Value too high: {item['value']}")
                        else:
                            errors.append(f"Negative value: {item['value']}")
                    else:
                        errors.append(f"Missing fields in item: {item}")
                elif isinstance(item, (int, float)):
                    if item > 0 and item < 1000:
                        result.append(item)
                    elif item >= 1000:
                        warnings.append(f"Numeric value too high: {item}")
                    else:
                        errors.append(f"Negative numeric: {item}")
                elif isinstance(item, str):
                    try:
                        val = float(item)
                        if val > 0:
                            result.append(val)
                        else:
                            errors.append(f"Negative string value: {item}")
                    except ValueError:
                        errors.append(f"Cannot parse: {item}")
                else:
                    errors.append(f"Unknown type: {type(item)}")
        else:
            for item in data:
                if item is not None:
                    result.append(item)
    elif mode == "lenient":
        for item in data:
            if item is not None:
                try:
                    if hasattr(item, "__iter__") and not isinstance(item, str):
                        for sub in item:
                            if sub is not None:
                                result.append(sub)
                    else:
                        result.append(item)
                except TypeError:
                    errors.append(f"Iteration error: {item}")
    elif mode == "batch":
        batch_size = options.get("batch_size", 10)
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            for item in batch:
                if item and isinstance(item, dict):
                    if "priority" in item:
                        if item["priority"] == "high":
                            result.insert(0, item)
                        elif item["priority"] == "medium":
                            result.append(item)
                        else:
                            warnings.append(f"Low priority skipped: {item}")
                    else:
                        result.append(item)
    else:
        errors.append(f"Unknown mode: {mode}")

    if flags.get("sort") and result:
        try:
            result.sort()
        except TypeError:
            warnings.append("Could not sort results")

    if flags.get("deduplicate") and result:
        seen = set()
        unique = []
        for item in result:
            key = str(item)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        result = unique

    return result, errors, warnings
