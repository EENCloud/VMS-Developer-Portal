from flask import current_app
import json
from app.auth import auth_required
from datetime import datetime
from app.utils.api_utils import api_call

# Get a list of users from the API, including detailed information, pagination, and formatted timestamps
@auth_required
def get_users():
    try:
        # Define API parameters to include additional fields and set page size
        params = {
            'include': 'loginDetails,locationSummary,timeZone,support,status,permissions,layoutSettings,'
                    'previewSettings,effectivePermissions,timeSettings,effectivePermissions',
            'pageSize': 100,  # Fetch up to 100 users per API call
        }

        if not params:
            raise ValueError("Invalid or empty query parameters provided.")

        users = []

        # Loop through paginated results
        while True:
            response = api_call('/users', method='GET', params=params)
            response_json = json.loads(response)

            if 'results' not in response_json:
                raise ValueError("Invalid users response format: 'results' key missing.")

            # Process each user in the current page
            for user in response_json['results']:
                last_login = user.get('loginDetails', {}).get('lastLogin', '')
                if last_login:
                    try:
                        # Parse the timestamp with timezone awareness
                        last_login_dt = datetime.strptime(last_login, '%Y-%m-%dT%H:%M:%S.%f%z')
                        # Convert to a formatted string without timezone
                        last_login = last_login_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError as e:
                        raise ValueError(f"Error parsing 'lastLogin' timestamp: {last_login}") from e

                # Add the user's details to the list
                users.append({
                    'userId': user.get('id', ''),
                    'name': f"{user.get('firstName', '')} {user.get('lastName', '')}",
                    'email': user.get('email', ''),
                    'status': user.get('status', {}).get('loginStatus', ''),
                    'lastLogin': last_login,
                })

            # Check for the next page of results
            next_page_token = response_json.get('nextPageToken')
            if not next_page_token:
                break
            params['pageToken'] = next_page_token

        # Return the aggregated user list
        return users

    except ValueError as ve:
        # Log and return validation errors
        current_app.logger.error(f"Validation error while fetching users: {str(ve)}")
        return {"error": str(ve)}, 400
    except json.JSONDecodeError as je:
        # Log and return JSON decoding errors
        current_app.logger.error(f"JSON decode error while fetching users: {str(je)}")
        return {"error": "Failed to decode response from API"}, 500
    except Exception as e:
        # Log and return general errors
        current_app.logger.error(f"An error occurred while fetching users: {str(e)}")
        return {"error": str(e)}, 500