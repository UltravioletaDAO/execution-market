import requests
import os
import json

def run_test():
    url = "https://api.execution.market/health"
    print(f"Testing live EM API: {url}")
    response = requests.get(url)
    print(response.status_code, response.text)

if __name__ == "__main__":
    run_test()
