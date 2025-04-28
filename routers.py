from flask import Blueprint, request, jsonify
from models import Users, Key, KeyHistory
from models import TransferRequest

from flask_cors import cross_origin
from app import db
api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/')
def index():
    return 'привет'

@api_blueprint.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user_input = data.get('user')
    password_input = data.get('password')

    user_record = Users.query.filter_by(number=user_input).first()
    if user_record and user_record.password == password_input:
        return jsonify({
            "status": "success",
            "message": "Добро пожаловать!",
            "code": 200,
            "admin": user_record.admin,
            "user_id": user_record.id  #обязательно!

        })
    else:
        return jsonify({"status": "error", "message": "Неверный логин или пароль"}), 401


@api_blueprint.route('/key-stats', methods=['GET'])
@cross_origin()
def key_stats():
    try:
        total_keys = Key.query.count()
        available_keys = Key.query.filter_by(status=True).count()       
        issued_keys = Key.query.filter_by(status=False).count()
        
        return jsonify({
            "status": "success",
            "total": total_keys,
            "available": available_keys,
            "issued": issued_keys
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Эндпоинт для получения списка всех ключей с их статусом
@api_blueprint.route('/keys', methods=['GET'])
@cross_origin()
def all_keys():
    try:
        keys = Key.query.all()
        keys_list = []
        
        for key in keys:
            # Для каждого ключа находим последнюю запись в истории
            last_history = KeyHistory.query.filter_by(key_id=key.id).order_by(KeyHistory.timestamp.desc()).first()
            
            user_name = None
            user_id = None
            if last_history and last_history.user:
                user_name = last_history.user.fio
                user_id = last_history.user.id

                
            keys_list.append({
                "id": key.id,
                "cab": key.cab,
                "corpus": key.corpus,
                "status": key.status,
                "available": key.status,  # True = доступен, False = выдан
                "last_user": user_name,
                "last_user_id": user_id,
                "key_name": f"{key.corpus}.{key.cab}"  # Форматированное имя ключа
            })
            
        return jsonify({
            "status": "success",
            "keys": keys_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Новый эндпоинт для получения истории ключей
@api_blueprint.route('/key-history', methods=['GET'])
@cross_origin()
def get_key_history():
    try:
        # Получаем историю ключей
        history_records = KeyHistory.query.order_by(KeyHistory.timestamp.desc()).all()
        
        history_list = []
        
        for record in history_records:
            # Получаем объект ключа и пользователя отдельно
            key = Key.query.filter_by(id=record.key_id).first()
            user = Users.query.filter_by(id=record.user_id).first()
            
            if key and user:
                history_list.append({
                    "id": record.id,
                    "user_id": record.user_id,
                    "key_name": f"{key.corpus}.{key.cab}",
                    "user_name": user.fio if user else "Неизвестно",
                    "action": record.action,
                    "timestamp": record.timestamp.strftime("%d.%m.%Y %H:%M")  # Исправлена русская буква М на английскую M
                })
            
        return jsonify({
            "status": "success",
            "history": history_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


   #список ключей конкретного пользователя
@api_blueprint.route('/my-keys', methods=['GET'])
@cross_origin()
def my_keys():
    try:
        user_id_str = request.args.get('user_id')
        if not user_id_str:
            return jsonify({"status": "error", "message": "user_id is required"}), 400
       
        user_id = int(user_id_str)
        issued_keys = Key.query.filter_by(status=False).all()
        keys_list = []

        for key_obj in issued_keys:
            last_history = KeyHistory.query \
                .filter_by(key_id=key_obj.id) \
                .order_by(KeyHistory.timestamp.desc()) \
                .first()

            if last_history and last_history.user_id == user_id:
                # Значит этот ключ сейчас у данного пользователя
                user_name = last_history.user.fio if last_history.user else None
                
                keys_list.append({
                    "id": key_obj.id,
                    "cab": key_obj.cab,
                    "corpus": key_obj.corpus,
                    "status": key_obj.status,      # False = выдан
                    "available": key_obj.status,   
                    "last_user": user_name,
                    "key_name": f"{key_obj.corpus}.{key_obj.cab}"
                })

        return jsonify({
            "status": "success",
            "keys": keys_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_blueprint.route('/request-key', methods=['POST'])
@cross_origin()
def request_key():

    data = request.get_json()
    user_id = data.get("user_id")
    key_id = data.get("key_id")

    user = Users.query.get(user_id)
    key_obj = Key.query.get(key_id)
    if not user or not key_obj:
        return jsonify({"status": "error", "message": "Invalid user_id or key_id"}), 400

    if key_obj.status == False:
        return jsonify({"status":"error","message":"Ключ уже выдан"}), 400

    new_hist = KeyHistory(
        user_id=user_id,
        key_id=key_id,
        action="request"
    )
    db.session.add(new_hist)
    db.session.commit()

    return jsonify({"status":"success","message":"Запрос на получение ключа отправлен"}),200


@api_blueprint.route('/pending-requests', methods=['GET'])
@cross_origin()
def pending_requests():

    try:
        records = KeyHistory.query.filter_by(action="request").order_by(KeyHistory.timestamp.desc()).all()
        result = []
        for r in records:
            user_name = r.user.fio if r.user else "??"
            key_name = f"{r.used_key.corpus}.{r.used_key.cab}" if r.used_key else "??"
            result.append({
                "history_id": r.id,
                "user_id": r.user_id,
                "user_name": user_name,
                "key_id": r.key_id,
                "key_name": key_name,
                "timestamp": r.timestamp.strftime("%d.%m.%Y %H:%M")
            })
        return jsonify({"status":"success","requests":result}),200
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}),500


@api_blueprint.route('/approve-request', methods=['POST'])
@cross_origin()
def approve_request():

    data = request.get_json()
    hist_id = data.get("history_id")

    record = KeyHistory.query.get(hist_id)
    if not record:
        return jsonify({"status":"error","message":"No such request"}),404

    if record.action != "request":
        return jsonify({"status":"error","message":"This history is not 'request'"}),400

    # Выдаём ключ
    record.action = "issue"
    if record.used_key:
        record.used_key.status = False  # ключ выдан
    db.session.commit()

    return jsonify({"status":"success","message":"Ключ выдан"}),200


@api_blueprint.route('/deny-request', methods=['POST'])
@cross_origin()
def deny_request():
    data = request.get_json()
    hist_id = data.get("history_id")

    record = KeyHistory.query.get(hist_id)
    if not record:
        return jsonify({"status":"error","message":"No such request"}),404

    if record.action != "request":
        return jsonify({"status":"error","message":"This history is not 'request'"}),400

    record.action = "denied"
    db.session.commit()

    return jsonify({"status":"success","message":"Запрос отклонён"}),200


@api_blueprint.route('/return-key', methods=['POST'])
@cross_origin()
def return_key():
    """
    Пользователь сдает ключ (action='return'), меняем key.status=True
    {
      "user_id":7,
      "key_id":15
    }
    """
    data = request.get_json()
    user_id = data.get("user_id")
    key_id = data.get("key_id")

    # Найдём последнюю запись, удостоверимся, что ключ действительно у user_id
    from sqlalchemy import desc
    last_record = KeyHistory.query \
        .filter_by(key_id=key_id) \
        .order_by(KeyHistory.timestamp.desc()) \
        .first()

    if not last_record or last_record.user_id != user_id or last_record.action != "issue":
        return jsonify({"status":"error","message":"Этот ключ сейчас не у вас"}),400

    new_hist = KeyHistory(
        user_id=user_id,
        key_id=key_id,
        action="return"
    )
    db.session.add(new_hist)
    key_obj = last_record.used_key
    if key_obj:
        key_obj.status = True

    db.session.commit()
    return jsonify({"status":"success","message":"Ключ сдан"}),200

@api_blueprint.route('/transfer-request', methods=['POST'])
@cross_origin()
def create_transfer_request():
    
    data = request.get_json()
    print("Данные запроса:", data)

    from_user_id = data.get("from_user_id")
    to_user_id = data.get("to_user_id")
    key_id = data.get("key_id")
    
    print(f" from_user_id={from_user_id}, to_user_id={to_user_id}, key_id={key_id}")

    # Проверим, что ключ действительно у from_user
    last_record = KeyHistory.query \
        .filter_by(key_id=key_id) \
        .order_by(KeyHistory.timestamp.desc()) \
        .first()

    if not last_record or last_record.user_id != from_user_id or last_record.action != "issue":
        return jsonify({"status": "error", "message": "Ключ не у этого пользователя"}), 400

    # Проверим, что нет уже pending-запроса
    existing = TransferRequest.query.filter_by(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        key_id=key_id,
        status='pending'
    ).first()

    if existing:
        return jsonify({"status": "error", "message": "Запрос уже отправлен"}), 400

    new_request = TransferRequest(
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        key_id=key_id
    )

    db.session.add(new_request)
    db.session.commit()

    return jsonify({"status": "success", "message": "Запрос на передачу отправлен"}), 200




@api_blueprint.route('/approve-transfer', methods=['POST'])
@cross_origin()
def approve_transfer():
    data = request.get_json()
    request_id = data.get("request_id")

    request_record = TransferRequest.query.get(request_id)
    if not request_record or request_record.status != "pending":
        return jsonify({"status": "error", "message": "Некорректный запрос"}), 400

    # Обновим историю
    new_hist = KeyHistory(
        user_id=request_record.to_user_id,
        key_id=request_record.key_id,
        action="transfer"
    )
    db.session.add(new_hist)

    request_record.status = "approved"
    db.session.commit()

    return jsonify({"status": "success", "message": "Ключ успешно передан"}), 200


@api_blueprint.route('/deny-transfer', methods=['POST'])
@cross_origin()
def deny_transfer():
    data = request.get_json()
    request_id = data.get("request_id")

    request_record = TransferRequest.query.get(request_id)
    if not request_record or request_record.status != "pending":
        return jsonify({"status": "error", "message": "Некорректный запрос"}), 400

    request_record.status = "denied"
    db.session.commit()

    return jsonify({"status": "success", "message": "Запрос отклонен"}), 200

@api_blueprint.route('/pending-transfers', methods=['GET'])
@cross_origin()
def pending_transfers():
    try:
        records = TransferRequest.query.filter_by(status="pending").order_by(TransferRequest.timestamp.desc()).all()
        result = []
        for r in records:
            key = Key.query.get(r.key_id)
            to_user = Users.query.get(r.to_user_id)
            result.append({
                "id": r.id,
                "key_id": r.key_id,
                "key_name": f"{key.corpus}.{key.cab}" if key else "??",
                "to_user_name": to_user.fio if to_user else "??",
                "from_user_id": r.from_user_id,
            })
        return jsonify({"status": "success", "requests": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/users', methods=['GET'])
@cross_origin()
def get_users():
    """Эндпоинт для получения списка всех пользователей."""
    try:
        users = Users.query.all()
        users_list = []
        for user in users:
            # Find the last key issued to this user, if any
            last_issued_key_record = KeyHistory.query \
                .filter_by(user_id=user.id, action='issue') \
                .order_by(KeyHistory.timestamp.desc()) \
                .first()

            current_key_name = None
            if last_issued_key_record:
                # Check if this key hasn't been returned or transferred since issue
                subsequent_action = KeyHistory.query \
                    .filter(KeyHistory.key_id == last_issued_key_record.key_id,
                            KeyHistory.timestamp > last_issued_key_record.timestamp,
                            KeyHistory.action.in_(['return', 'transfer'])) \
                    .first()
                if not subsequent_action and last_issued_key_record.used_key:
                     current_key_name = f"{last_issued_key_record.used_key.corpus}.{last_issued_key_record.used_key.cab}"


            users_list.append({
                "id": user.id,
                "name": user.fio,  # Assuming 'name' in frontend corresponds to 'fio'
                "status": "Admin" if user.admin else "Active", # Simple status logic
                "key": current_key_name, # Show currently held key if any
                "phone": user.number # Assuming 'phone' corresponds to 'number'
                # Add other fields if needed, like 'description' if it exists in your model
            })
        return jsonify({"status": "success", "users": users_list}), 200
    except Exception as e:
        print(f"Error fetching users: {e}") # Log the error
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500


@api_blueprint.route('/users/<int:user_id>', methods=['PUT'])
@cross_origin()
def update_user(user_id):
    """Эндпоинт для обновления данных пользователя (имя/логин, пароль)."""
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных для обновления"}), 400

        # Update name/login (assuming 'name' from frontend maps to 'fio')
        if 'name' in data and data['name']:
            user.fio = data['name']
            # If 'number' is used as login and should be updated too:
            # user.number = data['name'] # Uncomment if login = name

        # Update password only if provided and not empty
        if 'password' in data and data['password']:
            # Add password hashing here in a real application!
            user.password = data['password']

        db.session.commit()
        return jsonify({"status": "success", "message": "Данные пользователя обновлены"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating user {user_id}: {e}") # Log the error
        return jsonify({"status": "error", "message": f"Ошибка при обновлении: {str(e)}"}), 500


@api_blueprint.route('/users/<int:user_id>/key-history', methods=['GET'])
@cross_origin()
def get_user_key_history(user_id):
    """Эндпоинт для получения истории ключей конкретного пользователя."""
    try:
        limit = request.args.get('limit', 5, type=int) # Get limit from query param, default 5

        user = Users.query.get(user_id)
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404

        history_records = KeyHistory.query \
            .filter_by(user_id=user_id) \
            .order_by(KeyHistory.timestamp.desc()) \
            .limit(limit) \
            .all()

        history_list = []
        for record in history_records:
            key = record.used_key # Use relationship
            if key:
                 history_list.append({
                    "history_id": record.id, # Use history_id for consistency
                    "key_id": record.key_id,
                    "key_name": f"{key.corpus}.{key.cab}",
                    "action": record.action,
                    "timestamp": record.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ") # ISO format often preferred by JS Date
                    # "timestamp": record.timestamp.strftime("%d.%m.%Y %H:%M") # Alternative format
                })

        return jsonify({
            "status": "success",
            "history": history_list
        }), 200

    except Exception as e:
        print(f"Error fetching key history for user {user_id}: {e}") # Log the error
        return jsonify({"status": "error",
                "message": f"Ошибка при получении истории: {str(e)}"}), 500

@api_blueprint.route('/users', methods=['POST'])
@cross_origin()
def create_user():
    data = request.get_json() or {}
    name = data.get('name')
    password = data.get('password')
    if not name:
        return jsonify({"status":"error","message":"Имя пользователя не может быть пустым"}), 400
    if not password:
        return jsonify({"status":"error","message":"Пароль не может быть пустым"}), 400
    try:
        # Устанавливаем number = name как логин юзера
        new_user = Users(fio=name, number=name, password=password)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status":"success","message":"Пользователь создан","user":{"id":new_user.id,"name":new_user.fio}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status":"error","message":str(e)}), 500


