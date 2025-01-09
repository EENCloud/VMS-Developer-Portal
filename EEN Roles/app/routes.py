from functools import wraps
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
import json

# Initialize Blueprint
api_bp = Blueprint('api', __name__)

# --- Authentication Decorator ---
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            current_app.logger.info("User not authenticated, redirecting to login.")
            return redirect(url_for('api.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Before Request for Authentication ---
@api_bp.before_request
def require_auth():
    excluded_endpoints = ['api.login', 'static']
    if request.endpoint not in excluded_endpoints and 'access_token' not in session:
        current_app.logger.info("User not authenticated, redirecting to login.")
        return redirect(url_for('api.login'))
    
# --- Home Page Route ---
@api_bp.route('/', methods=['GET'])
@auth_required
def index():
    return render_template('index.html')

# --- Login Route ---
@api_bp.route('/login', methods=['GET', 'POST'])
def login():
    code = request.args.get('code')
    client = current_app.een_client

    if code:
        try:
            response = client.auth_een(code, type="code")
            auth_response = response.json()
            current_app.logger.info(f"Authentication response: {auth_response}")
            session['access_token'] = auth_response.get('access_token')
            session['base_url'] = auth_response.get('httpsBaseUrl', {}).get('hostname')
            current_app.logger.info("User authenticated successfully.")
            return redirect(url_for('api.index'))
        except Exception as e:
            current_app.logger.error(f"Login failed: {e}")
            return render_template('login.html', error="Authentication Failed")
    auth_url = client.get_auth_url()
    return render_template('login.html', auth_url=auth_url)

# --- Logout Route ---
@api_bp.route('/logout', methods=['GET'])
@auth_required
def logout():
    try:
        current_app.een_client.logout()
    except Exception as e:
        current_app.logger.error(f"Error during logout: {e}")
    session.clear()
    return redirect(url_for('api.index'))

# --- Roles Page Route ---
@api_bp.route('/roles', methods=['GET'])
@auth_required
def roles_page():
    return render_template('roles.html')

# --- Assignments Page Route ---
@api_bp.route('/assignments', methods=['GET'])
@auth_required
def assignments_page():
    return render_template('assignments.html')

# --- Roles API Routes ---
@api_bp.route('/api/roles', methods=['GET'])
@auth_required
def get_roles_route():
    try:
        include_fields = ['permissions', 'notes', 'assignable', 'userCount']
        response = current_app.een_client.get_roles(include=include_fields)
        roles = response.json()
        # Ensure roles is a proper JSON array
        if isinstance(roles, dict) and 'results' in roles:
            roles = roles['results']
        return jsonify({"results": roles, "totalSize": len(roles)})
    except Exception as e:
        current_app.logger.error(f"Error fetching roles: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/roles', methods=['POST'])
@auth_required
def create_role_route():
    try:
        role_data = request.get_json()
        response = current_app.een_client.create_role(role_data)
        if response is None:
            raise Exception("Failed to create role: No response")
        if not response.ok:
            raise Exception(f"Failed to create role: {response.text}")
        # Check if the response content is empty
        if response.content:
            response_data = response.json()
        else:
            response_data = {}
        return jsonify(response_data), 201
    except Exception as e:
        current_app.logger.error(f"Error creating role: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/roles/<role_id>', methods=['GET'])
@auth_required
def get_role_route(role_id):
    try:
        # Include necessary fields in the request
        include_fields = ['permissions', 'notes', 'assignable', 'userCount']
        response = current_app.een_client.get_role(role_id, include=include_fields)
        if response is None:
            raise Exception(f"Failed to fetch role {role_id}: No response")
        role_data = response.json()  # Parse the JSON response
        if isinstance(role_data, dict) and 'results' in role_data:
            role_data = role_data['results']
        return jsonify(role_data)
    except Exception as e:
        current_app.logger.error(f"Error fetching role {role_id}: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/roles/<role_id>', methods=['PATCH'])
@auth_required
def update_role_route(role_id):
    try:
        role_data = request.get_json()
        current_app.logger.info(f"Updating role {role_id} with data: {role_data}")
        response = current_app.een_client.update_role(role_id, role_data)
        if response is None:
            raise Exception(f"Failed to update role {role_id}: No response")
        if not response.ok:
            raise Exception(f"Failed to update role {role_id}: {response.text}")
        return '', 204
    except Exception as e:
        current_app.logger.error(f"Error updating role {role_id}: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/roles/<role_id>', methods=['DELETE'])
@auth_required
def delete_role_route(role_id):
    try:
        response = current_app.een_client.delete_role(role_id)
        if response is None:
            raise Exception(f"Failed to delete role {role_id}: No response")
        if not response.ok:
            if response.status_code == 409:
                error_message = "Role is currently assigned to user(s). Please remove assignments before trying to delete."
                raise Exception(error_message)
            raise Exception(f"Failed to delete role {role_id}: {response.text}")
        return '', 204
    except Exception as e:
        current_app.logger.error(f"Error deleting role {role_id}: {e}")
        return jsonify({"error": str(e)}), 500

# --- Role Assignments API Routes ---
@api_bp.route('/api/roleassignments', methods=['GET'])
@auth_required
def get_role_assignments_route():
    try:
        role_id = request.args.get('roleId')
        current_app.logger.info(f"Fetching role assignments for role ID: {role_id}")
        assignments_response = current_app.een_client.get_role_assignments(roleId__in=[role_id])
        assignments_data = assignments_response.json()  # Parse the JSON response

        users_response = current_app.een_client.get_users(include=['status', 'loginDetails'])
        users_data = users_response.json()  # Parse the JSON response

        # Combine firstName and lastName into name
        for user in users_data['results']:
            user['name'] = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()

        current_app.logger.info(f"Role assignments data: {assignments_data}")
        current_app.logger.info(f"Users data: {users_data}")

        # Fetch role details to get the role name
        role_response = current_app.een_client.get_role(role_id)
        role_data = role_response.json()
        role_name = role_data.get('name', 'Unknown Role')

        return jsonify({"assignments": assignments_data, "users": users_data, "roleName": role_name})
    except Exception as e:
        current_app.logger.error(f"Error fetching role assignments: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/roleassignments/bulkcreate', methods=['POST'])
@auth_required
def create_role_assignment_route():
    try:
        assignments = request.get_json()
        current_app.een_client.create_role_assignments(assignments)
        return '', 204
    except Exception as e:
        current_app.logger.error(f"Error creating role assignments: {e}")
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/roleassignments/bulkdelete', methods=['POST'])
@auth_required
def delete_role_assignment_route():
    try:
        assignments = request.get_json()
        current_app.een_client.delete_role_assignments(assignments)
        return '', 204
    except Exception as e:
        if e.response and e.response.status_code == 409:
            error_message = "Some role assignments could not be deleted because they are currently in use."
            current_app.logger.error(f"Error deleting role assignments: {error_message}")
            return jsonify({"error": error_message}), 409
        current_app.logger.error(f"Error deleting role assignments: {e}")
        return jsonify({"error": str(e)})

# --- Users API Route ---
@api_bp.route('/api/users', methods=['GET'])
@auth_required
def get_users_route():
    try:
        users_response = current_app.een_client.get_users(include=['status', 'loginDetails'])
        users_data = users_response.json()  # Parse the JSON response

        # Combine firstName and lastName into name
        for user in users_data['results']:
            user['name'] = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()

        return jsonify(users_data)
    except Exception as e:
        current_app.logger.error(f"Error fetching users: {e}")
        return jsonify({"error": str(e)}), 500