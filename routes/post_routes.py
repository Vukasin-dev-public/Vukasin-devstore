from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from functools import wraps
import logging

from func.models.post import Post, PostComment
from func.models.interest import Interest
from func.models.user import User
from func.models.media import Media
from func.models.database import database
from func.constants import ADMIN_TOKEN
from func.oauth_utils import token_required, admin_required, inject_admin_request

post_bp = Blueprint('post', __name__, url_prefix='/post')
logger = logging.getLogger(__name__)

@post_bp.route('/all', methods=['GET'])
@admin_required
def get_all_posts():
    try:
        posts = database.select("SELECT id FROM posts")
        return jsonify([Post.get(post['id']).to_dict() for post in posts]), 200
    except Exception as e:
        logger.error(f"Error fetching posts: {str(e)}")
        return jsonify({'error': 'Server error fetching posts'}), 500
    
@post_bp.route('/<username>/all', methods=['GET'])
@token_required
@inject_admin_request
def get_user_posts(user_id, admin_request, username):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        post_user = User.get(username=username)
        if not post_user:
            return jsonify({'error': 'Post user not found'}), 404
        
        if not admin_request and not user.is_following(post_user) and post_user.is_private and user != post_user:
            return jsonify({'error': 'User is private'}), 403
        
        posts = user.posts
        return jsonify([post.to_dict() for post in posts]), 200 
    except Exception as e:
        logger.error(f"Error fetching posts for user {user_id}: {str(e)}")
        return jsonify({'error': 'Server error fetching posts'}), 500
    
@post_bp.route('/<username>/all', methods=['DELETE'])
@admin_required
def delete_user_posts(username):
    try:        
        user = User.get(username=username)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        posts = user.posts
        if not posts:
            return jsonify({'error': 'User has no posts'}), 403
        
        for post in posts:
            post.delete()

        return jsonify({'message': 'Deleted user posts'}), 200 
    except Exception as e:
        logger.error(f"Error deleting posts for user {username}: {str(e)}")
        return jsonify({'error': 'Server error fetching posts'}), 500

@post_bp.route('/', methods=['POST'])
@token_required
def create_post(user_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # Validate required fields
        required_fields = ['title', 'content']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        media_ids = data.get('media_ids', [])
        
        # Create post
        post = Post.create(
            user_id=user_id,
            title=data['title'],
            content=data['content']
        )
        
        # Process interests
        interest_ids = data.get('interests', [])
        for interest_id in interest_ids:
            interest = Interest.get(id=interest_id)
            if interest:
                post.add_interest(interest)
        
        # Link media to post
        for media_id in media_ids:
            if media_id:
                media = Media.get(media_id)
                if media:
                    post.add_media(media)
        
        return jsonify(post.to_dict()), 201
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}")
        return jsonify({'error': 'Server error creating post'}), 500

