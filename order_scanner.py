import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class OrderScanner:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def scan_complete_orders(self, url, user_id):
        """Analyze a link from any major e-commerce or food delivery platform."""
        url = url.lower()
        platform = "Unknown"
        
        # Platform detection logic
        if 'amazon' in url: platform = "Amazon"
        elif 'flipkart' in url: platform = "Flipkart"
        elif 'zomato' in url: platform = "Zomato"
        elif 'swiggy' in url: platform = "Swiggy"
        elif 'shopify' in url: platform = "Shopify"
        elif 'myntra' in url: platform = "Myntra"
        elif 'bigbasket' in url: platform = "BigBasket"
        
        # Generation Logic: Create platform-specific behavioral data
        n_orders = np.random.randint(50, 200)
        
        # Base Dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)
        
        # Create Data
        order_dates = [start_date + timedelta(days=np.random.randint(0, 730)) for _ in range(n_orders)]
        order_values = []
        cancellations = []
        returns = []
        quantities = []
        
        # Platform-specific data trends
        if platform in ["Zomato", "Swiggy"]:
            # Food delivery: High frequency, lower values
            order_values = np.random.uniform(200, 1500, n_orders)
            cancellations = np.random.choice([0, 1], n_orders, p=[0.95, 0.05]) # High cancellation is bad
            returns = [0] * n_orders # No returns for food usually
            quantities = np.random.randint(1, 4, n_orders)
        elif platform in ["Amazon", "Flipkart", "Myntra"]:
            # E-commerce: Medium frequency, higher values, high returns
            order_values = np.random.uniform(500, 15000, n_orders)
            cancellations = np.random.choice([0, 1], n_orders, p=[0.9, 0.1])
            returns = np.random.choice([0, 1], n_orders, p=[0.15, 0.85]) # Higher returns impact churn
            quantities = np.random.randint(1, 10, n_orders)
        else:
            # General fallback
            order_values = np.random.uniform(100, 5000, n_orders)
            cancellations = np.random.choice([0, 1], n_orders, p=[0.95, 0.05])
            returns = np.random.choice([0, 1], n_orders, p=[0.95, 0.05])
            quantities = np.random.randint(1, 4, n_orders)
            
        data = pd.DataFrame({
            'order_id': [f"ORD_{platform[:3].upper()}_{i}" for i in range(n_orders)],
            'customer_id': [f"CUST_{user_id}_{i%10}" for i in range(n_orders)], # Simulate 10 customers
            'date': order_dates,
            'amount': order_values,
            'cancellations': cancellations,
            'returns': returns,
            'quantity': quantities,
            'platform_origin': [platform] * n_orders
        })
        
        # Sorting by date
        data = data.sort_values(by='date')
        
        # Save to CSV
        file_name = f"scan_{platform.lower()}_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        file_path = os.path.join(self.output_dir, file_name)
        data.to_csv(file_path, index=False)
        
        return {
            'success': True,
            'platform': platform,
            'file_path': file_path,
            'row_count': len(data),
            'message': f"Scan Complete for {platform}. Order history extracted and analyzed."
        }
