import sqlite3
from flask import Flask, g, request, jsonify, render_template
import datetime
import uuid # For generating a unique ID if we choose not to use the auto-increment ID

# --- Configuration ---
DATABASE = 'tasks.db'
app = Flask(__name__)
app.config.from_object(__name__)

# --- Database Helper Functions ---

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'sqlite_db' not in g:
        g.sqlite_db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        # Use sqlite3.Row objects to access columns by name
        g.sqlite_db.row_factory = sqlite3.Row
    return g.sqlite_db


def init_db():
    """Initializes the database schema with the required tasks table structure."""
    with app.app_context():
        db = get_db()
        # Create a table named 'tasks' with hierarchical support
        db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,        -- 5. Unique Id (Primary Key)
                description TEXT NOT NULL,                  -- 1. description (< 500 char, handled by front-end validation)
                start_timestamp TEXT NOT NULL,              -- 2. Start timestamp
                status TEXT NOT NULL DEFAULT 'ACTIVE',      -- 3. Status (ACTIVE, COMPLETED, ABANDONED, CLEAR)
                finish_timestamp TEXT,                      -- 4. Finish timestamp (can be NULL)
                parent_id INTEGER,                          -- 6. parent task (Foreign Key to tasks.id, can be NULL)
                
                -- Define a foreign key constraint for parent_id
                FOREIGN KEY (parent_id) REFERENCES tasks(id)
            );
        ''')
        db.commit()
        print("Tasks table created/verified with the hierarchical schema.")

# --- Teardown Hook ---

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = g.pop('sqlite_db', None)
    if db is not None:
        db.close()

# --- Server Routes ---

@app.route('/')
def index():
    """Renders the main task manager HTML page."""
    return render_template('index.html')

@app.route('/tasks', methods=['POST'])
def create_task():
    """Adds a new task to the database after checking parent status."""
    
    # 1. Get data from the incoming JSON request
    if not request.json:
        return jsonify({'error': 'Missing JSON data'}), 400
    
    data = request.json
    description = data.get('description')
    parent_id = data.get('parent_id')
    
    # Simple validation
    if not description:
        return jsonify({'error': 'Description is required'}), 400
    if len(description) > 500:
        return jsonify({'error': 'Description exceeds 500 character limit'}), 400

    db = get_db()
    
    if parent_id is not None:
        try:
            # Check the parent task's status
            parent_task = db.execute(
                'SELECT status FROM tasks WHERE id = ?', (parent_id,)
            ).fetchone()
            
            if parent_task is None:
                return jsonify({'error': f'Parent task with ID {parent_id} not found.'}), 404
            
            parent_status = parent_task['status']
            
            # Allow creation only if the parent is ACTIVE
            if parent_status != 'ACTIVE':
                return jsonify({
                    'error': 'Cannot create a subtask.',
                    'message': f'Parent task (ID {parent_id}) is not ACTIVE. Current status: {parent_status}.'
                }), 409 # Conflict

        except sqlite3.Error as e:
            return jsonify({'error': f'Database error during parent validation: {e}'}), 500

    # 2. Set default and required values
    start_timestamp = datetime.datetime.now().isoformat()
    status = 'ACTIVE' # Default status
    
    # 3. Insert the new task into the database
    try:
        cursor = db.execute(
            '''
            INSERT INTO tasks (description, start_timestamp, status, parent_id)
            VALUES (?, ?, ?, ?)
            ''',
            (description, start_timestamp, status, parent_id)
        )
        db.commit()
        
        # Get the ID of the newly created task
        new_id = cursor.lastrowid
        
        return jsonify({
            'message': 'Task created successfully',
            'task': {
                'id': new_id,
                'description': description,
                'start_timestamp': start_timestamp,
                'status': status,
                'parent_id': parent_id
            }
        }), 201
        
    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': f'Database error: {e}'}), 500

@app.route('/tasks/<int:task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """
    Updates the status of a task. Enforces rules for COMPLETED, ABANDONED, and CLEAR statuses.
    """
    if not request.json or 'status' not in request.json:
        return jsonify({'error': 'Missing status in JSON data'}), 400
    
    new_status = request.json['status'].upper()
    valid_statuses = ['ACTIVE', 'COMPLETED', 'ABANDONED', 'CLEAR']
    
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status: Must be one of {valid_statuses}'}), 400

    db = get_db()
    
    # Use a transaction to ensure all updates happen successfully
    try:
        # 1. Check if the task exists
        task = db.execute('SELECT id, status FROM tasks WHERE id = ?', (task_id,)).fetchone()
        if task is None:
            return jsonify({'error': f'Task with ID {task_id} not found'}), 404
        
        # 2. Handle COMPLETED status rule
        if new_status == 'COMPLETED':
            # Check for any active children
            active_children = db.execute(
                'SELECT COUNT(*) FROM tasks WHERE parent_id = ? AND status = ?',
                (task_id, 'ACTIVE')
            ).fetchone()[0]
            
            if active_children > 0:
                return jsonify({
                    'error': 'Cannot set task to COMPLETED.', 
                    'message': f'This task has {active_children} active direct child task(s).'
                }), 409 # Conflict
        
        # 3. Handle Recursive Status Change (ABANDONED or CLEAR)
        if new_status in ['ABANDONED', 'CLEAR']:
            # We need a function to find all recursive children IDs.
            # SQLite doesn't have easy recursive queries, so we'll do this iteratively/manually in Python for simplicity.
            
            # Start a set with the current task_id and add children recursively
            tasks_to_update = {task_id}
            queue = [task_id]
            
            while queue:
                current_parent_id = queue.pop(0)
                children = db.execute('SELECT id FROM tasks WHERE parent_id = ?', (current_parent_id,)).fetchall()
                for child in children:
                    child_id = child['id']
                    if child_id not in tasks_to_update:
                        tasks_to_update.add(child_id)
                        queue.append(child_id)
            
            # Convert set to a tuple for the SQL query
            task_ids_tuple = tuple(tasks_to_update)
            
            # Update all tasks (parent and all recursive children)
            placeholders = ', '.join(['?'] * len(task_ids_tuple))
            db.execute(
                f'''
                UPDATE tasks SET status = ?, finish_timestamp = ? 
                WHERE id IN ({placeholders})
                ''',
                (new_status, datetime.datetime.now().isoformat()) + task_ids_tuple
            )
            
        # 4. Handle simple status change (ACTIVE or COMPLETED, or if ABANDONED/CLEAR path didn't run)
        else:
            finish_time = datetime.datetime.now().isoformat() if new_status in ['COMPLETED', 'ABANDONED', 'CLEAR'] else None
            
            db.execute(
                '''
                UPDATE tasks SET status = ?, finish_timestamp = ? 
                WHERE id = ?
                ''',
                (new_status, finish_time, task_id)
            )
        
        db.commit()
        return jsonify({
            'message': f'Task {task_id} and relevant children status updated to {new_status}.'
        }), 200

    except sqlite3.Error as e:
        db.rollback()
        return jsonify({'error': f'Database error during status update: {e}'}), 500
    except Exception as e:
        # Catch unexpected errors
        db.rollback()
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500
    

@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    """Fetches ALL tasks (including CLEARED) and returns them in a nested JSON structure."""
    
    # Use the helper function to fetch all tasks
    query = 'SELECT * FROM tasks ORDER BY id ASC'
    nested_tasks = get_tasks_data(query)
    
    return jsonify(nested_tasks), 200

@app.route('/tasks/active', methods=['GET'])
def get_non_clear_tasks():
    """Fetches all tasks that are NOT in the 'CLEAR' status, returned in a nested JSON structure."""
    
    # Use the helper function to fetch tasks filtered by status
    query = "SELECT * FROM tasks WHERE status != 'CLEAR' ORDER BY id ASC"
    
    # Note: Even if a child task is not clear, if its parent is clear, 
    # the parent will be excluded from the query, meaning the child won't appear 
    # as a top-level task (as it has a parent_id), nor will it be nested.
    # This is the expected behaviour when filtering the root list.
    nested_tasks = get_tasks_data(query)
    
    return jsonify(nested_tasks), 200

@app.route('/tasks/active-only', methods=['GET'])
def get_active_only_tasks():
    """
    Fetches only tasks where status is 'ACTIVE', returning them in a nested JSON structure. 
    Note: A child task will only appear if its parent is also included in the query result.
    """
    
    # Use the helper function to fetch tasks filtered by status
    query = "SELECT * FROM tasks WHERE status = 'ACTIVE' ORDER BY id ASC"
    
    nested_tasks = get_tasks_data(query)
    
    return jsonify(nested_tasks), 200

@app.route('/schema', methods=['GET'])
def get_schema():
    """
    Retrieves and returns the schema for the 'tasks' table.
    """
    db = get_db()
    
    try:
        # Query the SQLite master table for the table creation SQL
        schema_query = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks';"
        ).fetchone()

        if schema_query:
            # The 'sql' column contains the exact CREATE TABLE statement
            create_sql = schema_query['sql']
            
            # Optionally, you can also query for PRAGMA table_info to get a list of columns
            columns_cursor = db.execute("PRAGMA table_info(tasks);").fetchall()
            
            columns_info = []
            for col in columns_cursor:
                columns_info.append({
                    'cid': col['cid'],
                    'name': col['name'],
                    'type': col['type'],
                    'notnull': bool(col['notnull']),
                    'default_value': col['dflt_value'],
                    'is_pk': bool(col['pk'])
                })

            return jsonify({
                'table_name': 'tasks',
                'create_statement': create_sql,
                'columns': columns_info
            }), 200
        else:
            return jsonify({'error': 'Tasks table not found in database.'}), 404

    except sqlite3.Error as e:
        return jsonify({'error': f'Database error retrieving schema: {e}'}), 500


def get_tasks_data(query, params=None):
    """
    Fetches tasks based on a query and returns them in a nested list structure.
    
    :param query: The SQL SELECT query string.
    :param params: A tuple of parameters for the query (or None).
    :return: A list of nested task dictionaries.
    """
    db = get_db()
    
    # 1. Fetch all tasks based on the provided query
    tasks_cursor = db.execute(query, params or ())
    tasks_list = [dict(task) for task in tasks_cursor.fetchall()]
    
    # 2. Build a map of tasks by ID for quick lookups
    tasks_map = {task['id']: task for task in tasks_list}
    
    # 3. Initialize a list for top-level tasks
    top_level_tasks = []
    
    # 4. Iterate through the tasks and build the hierarchy
    for task in tasks_list:
        task['children_tasks'] = [] 
        
        parent_id = task.get('parent_id')
        
        if parent_id is None:
            top_level_tasks.append(task)
        elif parent_id in tasks_map:
            # Add child to its parent's children_tasks list
            tasks_map[parent_id]['children_tasks'].append(task)
            
    return top_level_tasks

# --- Initialization and Run ---

if __name__ == '__main__':
    # Initialize the database *before* running the app
    init_db()
    
    # Run the server in debug mode
    app.run(debug=True)