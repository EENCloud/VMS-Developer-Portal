import json
from flask import request, jsonify, current_app, render_template
from app.auth import auth_required
from app.users import get_users
from app.utils.api_utils import api_call

## get list of available roles, supporting filtering by role name and pagination.
@auth_required
def get_roles():
    try:
        # Define API parameters such as page size and fields to include
        params = {
            'pageSize': int(request.args.get('pageSize', 100)),
            'include': 'permissions,notes,assignable,userCount',
        }

        # Add optional query parameters, if provided
        role_name_contains = request.args.get('roleName__contains')
        if role_name_contains:
            params['roleName__contains'] = role_name_contains

        page_token = request.args.get('pageToken')
        if page_token:
            params['pageToken'] = page_token

        roles = []

        # Handling the pagination of the API response
        while True:
            response = api_call('/roles', method='GET', params=params)
            response_json = json.loads(response)

            if 'results' not in response_json:
                raise ValueError("Invalid roles response format.")

            roles.extend(response_json['results'])
            next_page_token = response_json.get('nextPageToken')
            if not next_page_token:
                break
            params['pageToken'] = next_page_token

        # Respond with JSON if requested
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"results": roles, "totalSize": len(roles)})

        # Otherwise, render the HTML template
        return render_template('roles.html', roles=roles)

    except Exception as e:
        current_app.logger.error(f"An error occurred while fetching roles: {str(e)}")
        if request.headers.get('Accept') == 'application/json':
            return jsonify({"error": str(e)}), 500
        return render_template('error.html', error=str(e)), 500
    