@post_bp.route('/<post_id>', methods=['GET'])
@token_required
@inject_admin_request
def get_post(user_id, admin_request, post_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        post_user = post.user
        if not admin_request and (not user.is_following(post_user) and post_user.is_private) and user != post_user:
            return jsonify({'error': 'Post is private'}), 403
        
        return jsonify(post.to_dict()), 200
    except Exception as e:
        logger.error(f"Error fetching post {post_id}: {str(e)}")
        return jsonify({'error': 'Server error fetching post'}), 500

@post_bp.route('/<post_id>', methods=['DELETE'])
@token_required
@inject_admin_request
def delete_post(user_id, admin_request, post_id):
    try:
        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        if not admin_request and post.user_id != user_id:
            return jsonify({'error': 'Unauthorized to delete this post'}), 403

        post.delete()
        return jsonify({'message': 'Post deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting post {post_id}: {str(e)}")
        return jsonify({'error': 'Server error deleting post'}), 500
    
@post_bp.route('/<post_id>/comment', methods=['POST'])
@token_required
def create_comment(user_id, post_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        content = data.get('content')
        if not content:
            return jsonify({'error': 'content is required'}), 400
            
        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        post_user = post.user
        if user.is_following(post_user) and post_user.is_private and user != post_user:
            return jsonify({'error': 'Post is private'}), 403
            
        comment = PostComment.create(
            user_id=user_id,
            post_id=post_id,
            content=content
        )
        return jsonify(comment.to_dict()), 201
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        return jsonify({'error': 'Server error creating comment'}), 500

@post_bp.route('/<post_id>/comments', methods=['GET'])
@token_required
@inject_admin_request
def get_post_comments(user_id, admin_request, post_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        post_user = post.user
        if not admin_request and not user.is_following(post_user) and post_user.is_private and user != post_user:
            return jsonify({'error': 'Post is private'}), 403
                
        return jsonify([comment.to_dict() for comment in post.comments]), 200
    except Exception as e:
        logger.error(f"Error fetching comments for post {post_id}: {str(e)}")
        return jsonify({'error': 'Server error fetching comments'}), 500

@post_bp.route('/<post_id>/comment/<comment_id>', methods=['GET'])
@token_required
def get_comment(user_id, post_id, comment_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        post_user = post.user
        if user.is_following(post_user) and post_user.is_private and user != comment.user and user != post_user:
            return jsonify({'error': 'Post is private'}), 403
            
        comment = PostComment.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 400
            
        if comment not in post.comments:
            not jsonify({'Comment doesnt belong to post'}), 400
            
        return jsonify(comment.to_dict()), 201
    except Exception as e:
        logger.error(f"Error fetching comment: {str(e)}")
        return jsonify({'error': 'Server error fetching comment'}), 500
    
@post_bp.route('/<post_id>/comment/<comment_id>', methods=['PUT'])
@token_required
@inject_admin_request
def edit_comment(user_id, admin_request, post_id, comment_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        comment = PostComment.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404

        if comment.post_id != post.id:
            return jsonify({'error': 'Comment does not belong to the specified post'}), 400

        if not admin_request and user != comment.user:
            return jsonify({'error': 'Unauthorized to edit this comment'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400

        content = data.get('content')
        if not content:
            return jsonify({'error': 'Content is required'}), 400

        comment.content = content
        comment.save()

        return jsonify({'message': 'Comment updated successfully', 'comment': comment.to_dict()}), 200
    except Exception as e:
        logger.error(f"Error editing comment {comment_id}: {str(e)}")
        return jsonify({'error': 'Server error editing comment'}), 500
    
@post_bp.route('/<post_id>/comment/<comment_id>', methods=['DELETE'])
@token_required
@inject_admin_request
def delete_comment(user_id, admin_request, post_id, comment_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        comment = PostComment.get(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404

        if comment.post_id != post.id:
            return jsonify({'error': 'Comment does not belong to the specified post'}), 400

        if not admin_request and user != comment.user and user != post.user_id:
            return jsonify({'error': 'Unauthorized to delete this comment'}), 403

        comment.delete()
        return jsonify({'message': 'Comment deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {str(e)}")
        return jsonify({'error': 'Server error deleting comment'}), 500
    
@post_bp.route('/<post_id>/interests', methods=['GET'])
@token_required
@inject_admin_request
def get_post_interests(user_id, admin_request, post_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        post_user = post.user
        if not admin_request and not user.is_following(post_user) and post_user.is_private and user != post_user:
            return jsonify({'error': 'Post is private'}), 403
        
        return jsonify([interest.to_dict() for interest in post.interests]), 200
    except Exception as e:
        logger.error(f"Error fetching interests for post {post_id}: {str(e)}")
        return jsonify({'error': 'Server error fetching interests'}), 500

@post_bp.route('/<post_id>/user', methods=['GET'])
@token_required
@inject_admin_request
def get_post_user(user_id, admin_request, post_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        post = Post.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        post_user = post.user
        if not post_user:
            return jsonify({'error': 'User not found'}), 404
        
        # if not user.is_following(post_user) and post_user.is_private:
        #     return jsonify({'error': 'User is private'}), 403

        if user == post_user:
            admin_request = True
            
        return jsonify(user.to_dict(include_private=admin_request)), 200
    except Exception as e:
        logger.error(f"Error fetching user for post {post_id}: {str(e)}")
        return jsonify({'error': 'Server error fetching user'}), 500
    