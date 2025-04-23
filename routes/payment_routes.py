# TODO: Review this code @shaikhasif69

from flask import Blueprint, request, jsonify
from func.oauth_utils import token_required
from func.models.user import User
from func.models.subscription import Subscription, get_plan
from func.payment_utils import execute_payment
from func.constants import SUPPORTED_PAYMENT_PROVIDERS
import logging

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')
logger = logging.getLogger(__name__)

@payment_bp.route('/subscription/<platform>/create', methods=['GET'])
@token_required
def create_subscription_route(user_id, platform):
    try:
        user = User.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 400
        
        plan_id = request.args.get('plan_id')
        
        if not platform or not plan_id:
            return jsonify({"error": "platform and plan_id are required"}), 400
        
        if platform not in SUPPORTED_PAYMENT_PROVIDERS:
            return jsonify({"error": "Unsupported payment provider"}), 400
        
        plan = get_plan(plan_id)
        if not plan:
            return jsonify({"error": "Plan not found"}), 400
        
        approval_url = Subscription.create(plan_id=plan_id, platform=platform)
        if approval_url:
            return jsonify({"approval_url": approval_url}), 200
        return jsonify({"error": "Failed to create subscription"}), 400
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occured, contact the admins!"}), 500

@payment_bp.route('/subscription/<platform>/success', methods=['GET'])
@token_required
def subscription_success_route(user_id, platform):
    try:
        if not platform:
            return jsonify({"error": "An error occured, contact the admins!"}), 500
        
        if platform not in SUPPORTED_PAYMENT_PROVIDERS:
            return jsonify({"error": "Unsupported payment provider"}), 400

        user = User.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 400
        
        token = None
        if platform == 'paypal':
            token = request.args.get('token')        
        elif platform == 'stripe':
            token = request.args.get('session_id')

        if not token:
            return jsonify({"error": "Token not found"}), 400
        
        if user.activate_subscription(token, platform):
            return jsonify({"message": "Subscription activated successfully!"}), 200
        return jsonify({"error": "Failed to activate subscription"}), 400
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return jsonify({"error": "An error occured, contact the admins!"}), 500
    
@payment_bp.route('/<platform>/success')
@token_required
def payment_success_route(user_id, platform):
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    token = request.args.get('token')

    amount = int(request.cookies.get('amount', 0))

    if execute_payment(platform, payment_id, payer_id):
        user = User.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Do action
        
        return jsonify({'message': 'Payment executed successfully!'}), 200
    return jsonify({"error": 'Contact admins to solve this error.'}), 401

@payment_bp.route('/cancel')
def cancel_route():
    return jsonify({"message": "Payment cancelled"}), 200