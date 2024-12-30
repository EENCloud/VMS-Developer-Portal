from flask import current_app as app
from app.auth import login, logout
from app.roles import (
    get_roles, create_role, delete_role, get_role, update_role,
    get_role_assignments, create_role_assignment, delete_role_assignment,
    get_role_assignments_json
)
from app.users import get_users
from app.home import index

# Home Route, requires authentication
app.add_url_rule('/', view_func=index)

# Authentication Routes, login and logout
app.add_url_rule('/login', view_func=login) 
app.add_url_rule('/logout', view_func=logout)

# Role Management Routes, requires authentication
app.add_url_rule('/roles', view_func=get_roles, methods=['GET'])  # List roles
app.add_url_rule('/roles', view_func=create_role, methods=['POST'])  # Create a new role
app.add_url_rule('/roles/<role_id>', view_func=delete_role, methods=['DELETE'])  # Delete a role
app.add_url_rule('/roles/<role_id>', view_func=get_role, methods=['GET'])  # Retrieve a role
app.add_url_rule('/roles/<role_id>', view_func=update_role, methods=['PATCH'])  # Update a role

# Role Assignments Routes, requires authentication
app.add_url_rule('/assignments', view_func=get_role_assignments, methods=['GET'])  # Get role assignments
app.add_url_rule('/roleassignments/json', view_func=get_role_assignments_json, methods=['GET'])  # Get assignments in JSON
app.add_url_rule('/roleassignments/bulkcreate', view_func=create_role_assignment, methods=['POST'])  # Bulk create assignments
app.add_url_rule('/roleassignments/bulkdelete', view_func=delete_role_assignment, methods=['POST'])  # Bulk delete assignments

# User Management Routes, requires authentication
app.add_url_rule('/users', view_func=get_users, methods=['GET'])  # List users