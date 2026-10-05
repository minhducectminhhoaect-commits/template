import requests

def get_product_count():
    page = 1
    total = 0
    while True:
        url = f"https://bitis.com.vn/collections/all/products.json?page={page}&limit=250"
        response = requests.get(url)
        data = response.json()
        products = data.get('products', [])
        if not products:
            break
        total += len(products)
        print(f"Page {page}: {len(products)} products, total: {total}")
        page += 1
        
        # for quick check, let's just see how many pages we can find fast
        if page > 10:
            print("More than 10 pages, meaning >2500 products...")
            break
            
if __name__ == "__main__":
    get_product_count()
