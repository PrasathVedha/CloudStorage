from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import boto3
from botocore.exceptions import NoCredentialsError
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# AWS Configuration
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = os.getenv('S3_BUCKET_NAME')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    try:
        # List all files in the S3 bucket
        objects = s3.list_objects_v2(Bucket=S3_BUCKET)
        files = []
        if 'Contents' in objects:
            files = [obj['Key'] for obj in objects['Contents']]
        return render_template('index.html', files=files)
    except Exception as e:
        flash(f"Error accessing storage: {str(e)}")
        return render_template('index.html', files=[])

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        try:
            s3.upload_fileobj(
                file,
                S3_BUCKET,
                filename,
                ExtraArgs={'ACL': 'private'}  # Set files to private by default
            )
            flash('File uploaded successfully')
        except NoCredentialsError:
            flash('AWS credentials not available')
        except Exception as e:
            flash(f'Upload failed: {str(e)}')
    else:
        flash('File type not allowed')
    
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Generate a presigned URL for the file
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': filename},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        return redirect(url)
    except NoCredentialsError:
        flash('AWS credentials not available')
    except Exception as e:
        flash(f'Download failed: {str(e)}')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
