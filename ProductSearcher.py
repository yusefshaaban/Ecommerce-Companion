"""This is redundant code, but kept for future reference."""

import requests

# Keys: ['id', 'brand', 'name', 'price', 'price_sign', 'currency', 'image_link', 'product_link', 'website_link', 'description', 'rating', 'category', 'product_type', 'tag_list', 'created_at', 'updated_at', 'product_api_url', 'api_featured_image', 'product_colors']

class ProductSearcher:
    def __init__(self):
        pass

    def find(self, brand):
        response = requests.get(f"https://makeup-api.herokuapp.com/api/v1/products.json?brand={brand}")
        items = response.json()
        all_names = []
        for item in items:
            brand = item.get('brand')
            name = item.get('name')
            if brand and name:
                name = name.replace(brand, '').strip()
            all_names.append(name)

        return all_names

if __name__ == "__main__":
    productSearcher = ProductSearcher()
    all_names = productSearcher.find("maybelline")
    print(all_names)