# create role. validates that 'name' and 'permissions' fields are present in the request JSON.
@auth_required
def create_role():
    try:
        role_data = request.json
        required_fields = ['name', 'permissions']
        if not all(field in role_data for field in required_fields):
            return jsonify({"error": "Role must include a name and permissions"}), 400
        if not isinstance(role_data['permissions'], dict):
            return jsonify({"error": "Permissions must be a dictionary"}), 400
        response = api_call('/roles', method='POST', data=json.dumps(role_data))
        return jsonify(json.loads(response)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# get role by id, including permissions, notes, assignable, and user count.
@auth_required
def get_role(role_id):
    try:
        if not role_id:
            raise ValueError("Role ID is missing.")

        response = api_call(f'/roles/{role_id}?include=permissions,notes,assignable,userCount', method='GET')
        role_data = json.loads(response)

        # Validate response
        if 'permissions' not in role_data:
            raise ValueError("Invalid role data: Permissions field is missing.")

        # Categorize permissions
        categories = {
            'Administrator': ['administrator'],
            'Bridges and Cameras': ['addEditBridgesCameras', 'editSharing', 'controlPTZ', 'editPTZStations', 
                                    'addEditSpeakers', 'editSpeakers', 'turnCamerasOnOff', 'editMotionAreas', 
                                    'editAllCameraSettings'],
            'Accounts and Users': ['editAccounts', 'editNoBillingDeviceSettings', 'editUsers', 'upgradeEdition', 
                                    'viewPlugins', 'editPlugins', 'exportUsers', 'editMap'],
            'View and Downloads': ['viewLiveVideo', 'viewHistoricVideo', 'downloadVideo', 'viewPreviewVideo', 
                                    'talkDown'],
            'Layouts': ['layoutAdministrator', 'createLayouts'],
            'Auditlog': ['viewAuditLog'],
            'Archive': ['viewArchive', 'editArchive']
        }

        categorized_permissions = {
            category: {perm: role_data['permissions'].get(perm, False) for perm in perms}
            for category, perms in categories.items()
        }
        role_data['categorizedPermissions'] = categorized_permissions

        return jsonify(role_data), 200

    except ValueError as ve:
        current_app.logger.error(f"Validation error: {str(ve)}")
        return jsonify({"error": str(ve)}), 400

    except Exception as e:
        current_app.logger.error(f"An error occurred while fetching role: {str(e)}")
        return jsonify({"error": str(e)}), 500

# update role by id, validating required fields and handling 204 No Content response.
@auth_required
def update_role(role_id): 
    try:
        # Extract and validate request data
        role_data = request.json
        required_fields = ['name', 'permissions']
        
        if not all(field in role_data for field in required_fields):
            return jsonify({"error": "Role must include a name and permissions"}), 400
        if not isinstance(role_data['permissions'], dict):
            return jsonify({"error": "Permissions must be a dictionary"}), 400
        
        current_app.logger.info(f"Updating role with data: {role_data}")
        
        # Send API call
        response = api_call(f'/roles/{role_id}', method='PATCH', data=json.dumps(role_data))
        
        # Handle 204 No Content response
        if response == '' or response is None:  # This assumes the API returns an empty response for 204
            current_app.logger.info("Role updated successfully with 204 No Content response.")
            return jsonify({"message": "Role updated successfully"}), 204
        
        # If response contains unexpected data, log it
        current_app.logger.info(f"API Response: {response}")
        return jsonify({"error": "Unexpected response from API"}), 500
    
    except json.JSONDecodeError as json_err:
        current_app.logger.error(f"JSON Decode Error: {json_err}")
        return jsonify({"error": "Invalid JSON response from API"}), 500
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

## delete role, handling conflicts and logging errors.
@auth_required
def delete_role(role_id):
    if not role_id:
        return jsonify({"error": "Role ID is required."}), 400
    try:
        # Make the API call to delete the role
        response = api_call(f'/roles/{role_id}', method='DELETE')
        # If the response is successful
        return '', 204
    except Exception as e:
        # Check for specific conflict error in the exception message
        try:
            error_response = json.loads(str(e))
            if error_response.get("code") == 409 and error_response.get("message"):
                return jsonify({
                    "error": "Conflict",
                    "message": error_response["message"]
                }), 409
        except json.JSONDecodeError:
            return jsonify({"error": "Failed to delete the role."}), 500
        return jsonify({"error": str(e)}), 500
    
# fetch role assignments, optionally filtered by role ID.
@auth_required
def get_role_assignments():
    try:
        # Prepare parameters for the API call
        params = {}
        if 'roleId' in request.args:
            params['roleId__in'] = request.args.get('roleId')

        # Fetch role assignments from the external API
        response = api_call('/roleAssignments', method='GET', params=params)
        role_assignments = json.loads(response)

        # Ensure `results` is always a list
        if not role_assignments.get('results'):
            role_assignments['results'] = []

        # Fetch users
        users = get_users()
        if isinstance(users, tuple) and users[1] == 500:
            if 'format' in request.args and request.args['format'] == 'json':
                return jsonify({"error": "Failed to fetch users"}), 500
            return render_template('error.html', error="Failed to fetch users")

        # Determine response format based on query parameter or `Accept` header
        if 'format' in request.args and request.args['format'] == 'json':
            return jsonify({
                "roles": role_assignments['results'],
                "users": users
            })

        # Pass data to the template for HTML response
        return render_template(
            'assignments.html',
            roles=role_assignments['results'],
            users=users
        )
    except json.JSONDecodeError:
        if 'format' in request.args and request.args['format'] == 'json':
            return jsonify({"error": "Failed to decode role assignments response"}), 500
        return render_template('error.html', error="Failed to decode role assignments response")
    except Exception as e:
        if 'format' in request.args and request.args['format'] == 'json':
            return jsonify({"error": str(e)}), 500
        return render_template('error.html', error=f"An error occurred: {str(e)}")

# fetch role assignments as JSON, optionally filtered by role ID.
@auth_required
def get_role_assignments_json():
    try:
        # Prepare parameters for the API call
        params = {}
        if 'roleId' in request.args:
            params['roleId__in'] = request.args.get('roleId')

        # Fetch role assignments from the external API
        response = api_call('/roleAssignments', method='GET', params=params)
        role_assignments = json.loads(response)

        # Ensure `results` is always a list
        if not role_assignments.get('results'):
            role_assignments['results'] = []

        # Fetch users
        users = get_users()
        if isinstance(users, tuple) and users[1] == 500:
            return jsonify({"error": "Failed to fetch users"}), 500

        # Return the assignments and users as JSON
        return jsonify({
            "roles": role_assignments['results'],
            "users": users
        })
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to decode role assignments response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    
## create role assignment; validates that each assignment includes 'userId' and 'roleId'.
@auth_required
def create_role_assignment():
    try:
        role_assignment_data = request.json
        if not isinstance(role_assignment_data, list):
            return jsonify({"error": "Payload must be a list"}), 400

        for assignment in role_assignment_data:
            if not assignment.get('userId') or not assignment.get('roleId'):
                return jsonify({"error": "Each assignment must include userId and roleId"}), 400

        response = api_call('/roleAssignments:bulkcreate', method='POST', data=json.dumps(role_assignment_data))

        return jsonify(json.loads(response)), 201
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to decode response from role assignment creation"}), 500
    except Exception as e:
        # Log the error for debugging
        return jsonify({"error": str(e)}), 500

## delete role assignment; validates that each assignment includes 'userId' and 'roleId'.
@auth_required
def delete_role_assignment():
    try:
        role_assignment_data = request.json
        if not isinstance(role_assignment_data, list):
            return jsonify({"error": "Payload must be a list"}), 400

        for assignment in role_assignment_data:
            if not assignment.get('userId') or not assignment.get('roleId'):
                return jsonify({"error": "Each assignment must include userId and roleId"}), 400

        response = api_call('/roleAssignments:bulkdelete', method='POST', data=json.dumps(role_assignment_data))

        # Handle API response
        if response:
            try:
                response_data = json.loads(response)
                if all(item.get('status') == 200 for item in response_data):
                    return '', 204  # Successful deletion
                else:
                    return jsonify({"error": "Partial or complete failure in deletion", "details": response_data}), 500
            except json.JSONDecodeError:
                return jsonify({"error": "Failed to parse response from bulkdelete"}), 500
        else:
            return '', 204  # Assume no content indicates success

    except json.JSONDecodeError:
        return jsonify({"error": "Failed to decode response from role assignment deletion"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500