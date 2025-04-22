from flask import Flask, render_template, request, redirect, session, url_for, flash
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
freelancer_table = dynamodb.Table('freelancer')
job_table = dynamodb.Table('jobs')
application_table = dynamodb.Table('applications')

# Hardcoded clients
hardcoded_clients = {
    "admin1@example.com": {"name": "Admin One", "password": "1234", "role": "client"},
    "admin2@example.com": {"name": "Admin Two", "password": "1234", "role": "client"},
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        skills = request.form.get('skills', '')

        if not name or not email or not password or not role:
            flash('All fields are required.', 'error')
            return redirect(url_for('signup'))

        if role == 'client':
            flash('Client accounts are predefined. Please contact admin.', 'error')
            return redirect(url_for('signup'))

        try:
            response = freelancer_table.get_item(Key={'email': email})
            if 'Item' in response:
                flash('User already exists.', 'error')
                return redirect(url_for('signup'))

            freelancer_table.put_item(Item={
                'email': email,
                'name': name,
                'password': password,
                'role': role,
                'phone': '',
                'skills': skills
            })
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

        except ClientError as e:
            flash(f"Error accessing database: {e.response['Error']['Message']}", 'error')
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if role == 'client':
            client = hardcoded_clients.get(email)
            if client and client['password'] == password:
                session['logged_in'] = True
                session['username'] = client['name']
                session['role'] = role
                session['email'] = email
                return redirect(url_for('client_dashboard'))
            else:
                flash('Invalid credentials for client.', 'error')
                return redirect(url_for('login'))
        else:
            try:
                response = freelancer_table.get_item(Key={'email': email})
                user = response.get('Item')

                if user and user['password'] == password and user['role'] == role:
                    session['logged_in'] = True
                    session['username'] = user['name']
                    session['role'] = role
                    session['email'] = email
                    return redirect(url_for('freelancer_dashboard'))

                flash('Invalid credentials for freelancer.', 'error')
                return redirect(url_for('login'))

            except ClientError as e:
                flash(f"Error accessing database: {e.response['Error']['Message']}", 'error')
                return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/client/dashboard', methods=['GET', 'POST'])
def client_dashboard():
    if not session.get('logged_in') or session.get('role') != 'client':
        flash('Please login as client to access this page.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        skills = request.form['skills']
        contact_email = request.form['contact_email']
        contact_phone = request.form.get('contact_phone', '')
        
        if title and description and skills and contact_email:
            try:
                # Get the highest job ID to increment
                response = job_table.scan(
                    ProjectionExpression="id",
                )
                items = response.get('Items', [])
                job_id = 1
                if items:
                    job_id = max(int(item['id']) for item in items) + 1
                
                # Add new job to DynamoDB
                job_table.put_item(Item={
                    "id": job_id,
                    "title": title,
                    "description": description,
                    "skills": skills,
                    "contact_email": contact_email,
                    "contact_phone": contact_phone,
                    "created_at": datetime.now().isoformat()
                })
                flash('Job posted successfully!', 'success')
            except ClientError as e:
                flash(f"Error saving job: {e.response['Error']['Message']}", 'error')
    
    # Get jobs from DynamoDB for this client
    try:
        response = job_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('contact_email').eq(session.get('email'))
        )
        jobs = response.get('Items', [])
    except ClientError as e:
        flash(f"Error retrieving jobs: {e.response['Error']['Message']}", 'error')
        jobs = []

    return render_template('client_dashboard.html', 
                         username=session['username'],
                         jobs=jobs)

@app.route('/freelancer/dashboard')
def freelancer_dashboard():
    if not session.get('logged_in') or session.get('role') != 'freelancer':
        flash('Please login as freelancer to access this page.', 'error')
        return redirect(url_for('login'))

    # Get all jobs from DynamoDB
    try:
        response = job_table.scan()
        jobs = response.get('Items', [])
    except ClientError as e:
        flash(f"Error retrieving jobs: {e.response['Error']['Message']}", 'error')
        jobs = []
    
    # Get applications for this freelancer
    try:
        response = application_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('freelancer_email').eq(session['email'])
        )
        applications = response.get('Items', [])
        
        # Create a set of job IDs that the freelancer has applied to
        applied_job_ids = {int(app['job_id']) for app in applications}
        
        # Get details of applied jobs
        applied_jobs = []
        for job_id in applied_job_ids:
            response = job_table.get_item(Key={'id': job_id})
            if 'Item' in response:
                job = response['Item']
                # Find the matching application
                for app in applications:
                    if int(app['job_id']) == job_id:
                        job['application'] = app
                        break
                applied_jobs.append(job)
                
    except ClientError as e:
        flash(f"Error retrieving applications: {e.response['Error']['Message']}", 'error')
        applied_jobs = []
        applied_job_ids = set()

    return render_template('freelancer_dashboard.html', 
                         username=session['username'], 
                         jobs=jobs,
                         applied_jobs=applied_jobs,
                         applied_job_ids=applied_job_ids)

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    if not session.get('logged_in') or session.get('role') != 'freelancer':
        flash('Please login as freelancer to apply for jobs.', 'error')
        return redirect(url_for('login'))
    
    # Get job from DynamoDB
    try:
        response = job_table.get_item(Key={'id': job_id})
        job = response.get('Item')
        if not job:
            flash('Job not found!', 'error')
            return redirect(url_for('freelancer_dashboard'))
    except ClientError as e:
        flash(f"Error retrieving job: {e.response['Error']['Message']}", 'error')
        return redirect(url_for('freelancer_dashboard'))
    
    # Get freelancer details
    try:
        freelancer_response = freelancer_table.get_item(Key={'email': session['email']})
        freelancer = freelancer_response.get('Item', {})
    except ClientError as e:
        flash(f"Error retrieving freelancer details: {e.response['Error']['Message']}", 'error')
        freelancer = {}

    # Check if already applied
    try:
        response = application_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('freelancer_email').eq(session['email']) & 
                          boto3.dynamodb.conditions.Attr('job_id').eq(job_id)
        )
        if response.get('Items'):
            flash('You have already applied for this job.', 'warning')
            return redirect(url_for('freelancer_dashboard'))
    except ClientError as e:
        flash(f"Error checking application status: {e.response['Error']['Message']}", 'error')
    
    if request.method == 'POST':
        phone = request.form.get('phone')
        cover_letter = request.form.get('cover_letter')
        skills = request.form.get('skills', freelancer.get('skills', ''))
        
        # Update freelancer details if changed
        try:
            freelancer_table.update_item(
                Key={'email': session['email']},
                UpdateExpression='SET phone = :phone, skills = :skills',
                ExpressionAttributeValues={
                    ':phone': phone,
                    ':skills': skills
                }
            )
        except ClientError as e:
            flash(f"Error updating profile: {e.response['Error']['Message']}", 'error')
            return redirect(request.url)
        
        # Save application to DynamoDB
        try:
            application_id = f"{session['email']}_{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            application_table.put_item(Item={
                'id': application_id,
                'job_id': job_id,
                'freelancer_email': session['email'],
                'freelancer_name': session['username'],
                'phone': phone,
                'skills': skills,
                'cover_letter': cover_letter,
                'applied_at': datetime.now().isoformat(),
                'status': 'Pending'
            })
            
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('application_success'))
        except ClientError as e:
            flash(f"Error saving application: {e.response['Error']['Message']}", 'error')
            return redirect(request.url)
    
    return render_template('apply_form.html', 
                         job=job,
                         freelancer=freelancer)

@app.route('/application/success')
def application_success():
    if not session.get('logged_in'):
        flash('Please login to view this page.', 'error')
        return redirect(url_for('login'))
    return render_template('application_success.html')

@app.route('/services')
def services():
    if not session.get('logged_in'):
        flash('Please login to view this page.', 'error')
        return redirect(url_for('login'))
    return render_template('service-details-1.html')

@app.route('/services2')
def services2():
    if not session.get('logged_in'):
        flash('Please login to view this page.', 'error')
        return redirect(url_for('login'))
    return render_template('service-details-2.html')

@app.route('/services3')
def services3():
    if not session.get('logged_in'):
        flash('Please login to view this page.', 'error')
        return redirect(url_for('login'))
    return render_template('service-details-3.html')

if __name__ == '__main__':
    app.run(debug=True)