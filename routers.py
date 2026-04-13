from flask import Blueprint, request, jsonify
from models import Users, Key, KeyHistory, Category, TransferRequest, key_category, user_categories
from flask_cors import cross_origin
from services import db
from sqlalchemy import func
from sqlalchemy.orm import subqueryload
import json
import numpy as np
from face_service import get_embedding
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
            "user_id": user_record.id
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


@api_blueprint.route('/keys', methods=['GET'])
@cross_origin()
def all_keys():
    try:
        keys = Key.query.all()
        keys_list = []
        
        for key in keys:
            last_history = KeyHistory.query.filter_by(key_id=key.id).order_by(KeyHistory.timestamp.desc()).first()
            
            user_name = None
            user_id = None
            user_phone = None
            if last_history and last_history.user:
                user_name = last_history.user.fio
                user_id = last_history.user.id
                user_phone = last_history.user.number  # номер телефона пользователя

            # Добавляем категории ключа
            key_categories = [{"id": cat.id, "name": cat.category} for cat in key.categories]
                
            keys_list.append({
                "id": key.id,
                "cab": key.cab,
                "corpus": key.corpus,
                "status": key.status,
                "available": key.status,  # True = доступен, False = выдан
                "last_user": user_name,
                "last_user_id": user_id,
                "phone": user_phone,  # добавляем номер телефона
                "key_name": f"{key.corpus}.{key.cab}",
                "categories": key_categories,
                "user_count": len(key_categories)  # Примерное количество пользователей с доступом
            })
            
        return jsonify({
            "status": "success",
            "keys": keys_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_blueprint.route('/key-history', methods=['GET'])
@cross_origin()
def get_key_history():
    try:
        history_records = KeyHistory.query.order_by(KeyHistory.timestamp.desc()).all()
        
        history_list = []
        
        for record in history_records:
            key = Key.query.filter_by(id=record.key_id).first()
            user = Users.query.filter_by(id=record.user_id).first()
            
            if key and user:
                history_list.append({
                    "id": record.id,
                    "user_id": record.user_id,
                    "key_name": f"{key.corpus}.{key.cab}",
                    "user_name": user.fio if user else "Неизвестно",
                    "action": record.action,
                    "timestamp": record.timestamp.strftime("%d.%m.%Y %H:%M")
                })
            
        return jsonify({
            "status": "success",
            "history": history_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



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
                user_name = last_history.user.fio if last_history.user else None
                
                keys_list.append({
                    "id": key_obj.id,
                    "cab": key_obj.cab,
                    "corpus": key_obj.corpus,
                    "status": key_obj.status,
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
    data = request.get_json()
    user_id = data.get("user_id")
    key_id = data.get("key_id")
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
    key_obj = Key.query.get(key_id)
    if key_obj:
        key_obj.status = True
    db.session.commit()
    return jsonify({"status":"success","message":"Ключ сдан"}),200

@api_blueprint.route('/admin/return-key', methods=['POST'])
@cross_origin()
def admin_return_key():
    data = request.get_json()
    key_id = data.get("key_id")

    if not key_id:
        return jsonify({"status": "error", "message": "key_id is required"}), 400

    key = Key.query.get(key_id)
    if not key:
        return jsonify({"status": "error", "message": "Key not found"}), 404

    if key.status is True:
        return jsonify({"status": "error", "message": "Key is already available"}), 400

    # Find the last user who was issued the key
    last_issue_record = KeyHistory.query.filter_by(key_id=key_id, action='issue').order_by(KeyHistory.timestamp.desc()).first()
    
    if not last_issue_record:
        # This case is unlikely if key.status is False, but as a safeguard
        return jsonify({"status": "error", "message": "Could not find who this key was issued to"}), 404

    # Create a new history record for the return
    new_hist = KeyHistory(
        user_id=last_issue_record.user_id,
        key_id=key_id,
        action="return"
    )
    db.session.add(new_hist)
    
    # Update the key status
    key.status = True
    
    db.session.commit()
    
    return jsonify({"status": "success", "message": f"Ключ {key.corpus}.{key.cab} был возвращен администратором."}), 200

@api_blueprint.route('/transfer-request', methods=['POST'])
@cross_origin()
def create_transfer_request():
    data = request.get_json()
    print("Данные запроса:", data)
    from_user_id = data.get("from_user_id")
    to_user_id = data.get("to_user_id")
    key_id = data.get("key_id")
    print(f" from_user_id={from_user_id}, to_user_id={to_user_id}, key_id={key_id}")

    last_record = KeyHistory.query \
        .filter_by(key_id=key_id) \
        .order_by(KeyHistory.timestamp.desc()) \
        .first()
    if not last_record or last_record.user_id != from_user_id or last_record.action != "issue":
        return jsonify({"status": "error", "message": "Ключ не у этого пользователя"}), 400
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
    try:
        users = Users.query.all()
        users_list = []
        for user in users:
             last_issued_key_record = KeyHistory.query \
                .filter_by(user_id=user.id, action='issue') \
                .order_by(KeyHistory.timestamp.desc()) \
                .first()
             current_key_name = None
             if last_issued_key_record:
                 subsequent_action = KeyHistory.query \
                     .filter(KeyHistory.key_id == last_issued_key_record.key_id,
                             KeyHistory.timestamp > last_issued_key_record.timestamp,
                             KeyHistory.action.in_(['return', 'transfer'])) \
                     .first()
                 key = Key.query.get(last_issued_key_record.key_id)
                 if not subsequent_action and key:
                      current_key_name = f"{key.corpus}.{key.cab}"
             user_categories = [{"id": cat.id, "name": cat.category} for cat in user.categories]
             users_list.append({
                "id": user.id,
                "name": user.fio,
                "status": "Admin" if user.admin else "Active",
                "key": current_key_name,
                "phone": user.number,
                "categories": user_categories
            })
        return jsonify({"status": "success", "users": users_list}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error fetching users: {e}")
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500

@api_blueprint.route('/users/<int:user_id>', methods=['PUT'])
@cross_origin()
def update_user(user_id):
    try:
        user = Users.query.get(user_id)
        if not user:
            return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Нет данных для обновления"}), 400
        if 'name' in data and data['name']:
            user.fio = data['name']
        if 'password' in data and data['password']:
            user.password = data['password']
        if 'phone' in data:
             user.number = data['phone']
        if 'category_ids' in data:
            category_ids = data['category_ids']
            if isinstance(category_ids, list):
                 categories_to_assign = Category.query.filter(Category.id.in_(category_ids)).all()
                 user.categories = categories_to_assign
            else:
                 return jsonify({"status": "error", "message": "category_ids должен быть списком"}), 400
        if 'admin' in data:
            user.admin = bool(data['admin'])
            
        db.session.commit()
        updated_categories = [{"id": cat.id, "name": cat.category} for cat in user.categories]
        return jsonify({
            "status": "success", 
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
        print(f"Error updating user {user_id}: {e}")
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
        print(f"Error updating user {user_id}: {e}")
        return jsonify({"status": "error", "message": f"Ошибка при обновлении: {str(e)}"}), 500

@api_blueprint.route('/users', methods=['POST'])
@cross_origin()
def create_user():
    data = request.get_json() or {}
    name = data.get('name')
    password = data.get('password')
    phone = data.get('phone')
    category_ids = data.get('category_ids', [])
    if not name:
        return jsonify({"status":"error","message":"Имя пользователя не может быть пустым"}), 400
    if not phone:
         return jsonify({"status":"error","message":"Телефон не может быть пустым"}), 400
    existing_user = Users.query.filter_by(number=phone).first()
    if existing_user:
        return jsonify({"status": "error", "message": f"Пользователь с телефоном {phone} уже существует"}), 409
    try:
        admin_flag = data.get('admin', False)
        new_user = Users(fio=name, number=phone, password=password if password else '', admin=bool(admin_flag))
        if category_ids and isinstance(category_ids, list):
             categories_to_assign = Category.query.filter(Category.id.in_(category_ids)).all()
             new_user.categories = categories_to_assign
        db.session.add(new_user)
        db.session.commit()
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
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {e}")
        return jsonify({"status":"error","message":f"Ошибка при создании пользователя: {str(e)}"}), 500

@api_blueprint.route('/users/<int:user_id>/key-history', methods=['GET'])
@cross_origin()
def get_user_key_history(user_id):
    try:
        limit = request.args.get('limit', 5, type=int)
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
            key = Key.query.get(record.key_id)
            if key:
                 history_list.append({
                    "history_id": record.id,
                    "key_id": record.key_id,
                    "key_name": f"{key.corpus}.{key.cab}",
                    "action": record.action,
                    "timestamp": record.timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                })
        return jsonify({
            "status": "success",
            "history": history_list
        }), 200
    except Exception as e:
        print(f"Error fetching key history for user {user_id}: {e}")
        return jsonify({"status": "error",
                "message": f"Ошибка при получении истории: {str(e)}"}), 500

@api_blueprint.route('/categories', methods=['GET'])
@cross_origin()
def get_categories():
    try:
        # Correctly count associated keys and users via association tables
        categories_with_counts = db.session.query(
            Category,
            func.count(func.distinct(key_category.c.key_id)).label('keys_count'),
            func.count(func.distinct(user_categories.c.user_id)).label('user_count')
        ).outerjoin(key_category, Category.id == key_category.c.category_id)\
         .outerjoin(user_categories, Category.id == user_categories.c.category_id)\
         .group_by(Category.id)\
         .all()

        categories_list = []
        for category, keys_count, user_count in categories_with_counts:
            categories_list.append({
                "id": category.id,
                "name": category.category,
                "keys_count": keys_count,
                "user_count": user_count
            })

        return jsonify({
            "status": "success",
            "categories": categories_list
        })
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return jsonify({"status": "error", "message": f"Ошибка при получении категорий: {str(e)}"}), 500

@api_blueprint.route('/categories', methods=['POST'])
@cross_origin()
def create_category():
    try:
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "Имя категории не может быть пустым"}), 400
        new_category = Category(category=data.get('name')) 
        db.session.add(new_category)
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Категория создана успешно",
            "category": {"id": new_category.id, "name": new_category.category}
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error creating category: {e}")
        return jsonify({"status": "error", "message": f"Ошибка при создании категории: {str(e)}"}), 500
            
@api_blueprint.route('/categories/<int:category_id>', methods=['PUT', 'DELETE'])
@cross_origin()
def manage_category(category_id):
    try:
        category = Category.query.get(category_id)
        if not category:
            return jsonify({"status": "error", "message": "Категория не найдена"}), 404

        if request.method == 'DELETE':
            db.session.delete(category)
            db.session.commit()
            return jsonify({"status": "success", "message": "Категория удалена"})
        
        else:
            data = request.get_json()
            if not data or not data.get('name'):
                return jsonify({"status": "error", "message": "Имя категории не может быть пустым"}), 400
            
            category.category = data.get('name')
            db.session.commit()
            
            return jsonify({
                "status": "success", 
                "message": "Категория обновлена",
                "category": {"id": category.id, "name": category.category}
            })
    except Exception as e:
        db.session.rollback()
        print(f"Error managing category {category_id}: {e}")
        return jsonify({"status": "error", "message": f"Ошибка при управлении категорией: {str(e)}"}), 500

@api_blueprint.route('/keys-with-categories', methods=['GET'])
@cross_origin()
def keys_with_categories():
    try:
        keys = Key.query.all()
        keys_list = []
        for key in keys:
            key_categories = []
            for category in key.categories:
                key_categories.append({"id": category.id, "name": category.category})
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
                "available": key.status,
                "last_user": user_name,
                "last_user_id": user_id,
                "key_name": f"{key.corpus}.{key.cab}",
                "categories": key_categories
            })
        return jsonify({
            "status": "success",
            "keys": keys_list
        })      
    except Exception as e:
        print(f"Error fetching keys with categories: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@api_blueprint.route('/keys/<int:key_id>/categories', methods=['PUT'])
@cross_origin()
def update_key_categories(key_id):
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
        categories_to_assign = Category.query.filter(Category.id.in_(category_ids)).all()
        key.categories = categories_to_assign
        
        db.session.commit()
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
        print(f"Error updating key categories for key {key_id}: {e}")
        return jsonify({"status": "error", "message": f"Ошибка при обновлении категорий: {str(e)}"}), 500

@api_blueprint.route('/keys/bulk-update', methods=['PUT'])
@cross_origin()
def bulk_update_key_categories():
    try:
        data = request.get_json()
        if not data or 'key_ids' not in data or 'category_ids' not in data:
            return jsonify({"status": "error", "message": "Отсутствуют данные key_ids или category_ids"}), 400
        
        key_ids = data['key_ids']
        category_ids = data['category_ids']
        
        if not isinstance(key_ids, list) or not isinstance(category_ids, list):
            return jsonify({"status": "error", "message": "key_ids и category_ids должны быть списками"}), 400
        
        # Получаем ключи и категории
        keys = Key.query.filter(Key.id.in_(key_ids)).all()
        categories_to_assign = Category.query.filter(Category.id.in_(category_ids)).all()
        
        if len(keys) != len(key_ids):
            return jsonify({"status": "error", "message": "Некоторые ключи не найдены"}), 404
        
        # Обновляем категории для всех ключей
        for key in keys:
            key.categories = categories_to_assign
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Категории обновлены для {len(keys)} ключей",
            "updated_keys": len(keys)
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error bulk updating key categories: {e}")
        return jsonify({"status": "error", "message": f"Ошибка при массовом обновлении: {str(e)}"}), 500

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

        issued_keys = Key.query.filter_by(status=False).all()
        for key in issued_keys:
            last = KeyHistory.query.filter_by(key_id=key.id) \
                   .order_by(KeyHistory.timestamp.desc()).first()
            if last and last.user_id == user_id and last.action == 'issue':
                db.session.add(KeyHistory(user_id=user_id, key_id=key.id, action='return'))
                key.status = True

        KeyHistory.query.filter_by(user_id=user_id).delete()

        TransferRequest.query.filter(
            (TransferRequest.from_user_id == user_id) |
            (TransferRequest.to_user_id   == user_id)
        ).delete(synchronize_session=False)

        Category.query.filter_by(user_id=user_id).update({"user_id": None})
        user.categories = []

        db.session.delete(user)
        db.session.commit()
        return jsonify({"status": "success", "message": "Пользователь и его данные удалены"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user {user_id}: {e}")
        return jsonify({"status": "error", "message": f"Ошибка при удалении пользователя: {str(e)}"}), 500


@api_blueprint.route('/contact-info', methods=['GET'])
@cross_origin()
def get_contact_info():
    """Получить контактную информацию для администратора"""
    try:
        # Здесь можно добавить логику для получения из БД или конфига
        # Пока возвращаем статичные данные
        contact_info = {
            "phone": "+7710504939",
            "teacher_name": "Петров П.П",
            "email": "admin@aitu.edu.kz",  # дополнительно
            "office": "Кабинет 101"        # дополнительно
        }
        
        return jsonify({
            "status": "success",
            "phone": contact_info["phone"],
            "teacher_name": contact_info["teacher_name"],
            "email": contact_info.get("email"),
            "office": contact_info.get("office")
        })
        
    except Exception as e:
        print(f"Error getting contact info: {e}")
        return jsonify({
            "status": "error", 
            "message": f"Ошибка при получении контактной информации: {str(e)}"
        }), 500
    

@api_blueprint.route('/face-login', methods=['POST'])
def face_login():
    try:
        image = request.files.get('image')

        if not image:
            return jsonify({"status": "error", "message": "No image provided"}), 400

        embedding = get_embedding(image)

        if embedding is None:
            return jsonify({"status": "error", "message": "Face not detected"}), 400

        users = Users.query.all()

        best_match = None
        best_score = 0

        for user in users:
            if not user.face_embedding:
                continue

            stored_embedding = np.array(json.loads(user.face_embedding))

            score = np.dot(stored_embedding, embedding) / (
                np.linalg.norm(stored_embedding) * np.linalg.norm(embedding)
            )

            if score > best_score:
                best_score = score
                best_match = user

        if best_match and best_score > 0.5:
            return jsonify({
                "status": "success",
                "user_id": best_match.id,
                "name": best_match.fio,
                "score": float(best_score)
            }), 200

        return jsonify({
            "status": "error",
            "message": "User not recognized"
        }), 401

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
