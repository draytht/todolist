from flask import Flask, request, jsonify, send_from_directory
import boto3
from boto3.dynamodb.conditions import Key
import os
from botocore.exceptions import ClientError


# Initialize the Flask application
application = Flask(__name__)

# Initialize the DynamoDB resource
region = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=region)

# Reference the 'todolistDB' table
table = dynamodb.Table('todolistDB')

@application.route('/')
def home():
    return send_from_directory('.', 'index.html')

# Route to serve static files (CSS, JS, images)
@application.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# API endpoint to add a task
@application.route('/add_task', methods=['POST'])
def add_task():
    data = request.json
    task = data.get('task')

    if not task:
        return jsonify({'error': 'Task cannot be empty'}), 400

    try:
        # Get the current maximum task_id
        response = table.scan(ProjectionExpression='task_id')
        task_ids = [int(item['task_id']) for item in response.get('Items', []) if item['task_id'].isdigit()]
        
        # Calculate the next task_id
        next_task_id = str(max(task_ids) + 1) if task_ids else '1'

        # Insert the new task
        table.put_item(Item={'task_id': next_task_id, 'task': task, 'checked': False})
        
        return jsonify({'message': 'Task added successfully', 'task_id': next_task_id})
    
    except ClientError as e:
        return jsonify({'error': f'Could not add task: {str(e)}'}), 500

@application.route('/delete_task', methods=['POST'])
def delete_task():
    data = request.json
    task_name = data.get('task')

    if not task_name:
        return jsonify({'error': 'Task name is required'}), 400

    try:
        # Scan the table to find the task by name
        response = table.scan(
            FilterExpression=Key('task').eq(task_name)
        )
        items = response.get('Items', [])

        if not items:
            return jsonify({'error': f'Task "{task_name}"'}), 404

        # Delete the first matching item (assuming task names are unique)
        task_id = items[0]['task_id']
        table.delete_item(Key={'task_id': task_id})

        return jsonify({'message': f'Task "{task_name}" deleted successfully'})
    except Exception as e:
        return jsonify({'error': f'Could not delete task: {str(e)}'}), 500

        

# API endpoint to get all tasks
@application.route('/get_tasks', methods=['GET'])
def get_tasks():
    try:
        response = table.scan()
        tasks = response.get('Items', [])
        return jsonify(tasks)
    except Exception as e:
        return jsonify({'error': f'Could not retrieve tasks: {str(e)}'}), 500

# API endpoint to update task status
@application.route('/update_task_status', methods=['POST'])
def update_task_status():
    data = request.json
    task = data.get('task')
    checked = data.get('checked')

    if not task:
        return jsonify({'error': 'Task is required'}), 400

    try:
        # Update the task status in DynamoDB
        response = table.update_item(
            Key={'task_id': task},
            UpdateExpression='SET checked = :checked',
            ExpressionAttributeValues={':checked': checked},
            ReturnValues='UPDATED_NEW'
        )
        return jsonify({'message': 'Task status updated successfully', 'updated': response['Attributes']})
    except Exception as e:
        return jsonify({'error': f'Could not update task status: {str(e)}'}), 500


# Run the Flask app
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=8080, debug=True)

