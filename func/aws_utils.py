import os
import boto3
import logging
from func.constants import AWS_S3_BUCKET, AWS_S3_REGION, AWS_S3_ACCESS_KEY, AWS_S3_SECRET_KEY

logger = logging.getLogger(__name__)

# AWS S3 Configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_S3_ACCESS_KEY,
    aws_secret_access_key=AWS_S3_SECRET_KEY
)

def upload_to_s3(file, filename):
    try:
        s3_client.upload_fileobj(
            file,
            AWS_S3_BUCKET,
            filename,
            ExtraArgs={'ACL': 'public-read'}
        )
        return f"https://{AWS_S3_BUCKET}.s3.{AWS_S3_REGION}.amazonaws.com/{filename}"
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise