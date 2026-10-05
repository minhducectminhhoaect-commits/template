import os
import aiohttp
import asyncio
import pandas as pd
import re

API_URL = "https://bitis.com.vn/collections/all/products.json?page={}&limit=250"
OUTPUT_DIR = "Bitis_Products"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def sanitize_filename(filename):
    # Remove invalid characters for Windows filenames
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

async def fetch_products(session, page):
    url = API_URL.format(page)
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('products', [])
            return []
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return []

async def download_image(session, img_url, filepath):
    if not img_url.startswith('http'):
        img_url = 'https:' + img_url
    try:
        async with session.get(img_url) as response:
            if response.status == 200:
                with open(filepath, 'wb') as f:
                    f.write(await response.read())
                return True
    except Exception as e:
        print(f"Error downloading {img_url}: {e}")
    return False

async def process_product(session, product, semaphore, results):
    title = product.get('title', 'Unknown')
    handle = product.get('handle', '')
    product_url = f"https://bitis.com.vn/products/{handle}" if handle else ""
    
    images = product.get('images', [])
    if not images:
        return
    
    # Take the first image
    img_url = images[0].get('src', '')
    if not img_url:
        return
        
    ext = img_url.split('?')[0].split('.')[-1]
    if len(ext) > 4:
        ext = 'jpg'
        
    safe_title = sanitize_filename(title)
    
    # Handle duplicates by adding product id
    prod_id = product.get('id', '')
    filename = f"{safe_title}_{prod_id}.{ext}"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    async with semaphore:
        success = await download_image(session, img_url, filepath)
    
    if success:
        results.append({
            'Tên sản phẩm': title,
            'URL Sản phẩm': product_url,
            'File hình ảnh': filename,
            'URL Hình ảnh': img_url
        })
        try:
            print(f"Downloaded: {filename}".encode('utf-8', 'ignore').decode('utf-8'))
        except:
            pass

async def main():
    print("Starting Biti's product scraper...")
    # Limit max products for safety but allow setting to infinity.
    # The prompt says ALL products. We will fetch all.
    results = []
    page = 1
    
    # Limit concurrent downloads to avoid overwhelming the server
    semaphore = asyncio.Semaphore(10)
    
    async with aiohttp.ClientSession() as session:
        while True:
            print(f"Fetching page {page}...")
            products = await fetch_products(session, page)
            if not products:
                print("No more products found. Stopping pagination.")
                break
                
            tasks = [process_product(session, p, semaphore, results) for p in products]
            await asyncio.gather(*tasks)
            
            # Since limit is ignored and it returns 50 max, if less than 50 we are likely at the end.
            if len(products) < 50:
                print("Reached the last page.")
                break
                
            # Save incrementally every 10 pages
            if page % 10 == 0 and results:
                df = pd.DataFrame(results)
                df.to_excel("Bitis_Products_Summary.xlsx", index=False)
                print(f"Incremental summary saved for {len(results)} products.")

            page += 1
            
            # For demonstration and system stability, let's stop after 100 pages (5000 products)
            # if we don't want it to run for hours. 
            # Actually, I will remove the limit to fulfill "tất cả" but print progress.
            
    # Save to Excel
    print(f"Total products downloaded: {len(results)}")
    if results:
        df = pd.DataFrame(results)
        excel_path = "Bitis_Products_Summary.xlsx"
        df.to_excel(excel_path, index=False)
        print(f"Summary saved to {excel_path}")
    else:
        print("No products downloaded.")

if __name__ == "__main__":
    asyncio.run(main())
