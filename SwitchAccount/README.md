# EagleEyeNetworks API

This is a code sample for interacting with the EagleEyeNetworks API. It can be used to generate access tokens on behalf of the end-user account.

**Use case:**  
A reseller needs to manage bridges or cameras within one of the end-user accounts. The reseller does not have direct access to these devices. To gain access, they need to generate an access token on behalf of the end-user. With this new access token, the reseller has access to all devices within the end-user account.
  
## Installation

To use this library, you need to have Python installed. You can install the required dependencies by running the following command:

```shell
pip install requests python-dotenv
```

## Usage

1. Import the required modules:

```python
import requests
import json
from dotenv import load_dotenv
import os
```

1. Load the environment variables from a `.env` file:

```python
# Load environment variables from a .env file
load_dotenv()
```

1. `.env`contains:

```shell
ACCESS_TOKEN=''
BASE_URL='api.cXXX.eagleeyenetworks.com'
```

1. Create an instance of the `EagleEyeNetworks` class:

```python
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
```

1. List accounts:

```python
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
```

1. Generating an access_token on behalf of the end-user account:

```python
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
```

1. Run the code:

```python
# Main entry point of the script
if __name__ == "__main__":
    eagle_eye_networks = EagleEyeNetworks()
    eagle_eye_networks.switch_account()
```

1. Output:

```shell
Total Size: 6
Results:
- ID: 00133338, Name: API SANDBOX, Status: active, Type: endUserAccount
- ID: 00146250, Name: ML-AMS01 , Status: active, Type: endUserAccount
- ID: 00045519, Name: ML-EHV01 , Status: active, Type: endUserAccount
- ID: 00154379, Name: ML-EHV02 , Status: active, Type: endUserAccount
- ID: 00055548, Name: ML-HMK01 , Status: active, Type: endUserAccount
- ID: 00016333, Name: RESELLER , Status: active, Type: reseller
Enter the account id you want to switch to: 00133338
Switching account to: ID: 00133338, Name: API SANDBOX  
Switched to account: results:
- Access_token: eyJraWQiO.........kPQN4TdLUFlpJg
- BaseUrl: api.c013.eagleeyenetworks.com
```
