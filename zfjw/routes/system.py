"""健康检查 接口。"""
from flask import Blueprint
from flask import jsonify




bp = Blueprint("system", __name__)


@bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "message": "ZFJW Backend API is running"})
