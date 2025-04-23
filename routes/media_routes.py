from flask import Blueprint, request, jsonify, send_file
from func.models.media import Media, MediaType
from func.aws_utils import upload_to_s3
from func.utils import load_json, save_json, generate_random_string
from func.constants import MEDIA_FOLDER_PATH, MEDIA_JSON_FILE_PATH, USE_AWS_SERVICE

import logging
from werkzeug.utils import secure_filename
import os

media_bp = Blueprint('media', __name__, url_prefix='/media')
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@media_bp.route('/stream/<media_id>', methods=['GET'])
def stream_media(media_id):
    media = load_json(MEDIA_JSON_FILE_PATH)
    media_path = media.get(media_id)

    if not media_path:
        return jsonify({'error': 'Media not found'}), 404

    if not os.path.exists(media_path):
        # Delete the media record from the database
        media_obj = Media.from_url(f'/api/media/stream/{media_id}')
        if media_obj:
            media_obj.delete()

        # Remove the entry from the JSON file
        del media[media_id]
        save_json(media, MEDIA_JSON_FILE_PATH)

        return jsonify({'error': 'Media file not found on server'}), 404

    try:
        return send_file(media_path, as_attachment=False)
    except Exception as e:
        logger.error(f"Error streaming media {media_id}: {str(e)}")
        return jsonify({'error': 'Error streaming media'}), 500

@media_bp.route('/upload', methods=['POST'])
def upload_media():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
            
        # Determine media type
        ext = file.filename.rsplit('.', 1)[1].lower()
        media_type = MediaType.from_ext(ext)
            
        # Upload to S3
        filename = secure_filename(file.filename)

        if USE_AWS_SERVICE:
            url = upload_to_s3(file, filename)
        else:
            # Save the file locally in MEDIA_FOLDER_PATH and the URL should be /stream/id
            media = load_json(MEDIA_JSON_FILE_PATH)

            id = generate_random_string(
                length=10, 
                include_numbers=True, 
                include_ascii_letters=False, 
                include_special_chars=False
            )

            if not os.path.exists(MEDIA_FOLDER_PATH):
                os.makedirs(MEDIA_FOLDER_PATH)

            local_path = f'{MEDIA_FOLDER_PATH}/{id}.{ext}'
            file.save(local_path)

            media[id] = local_path
            save_json(media, MEDIA_JSON_FILE_PATH)

            url = f'/api/media/stream/{id}'
        
        # Create media record
        media_obj = Media.create(media_type=media_type, url=url)
        
        return jsonify(media_obj.to_dict()), 201
    except Exception as e:
        logger.error(f"Media upload failed: {str(e)}")
        return jsonify({'error': 'Server error uploading media'}), 500