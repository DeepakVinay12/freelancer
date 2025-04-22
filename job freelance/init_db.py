import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# Initialize the boto3 client
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')

def create_tables():
    # Create freelancer table
    try:
        freelancer_table = dynamodb.create_table(
            TableName='freelancer',
            KeySchema=[
                {
                    'AttributeName': 'email',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'  # String
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("Creating Freelancer table...")
        freelancer_table.meta.client.get_waiter('table_exists').wait(TableName='freelancer')
        print("Freelancer table created successfully!")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("Freelancer table already exists!")
        else:
            print(f"Error creating freelancer table: {e}")

    # Create jobs table
    try:
        job_table = dynamodb.create_table(
            TableName='jobs',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'N'  # Number
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("Creating Jobs table...")
        job_table.meta.client.get_waiter('table_exists').wait(TableName='jobs')
        print("Jobs table created successfully!")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("Jobs table already exists!")
        else:
            print(f"Error creating jobs table: {e}")

    # Create applications table
    try:
        application_table = dynamodb.create_table(
            TableName='applications',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'  # String
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("Creating Applications table...")
        application_table.meta.client.get_waiter('table_exists').wait(TableName='applications')
        print("Applications table created successfully!")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("Applications table already exists!")
        else:
            print(f"Error creating applications table: {e}")

def seed_initial_data():
    # Seed initial job data
    job_table = dynamodb.Table('jobs')
    
    # Check if jobs table is empty
    response = job_table.scan(
        ProjectionExpression="id",
        Limit=1
    )
    
    if not response.get('Items'):
        print("Seeding initial job data...")
        initial_jobs = [
            {
                "id": 1, 
                "title": "Website Developer Needed", 
                "description": "Build a freelance job portal using Flask and Bootstrap.",
                "skills": "Python, Flask, HTML, CSS",
                "contact_email": "hr@example.com",
                "contact_phone": "+1 (123) 456-7890",
                "created_at": datetime.now().isoformat()
            },
            {
                "id": 2, 
                "title": "UI/UX Designer", 
                "description": "Redesign our client dashboard for better usability.",
                "skills": "Figma, Adobe XD, CSS",
                "contact_email": "design@example.com",
                "contact_phone": "+1 (987) 654-3210",
                "created_at": datetime.now().isoformat()
            }
        ]
        
        for job in initial_jobs:
            job_table.put_item(Item=job)
        print("Initial job data seeded successfully!")
    else:
        print("Jobs table already contains data, skipping seed.")

if __name__ == "__main__":
    print("Initializing DynamoDB tables...")
    create_tables()
    seed_initial_data()
    print("Database initialization complete!")