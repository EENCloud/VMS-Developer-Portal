import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables from a .env file
load_dotenv()

class EagleEyeNetworks:
    def __init__(self):
        # Initialize instance variables
        self.access_token = os.getenv('ACCESS_TOKEN')
        self.base_url = os.getenv('BASE_URL')
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}"
        }
        self.account_id = ""
        self.account_name = ""
        
    def list_accounts(self):
        # URL for listing accounts
        url = f"https://{self.base_url}/api/v3.0/accounts"

        # Make a GET request to the API to list accounts
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            # If the response is successful, parse the JSON data
            data = response.json()

            # Print the total number of accounts and their details
            print(f"Total Size: {data['totalSize']}")
            print("Results:")
            for result in data['results']:
                print(f"- ID: {result['id']}, Name: {result['name']}, Status: {result['status']}, Type: {result['type']}")
            return data['results']
        else:
            # If the request failed, print the error message
            print("Failed to retrieve list of accounts")
            return print(json.dumps(response.json(), indent=4))
    
    def switch_account(self):
        # URL for switching accounts
        url = "https://auth.eagleeyenetworks.com/api/v3.0/authorizationTokens"
        
        # Get the account ID from the user input
        accounts = self.list_accounts()
        self.account_id = input("Enter the account id you want to switch to: ")
        for account in accounts:
            if account['id'] == self.account_id:
                self.account_name = account['name']
                break
        # Payload for the POST request to switch accounts
        payload = {
            "scopes": ["vms.all"],
            "type": "reseller",
            "targetType": "account",
            "targetId": f"{self.account_id}"
        }

        # Make a POST request to the API to switch accounts
        response = requests.post(url, json=payload, headers=self.headers)
        
        # Print the account switch status
        print(f"Switching account to: ID: {self.account_id}, Name: {self.account_name} ")
        if response.status_code == 201:
            # If the response is successful, parse and print the new token details
            data = response.json()
            print("Switched to account: results:")
            print(f"- Access_token: {data['accessToken']}")
            print(f"- BaseUrl: {data['httpsBaseUrl']['hostname']}")
            return response.json()
        else:
            # If the request failed, print the error message
            print("Failed to switch account")
            return print(json.dumps(response.json(), indent=4))

# Main entry point of the script
if __name__ == "__main__":
    eagle_eye_networks = EagleEyeNetworks()
    eagle_eye_networks.switch_account()
