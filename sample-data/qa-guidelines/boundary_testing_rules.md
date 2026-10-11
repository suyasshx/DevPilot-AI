# QA Guideline: Boundary Value Analysis and Input Range Testing

## 1. Purpose
Define standardized testing rules for integer, decimal, string, and array boundaries across EA REST APIs.

## 2. Integer and Quantity Boundaries
- **Zero and Negative Checks:** For all count, quantity, offset, or pagination size parameters, always test `0` and negative values (`-1`, `-10`). Unless explicitly specified as allowing negative values, the API MUST reject non-positive quantities with `422 Unprocessable Entity` or `400 Bad Request`.
- **Lower Boundary:** For positive 1-indexed integers (e.g., order item quantity, page limit), test the minimum allowed value `1`.
- **Upper Boundary:** Test documented maximum limits (e.g., maximum page limit of `100`). Test off-by-one upper bound (`101`) to ensure strict enforcement.
- **Large Integers:** Test 64-bit integer overflows (`9223372036854775807`) and verify that backend database drivers do not raise unhandled SQL exceptions.

## 3. String and Identifier Boundaries
- **Empty and Whitespace Strings:** Test empty string `""` and whitespace-only `"   "` for required string fields (e.g., usernames, shipping addresses). API MUST reject with `422`.
- **Length Limits:** Test minimum string length (e.g., username min length 3 -> test length 2) and maximum string length.
- **Special Characters:** Test strings containing emojis, SQL control characters (`' OR 1=1 --`), and HTML tags (`<script>`) to ensure proper sanitization and parameter binding.

## 4. Array and Collection Boundaries
- **Empty Arrays:** For collection submissions (e.g., order items list), test empty list `[]`. API MUST reject with `422` if minimum items is 1.
- **Duplicate Items:** Test arrays containing identical items (e.g., duplicate product IDs in the same order) to verify deduplication or aggregation.
