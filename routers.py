from flask import Blueprint, request, jsonify
from models import Users, Key, KeyHistory, Category, TransferRequest, key_category
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
    data       = request.get_json() or {}
    user_id    = data.get("user_id")
    key_id     = data.get("key_id")
    is_return  = data.get("return", False)

    user = Users.query.get(user_id)
    key  = Key.query.get(key_id)
    if not user or not key:
        return jsonify({"status":"error","message":"Invalid user_id or key_id"}), 400

    if not is_return and key.status is False:
        return jsonify({"status":"error","message":"Ключ уже выдан"}), 400

    if not is_return:
        # Проверяем категории пользователя и ключа
        user_cats = {cat.id for cat in user.categories}
        key_cats  = {cat.id for cat in key.categories}
        if key_cats and not (user_cats & key_cats) and not user.admin:
            return jsonify({
                "status": "error",
                "message": "У вас нет прав на запрос этого ключа"
            }), 403

    action_name = "request_return" if is_return else "request"
    new_hist    = KeyHistory(user_id=user_id, key_id=key_id, action=action_name)
    db.session.add(new_hist)
    db.session.commit()

    msg = "Запрос на сдачу ключа отправлен" if is_return else "Запрос на получение ключа отправлен"
    return jsonify({"status":"success","message": msg}), 200

@api_blueprint.route('/pending-requests', methods=['GET'])
@cross_origin()
def pending_requests():
    records = (KeyHistory.query
               .filter(KeyHistory.action.in_(["request", "request_return"]))
               .order_by(KeyHistory.timestamp.desc())
               .all())
    result = []
    for r in records:
        # Replace used_key with direct Key query
        key = Key.query.get(r.key_id)
        key_name = f"{key.corpus}.{key.cab}" if key else "??"
        result.append({
            "history_id": r.id,
            "user_id"   : r.user_id,
            "user_name" : r.user.fio if r.user else "??",
            "key_id"    : r.key_id,
            "key_name"  : key_name,
            "timestamp" : r.timestamp.strftime("%d.%m.%Y %H:%M"),
            "action"    : r.action
        })
    return jsonify({"status":"success","requests":result}), 200

@api_blueprint.route('/approve-request', methods=['POST'])
@cross_origin()
def approve_request():
    data = request.get_json()
    hist_id = data.get("history_id")
    record = KeyHistory.query.get(hist_id)
    if not record:
        return jsonify({"status":"error","message":"No such request"}),404
    if record.action not in ("request", "request_return"):
        return jsonify({"status":"error","message":"Not a pending request"}),400
    # Get key directly instead of using record.used_key
    key = Key.query.get(record.key_id)
    
    if record.action == "request":
        record.action = "issue"
        if key:
            key.status = False
        message = "Ключ выдан"
    else:                                     
        record.action = "return"
        if key:
            key.status = True
        message = "Ключ принят и помещён в шкаф"
    db.session.commit()
    return jsonify({"status":"success","message": message}),200

@api_blueprint.route('/deny-request', methods=['POST'])
@cross_origin()
def deny_request():
    data = request.get_json()
    hist_id = data.get("history_id")
    record = KeyHistory.query.get(hist_id)
    if not record:
        return jsonify({"status":"error","message":"No such request"}),404
    if record.action not in ("request", "request_return"):
        return jsonify({"status":"error","message":"Not a pending request"}),400

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
    # Get key directly instead of using last_record.used_key
    key_obj = Key.query.get(key_id)
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
        key_id=key_id,
        status='pending'
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
    """Эндпоинт для получения списка всех пользователей с их категориями."""
    try:
        users = Users.query.all()
        users_list = []
        for user in users:
            # ... (existing code for finding current_key_name) ...
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
                 # Get key directly instead of using last_issued_key_record.used_key
                 key = Key.query.get(last_issued_key_record.key_id)
                 if not subsequent_action and key:
                      current_key_name = f"{key.corpus}.{key.cab}"
             # ...rest of existing code...
             # Get user's categories
             user_categories = [{"id": cat.id, "name": cat.category} for cat in user.categories]
             users_list.append({
                "id": user.id,
                "name": user.fio,
                "status": "Admin" if user.admin else "Active",
                "key": current_key_name,
                "phone": user.number,
                "categories": user_categories # Add categories to the response
            })
        return jsonify({"status": "success", "users": users_list}), 200
    except Exception as e:
        db.session.rollback() # Rollback in case of error during processing
        print(f"Error fetching users: {e}") # Log the error
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500

