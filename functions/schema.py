PRODUCTS_SCHEMA = [
    {
        "name": "name",
        "type": "STRING",
        "mode": "REQUIRED"
    },
    {
        "name": "description",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "options",
        "type": "RECORD",
        "mode": "REPEATED",
        "fields": [
        {
            "name": "key",
            "type": "STRING",
            "mode": "NULLABLE"
        },
        {
            "name": "value",
            "type": "STRING",
            "mode": "NULLABLE"
        }
        ]
    },
    {
        "name": "url",
        "type": "STRING",
        "mode": "REQUIRED"
    },
    {
        "name": "marketplace",
        "type": "STRING",
        "mode": "REQUIRED"
    },
    {
        "name": "category_breadcrumb",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "price",
        "type": "INTEGER",
        "mode": "NULLABLE"
    },
    {
        "name": "strike_price",
        "type": "INTEGER",
        "mode": "NULLABLE"
    },
    {
        "name": "weight",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "brand",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "stock",
        "type": "INTEGER",
        "mode": "NULLABLE"
    },
    {
        "name": "shop_name",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "shop_domain",
        "type": "STRING",
        "mode": "NULLABLE"
    },
    {
        "name": "image_urls",
        "type": "STRING",
        "mode": "REPEATED"
    },
    {
        "name": "rating",
        "type": "FLOAT",
        "mode": "NULLABLE"
    },
    {
        "name": "review_count",
        "type": "INTEGER",
        "mode": "NULLABLE"
    },
    {
        "name": "view_count",
        "type": "INTEGER",
        "mode": "NULLABLE"
    },
    {
        "name": "sale_count",
        "type": "INTEGER",
        "mode": "NULLABLE"
    },
    {
        "name": "categories",
        "type": "STRING",
        "mode": "REPEATED"
    }
    ]