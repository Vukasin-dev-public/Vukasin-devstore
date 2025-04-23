from flask import Blueprint, request, jsonify, url_for
import logging

from func.models.user import User
from func.utils import validate_username, validate_email, validate_password, hash_password, verify_password
from func.oauth_utils import token_required

account_bp = Blueprint('account', __name__)
logger = logging.getLogger(__name__)

@account_bp.route('/profile/<username>', methods=['GET'])
@token_required
def get_user_profile(user_id, username):
    try:
        # Get the requesting user
        current_user = User.get(id=user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get the requested user profile
        user = User.get(username=username)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not current_user.is_following(user) and user.is_private:
            return jsonify({'error': 'User is private'}), 403
        
        # Check if the user is private and not the current user
        if current_user == user:
            return jsonify({"redirect": url_for('profile')})
                        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        return jsonify({'error': 'Server error while fetching user profile'}), 500
    
@account_bp.route('/profile', methods={'GET'})
@token_required
def get_current_user_profile(user_id):
    try:
        # Get the requesting user
        current_user = User.get(id=user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': current_user.to_dict(include_private=True)})
    
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        return jsonify({'error': 'Server error while fetching user profile'}), 500

@account_bp.route('/profile/edit', methods=['PUT'])
@token_required
def update_profile(user_id):
    try:
        user = User.get(id=user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        if 'bio' in data:
            user.bio = data['bio']
            
        if 'is_private' in data:
            user.is_private = bool(data['is_private'])
        
        # Username update requires validation
        if 'username' in data and data['username'] != user.username:
            new_username = data['username']
            
            # Validate username
            errors = user.change_username(new_username=new_username)
            if errors:
                return jsonify({'errors': errors}), 400
        
        # Email update requires validation
        if 'email' in data and data['email'] != user.email:
            new_email = data['email']

            # Validate username
            errors = user.change_email(new_email=new_email)
            if errors:
                return jsonify({'errors': errors}), 400
            
        user.save()
        
        return jsonify({'user': user.to_dict(include_private=True)}), 200
        
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return jsonify({'error': 'Server error while updating user profile'}), 500

@account_bp.route('/password', methods=['PUT'])
@token_required
def change_password(user_id):
    try:
        user = User.get(id=user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('current_password') or not data.get('new_password') or not data.get('confirm_password'):
            return jsonify({'error': 'Current password, new password, and confirmation are required'}), 400
        
        # Verify current password
        if not verify_password(data['current_password'], user.password_hash):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        if data['new_password'] != data['confirm_password']:
            return jsonify({'error': 'New passwords do not match'}), 400
        
        # Update password
        errors = user.change_password(new_password=data['new_password'])
        if errors:
            return jsonify({'errors': errors}), 400 
        
        return jsonify({'message': 'Password updated successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return jsonify({'error': 'Server error while changing password'}), 500
    
@account_bp.route('/followers', methods=['GET'])
@token_required
def get_followers(user_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({"followers": [follower.to_dict(minimized=True) for follower in user.followers]})
    
    except Exception as e:
        logger.error(f"Error fetching followers: {str(e)}")
        return jsonify({'error': 'Server error while followers'}), 500

@account_bp.route('/followers/requests', methods=['GET'])
@token_required
def get_follower_requests(user_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        accepted = request.args.get('accepted', "false").lower() == "true"
        return jsonify({"followers": [follower_request.to_dict(minimized=True) for follower_request in user.follower_requests(accepted=accepted)]})
    
    except Exception as e:
        logger.error(f"Error fetching follower requests: {str(e)}")
        return jsonify({'error': 'Server error while ollower requests'}), 500
    
@account_bp.route('/following', methods=['GET'])
@token_required
def get_following(user_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({"followers": [follower.to_dict(minimized=True) for follower in user.following]})
    
    except Exception as e:
        logger.error(f"Error fetching following: {str(e)}")
        return jsonify({'error': 'Server error while fetching following'}), 500

@account_bp.route('/following/requests', methods=['GET'])
@token_required
def get_following_requests(user_id):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        accepted = request.args.get('accepted', "false").lower() == "true"
        return jsonify({"followers": [following_request.to_dict(minimized=True) for following_request in user.following_requests(accepted=accepted)]})
    
    except Exception as e:
        logger.error(f"Error fetching following requests: {str(e)}")
        return jsonify({'error': 'Server error while fetching following requests'}), 500

@account_bp.route('/follow/<username>', methods=['POST'])
@token_required
def follow_user(user_id, username):
    try:
        # Get current user
        current_user = User.get(id=user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get target user
        target_user = User.get(username=username)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Can't follow yourself
        if current_user == target_user:
            return jsonify({'error': 'You cannot follow yourself'}), 400
        
        if target_user in current_user.following:
            return jsonify({'error': f'You are already following {username}'}), 400 
        
        # Follow the user
        if current_user.follow_user(target_user):
            return jsonify({'message': f'You have started following {username}'}), 200
        
        return jsonify({'message': f'Sent a friend request to {username}'}), 200
        
    except Exception as e:
        logger.error(f"Error following user: {str(e)}")
        return jsonify({'error': 'Server error while following user'}), 500
    
@account_bp.route('/follow/<username>/accept', methods=['PUT'])
@token_required
def accept_follow(user_id, username):
    try:
        # Get current user
        current_user = User.get(id=user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get target user
        target_user = User.get(username=username)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Can't follow yourself
        if current_user == target_user:
            return jsonify({'error': 'You cannot follow yourself'}), 400
        
        # Follow the user
        success = current_user.accept_follow(target_user)
        if not success:
            return jsonify({'error': f'{target_user.username} has not requested following you'}), 400
        
        return jsonify({'message': f"Accepted {username}'s follow request"}), 200
        
    except Exception as e:
        logger.error(f"Error following user: {str(e)}")
        return jsonify({'error': 'Server error while following user'}), 500

@account_bp.route('/unfollow/<username>', methods=['POST'])
@token_required
def unfollow_user(user_id, username):
    try:
        # Get current user
        current_user = User.get(id=user_id)
        if not current_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get target user
        target_user = User.get(username=username)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Can't follow yourself
        if current_user == target_user:
            return jsonify({'error': 'You cannot unfollow yourself'}), 400
        
        if target_user not in current_user.following:
            return jsonify({'error': f"You don't follow {username}"}), 400 
        
        # Unfollow the user
        current_user.unfollow_user(target_user)
        
        return jsonify({'message': f'Unfollowed {username}'}), 200
        
    except Exception as e:
        logger.error(f"Error unfollowing user: {str(e)}")
        return jsonify({'error': 'Server error while unfollowing user'}), 500

# Need some more work, to show friends first, then followings, then followers, then other users on the application
@account_bp.route('/search', methods=['GET'])
@token_required
def search_users(user_id):
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 10))
        
        if len(query) < 3:
            return jsonify({'results': []}), 200
        
        # Search for users by username prefix
        users = User.find_by_username_prefix(query, limit)
        
        return jsonify({'results': [user.to_dict(minimized=True) for user in users]}), 200
        
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        return jsonify({'error': 'Server error while searching users'}), 500

@account_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(user_id):
    try:
        user = User.get(id=user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        notifications = [notification.to_dict() for notification in user.notifications]
        return jsonify({'notifications': notifications}), 200

    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return jsonify({'error': 'Server error fetching notifications'}), 500
    
@account_bp.route('/notification/<notification_id>', methods=['GET'])
@token_required
def get_notification(user_id, notification_id):
    try:
        user = User.get(id=user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        for notification in user.notifications:
            if notification.id == notification_id:
                return jsonify({'notification': notification.to_dict()}), 200
            
        return jsonify({'error': 'Notification not found'}), 404

    except Exception as e:
        logger.error(f"Error fetching notification: {str(e)}")
        return jsonify({'error': 'Server error fetching notification'}), 500
    
@account_bp.route('/notification/<notification_id>/read', methods=['DELETE'])
@token_required
def read_notification(user_id, notification_id):
    try:
        user = User.get(id=user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        for notification in user.notifications:
            if notification.id == notification_id:
                notification.delete()
                return jsonify({'message': 'Notification read successfully'}), 200
            
        return jsonify({'error': 'Notification not found'}), 404

    except Exception as e:
        logger.error(f"Error reading notification: {str(e)}")
        return jsonify({'error': 'Server error reading notification'}), 500