@api_blueprint.route('/users/<int:user_id>', methods=['PUT'])
@cross_origin()
def update_user(user_id):
    """Эндпоинт для обновления данных пользователя, включая категории."""
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных для обновления"}), 400
        # Update name/login
        if 'name' in data and data['name']:
            user.fio = data['name']
            # Consider if 'number' (login) should also be updated based on 'name'
            # user.number = data['name']
        # Update password
        if 'password' in data and data['password']:
            # !! Add password hashing here in a real application !!
            user.password = data['password']
        # Update phone number if provided
        if 'phone' in data: # Check if 'phone' key exists
             user.number = data['phone'] # Assuming phone maps to number field
        # Update categories
        if 'category_ids' in data: # Check if category_ids are provided
            category_ids = data['category_ids']
            if isinstance(category_ids, list): # Ensure it's a list
                 # Fetch Category objects based on the provided IDs
                 categories_to_assign = Category.query.filter(Category.id.in_(category_ids)).all()
                 user.categories = categories_to_assign # Replace existing categories
            else:
                 # Handle potential error if category_ids is not a list
                 return jsonify({"status": "error", "message": "category_ids должен быть списком"}), 400
        if 'admin' in data:
            user.admin = bool(data['admin'])
            
        db.session.commit()
        # Fetch updated user categories to return
        updated_categories = [{"id": cat.id, "name": cat.category} for cat in user.categories]
        return jsonify({
            "status": "success", 
            "message": "Данные пользователя обновлены",
            "user": { # Optionally return updated user data
                 "id": user.id,
                 "name": user.fio,
                 "phone": user.number,
                 "status": "Admin" if user.admin else "Active",
                 "categories": updated_categories
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating user {user_id}: {e}") # Log the error
        return jsonify({"status": "error", "message": f"Ошибка при обновлении: {str(e)}"}), 500
        return jsonify({
            "message": "Данные пользователя обновлены",
            "user": {
                "id": user.id,
                "name": user.fio,
                "phone": user.number,
                "status": "Admin" if user.admin else "Active",
                "categories": updated_categories
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating user {user_id}: {e}") # Log the error
        return jsonify({"status": "error", "message": f"Ошибка при обновлении: {str(e)}"}), 500

@api_blueprint.route('/users', methods=['POST'])
@cross_origin()
def create_user():
    """Эндпоинт для создания нового пользователя с категориями."""
    data = request.get_json() or {}
    name = data.get('name')
    password = data.get('password')
    phone = data.get('phone') # Get phone number
    category_ids = data.get('category_ids', []) # Get category IDs, default to empty list
    if not name:
        return jsonify({"status":"error","message":"Имя пользователя не может быть пустым"}), 400
    # Password might be optional for creation, adjust if needed
    # if not password:
    #     return jsonify({"status":"error","message":"Пароль не может быть пустым"}), 400
    if not phone:
         return jsonify({"status":"error","message":"Телефон не может быть пустым"}), 400
    # Check if user with this phone number already exists
    existing_user = Users.query.filter_by(number=phone).first()
    if existing_user:
        return jsonify({"status": "error", "message": f"Пользователь с телефоном {phone} уже существует"}), 409 # 409 Conflict
    try:
        # Use phone as the 'number' (login) field
        admin_flag = data.get('admin', False)
        new_user = Users(fio=name, number=phone, password=password if password else '', admin=bool(admin_flag)) # Handle potentially empty password
        # Fetch and assign categories
        if category_ids and isinstance(category_ids, list):
             categories_to_assign = Category.query.filter(Category.id.in_(category_ids)).all()
             new_user.categories = categories_to_assign
        db.session.add(new_user)
        db.session.commit()
        # Get assigned categories for the response
        assigned_categories = [{"id": cat.id, "name": cat.category} for cat in new_user.categories]
        
        return jsonify({
            "status":"success",
            "message":"Пользователь создан",
            "user":{
                "id":new_user.id,
                "name":new_user.fio,
                "phone": new_user.number,
                "status": "Admin" if new_user.admin else "Active",
                "categories": assigned_categories
            }
        }), 201 # 201 Created status code
    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {e}") # Log the error
        # Check for specific database errors like unique constraint violation if needed
        return jsonify({"status":"error","message":f"Ошибка при создании пользователя: {str(e)}"}), 500

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
            # Get key directly instead of using record.used_key
            key = Key.query.get(record.key_id)
            if key:
                 history_list.append({
                    "history_id": record.id, # Use history_id for consistency
                    "key_id": record.key_id,
                    "key_name": f"{key.corpus}.{key.cab}",
                    "action": record.action,
                    "timestamp": record.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ") # ISO format often preferred by JS Date
                    # Fix Russian 'М' to 'M'
                })
        return jsonify({
            "status": "success",
            "history": history_list
        }), 200
    except Exception as e:
        print(f"Error fetching key history for user {user_id}: {e}") # Log the error
        return jsonify({"status": "error",
                "message": f"Ошибка при получении истории: {str(e)}"}), 500

@api_blueprint.route('/categories', methods=['GET'])
@cross_origin()
def get_categories():
    """Endpoint to get all categories from the database"""
    try:
        categories_query = Category.query.all()
        categories_list = [{"id": cat.id, "name": cat.category} for cat in categories_query] # Use cat.category based on model
        return jsonify({
            "status": "success",
            "categories": categories_list
        })
    except Exception as e:
        print(f"Error fetching categories: {e}")  # Log the error
        return jsonify({"status": "error", "message": f"Ошибка при получении категорий: {str(e)}"}), 500

@api_blueprint.route('/categories', methods=['POST'])
@cross_origin()
def create_category():
    """Endpoint to create a new category"""
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "Имя категории не может быть пустым"}), 400
        # Save the new category to the database
        # Assuming the column name is 'category' as per the model definition
        new_category = Category(category=data.get('name')) 
        db.session.add(new_category)
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Категория создана успешно",
            "category": {"id": new_category.id, "name": new_category.category} # Return actual ID and name
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error creating category: {e}") # Log the error
        return jsonify({"status": "error", "message": f"Ошибка при создании категории: {str(e)}"}), 500
            
@api_blueprint.route('/categories/<int:category_id>', methods=['PUT', 'DELETE'])
@cross_origin()
def manage_category(category_id):
    """Endpoint to update or delete a category"""
    try:
        category = Category.query.get(category_id)
        if not category:
            return jsonify({"status": "error", "message": "Категория не найдена"}), 404

        if request.method == 'DELETE':
            # Delete logic
            db.session.delete(category)
            db.session.commit()
            return jsonify({"status": "success", "message": "Категория удалена"})
        
        else:  # PUT
            data = request.get_json()
            if not data or not data.get('name'):
                return jsonify({"status": "error", "message": "Имя категории не может быть пустым"}), 400
            
            # Update logic
            category.category = data.get('name') # Update the 'category' field
            db.session.commit()
            
            return jsonify({
                "status": "success", 
                "message": "Категория обновлена",
                "category": {"id": category.id, "name": category.category} # Return updated data
            })
    except Exception as e:
        db.session.rollback()
        print(f"Error managing category {category_id}: {e}") # Log the error
        return jsonify({"status": "error", "message": f"Ошибка при управлении категорией: {str(e)}"}), 500

@api_blueprint.route('/keys-with-categories', methods=['GET'])
@cross_origin()
def keys_with_categories():
    """Get all keys with their assigned categories"""
    try:
        keys = Key.query.all()
        keys_list = []
        for key in keys:
            # Fetch categories using the pre-defined relationship
            key_categories = []
            for category in key.categories:
                key_categories.append({"id": category.id, "name": category.category})
            # Get last history record for this key
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
                "key_name": f"{key.corpus}.{key.cab}",  # Форматированное имя ключа
                "categories": key_categories  # Add categories to the response
            })
        return jsonify({
            "status": "success",
            "keys": keys_list
        })      
    except Exception as e:
        print(f"Error fetching keys with categories: {e}")  # Log the error
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/keys/<int:key_id>/categories', methods=['PUT'])
@cross_origin()
def update_key_categories(key_id):
    """Update categories for a specific key"""
    try:
        key = Key.query.get(key_id)
        if not key:
            return jsonify({"status": "error", "message": "Ключ не найден"}), 404
        data = request.get_json()
        if not data or 'category_ids' not in data:
            return jsonify({"status": "error", "message": "Отсутствуют данные категорий"}), 400
        category_ids = data['category_ids']
        if not isinstance(category_ids, list):
            return jsonify({"status": "error", "message": "category_ids должен быть списком"}), 400
        # Get the categories and assign them directly using the relationship
        categories_to_assign = Category.query.filter(Category.id.in_(category_ids)).all()
        key.categories = categories_to_assign
        
        db.session.commit()
        # Use the updated relationship data
        updated_categories = [{"id": cat.id, "name": cat.category} for cat in key.categories]
        
        return jsonify({
            "status": "success",
            "message": "Категории ключа обновлены",
            "key": {
                "id": key.id,
                "key_name": f"{key.corpus}.{key.cab}",
                "categories": updated_categories
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating key categories for key {key_id}: {e}")  # Log the error
        return jsonify({"status": "error", "message": f"Ошибка при обновлении категорий: {str(e)}"}), 500

@api_blueprint.route('/available-keys-for-user/<int:user_id>', methods=['GET'])
@cross_origin()
def available_keys_for_user(user_id):
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"status":"error","message":"Пользователь не найден"}), 404

        user_cats     = {cat.id for cat in user.categories}
        all_available = Key.query.filter_by(status=True).all()
        result        = []

        for key in all_available:
            key_cats = {cat.id for cat in key.categories}
            if user.admin or not key_cats or (user_cats & key_cats):
                result.append({
                    "id":        key.id,
                    "cab":       key.cab,
                    "corpus":    key.corpus,
                    "status":    key.status,
                    "available": key.status,
                    "key_name":  f"{key.corpus}.{key.cab}",
                    "categories":[{"id":c.id,"name":c.category} for c in key.categories]
                })

        return jsonify({"status":"success","keys":result}), 200

    except Exception as e:
        print(f"Error in available-keys-for-user: {e}")
        return jsonify({"status":"error","message":str(e)}), 500

@api_blueprint.route('/users/<int:user_id>', methods=['DELETE'])
@cross_origin()
def delete_user(user_id):
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404

        # вернуть все выданные пользователю ключи и записать в историю
        issued_keys = Key.query.filter_by(status=False).all()
        for key in issued_keys:
            last = KeyHistory.query.filter_by(key_id=key.id) \
                   .order_by(KeyHistory.timestamp.desc()).first()
            if last and last.user_id == user_id and last.action == 'issue':
                db.session.add(KeyHistory(user_id=user_id, key_id=key.id, action='return'))
                key.status = True

        # удалить всю историю ключей пользователя
        KeyHistory.query.filter_by(user_id=user_id).delete()

        # удалить все transfer-запросы, где участвует пользователь
        TransferRequest.query.filter(
            (TransferRequest.from_user_id == user_id) |
            (TransferRequest.to_user_id   == user_id)
        ).delete(synchronize_session=False)

        # обнулить ownership в категориях и очистить m2m
        Category.query.filter_by(user_id=user_id).update({"user_id": None})
        user.categories = []

        # удалить пользователя
        db.session.delete(user)
        db.session.commit()
        return jsonify({"status": "success", "message": "Пользователь и его данные удалены"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user {user_id}: {e}")
        return jsonify({"status": "error", "message": f"Ошибка при удалении пользователя: {str(e)}"}), 500
