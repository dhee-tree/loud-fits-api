from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from product.models import CategoryChoices


class FeedUploadSerializer(serializers.Serializer):
    """Serializer for validating the entire feed JSON structure."""
    products = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        allow_empty=False
    )

    def validate_products(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Products must be an array.")
        if len(value) == 0:
            raise serializers.ValidationError(
                "Products array cannot be empty.")
        return value


def validate_feed_products(products: list) -> dict:
    """
    Validate a list of product dictionaries and return structured results.
    
    Returns:
        dict with keys: valid_products, errors, counts_by_category, duplicates
    """
    url_validator = URLValidator()
    valid_products = []
    errors = []
    counts_by_category = {}
    seen_ids = {}
    duplicates = []

    required_fields = ['external_id', 'name', 'category',
                       'image_url', 'price', 'currency', 'product_url']
    valid_categories = [choice[0] for choice in CategoryChoices.choices]

    for index, product in enumerate(products):
        product_errors = []
        product_id = product.get('external_id', f'unknown_at_index_{index}')

        # Check for required fields
        for field in required_fields:
            if field not in product or product[field] is None or product[field] == '':
                product_errors.append({
                    'field': field,
                    'error': f"'{field}' is required."
                })

        # Skip further validation if required fields are missing
        if product_errors:
            errors.append({
                'index': index,
                'external_id': product_id,
                'errors': product_errors
            })
            continue

        # Check for duplicate external_ids within the file
        if product_id in seen_ids:
            duplicates.append({
                'index': index,
                'external_id': product_id,
                'first_occurrence': seen_ids[product_id]
            })
            product_errors.append({
                'field': 'external_id',
                'error': f"Duplicate product external_id. First seen at index {seen_ids[product_id]}."
            })
        else:
            seen_ids[product_id] = index

        # Validate category
        if product.get('category') and product['category'] not in valid_categories:
            product_errors.append({
                'field': 'category',
                'error': f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            })

        # Validate URLs
        for url_field in ['image_url', 'product_url']:
            url_value = product.get(url_field)
            if url_value:
                try:
                    url_validator(url_value)
                except DjangoValidationError:
                    product_errors.append({
                        'field': url_field,
                        'error': f"Invalid URL format."
                    })

        # Validate price
        price = product.get('price')
        if price is not None:
            try:
                price_val = float(price)
                if price_val < 0:
                    product_errors.append({
                        'field': 'price',
                        'error': "Price cannot be negative."
                    })
            except (TypeError, ValueError):
                product_errors.append({
                    'field': 'price',
                    'error': "Price must be a valid number."
                })

        # Validate currency (basic check - 3 letter code)
        currency = product.get('currency')
        if currency and (not isinstance(currency, str) or len(currency) != 3):
            product_errors.append({
                'field': 'currency',
                'error': "Currency must be a 3-letter code (e.g., 'GBP', 'USD')."
            })

        if product_errors:
            errors.append({
                'index': index,
                'external_id': product_id,
                'errors': product_errors
            })
        else:
            valid_products.append({
                'external_id': product['external_id'],
                'name': product['name'],
                'category': product['category'],
                'image_url': product['image_url'],
                'price': product['price'],
                'currency': product['currency'],
                'product_url': product['product_url'],
            })
            # Count by category
            category = product['category']
            counts_by_category[category] = counts_by_category.get(
                category, 0) + 1

    return {
        'valid_products': valid_products,
        'errors': errors,
        'counts_by_category': counts_by_category,
        'duplicates': duplicates,
        'total': len(products),
        'valid_count': len(valid_products),
        'failed_count': len(errors),
    }
