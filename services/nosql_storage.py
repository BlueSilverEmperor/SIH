import os
import json
import base64
import datetime
import re
from django.conf import settings
from core.models import Project, FieldInput, Blueprint3D

# Optional PyMongo import
try:
    import pymongo
    HAS_PYMONGO = True
except ImportError:
    HAS_PYMONGO = False


def sanitize_nosql_table_name(project_name_or_code):
    """
    Cleans project name to create a valid NoSQL collection/table name.
    Replaces spaces and special characters with underscores.
    Example: 'Skyline Commercial Tower - Phase 1' -> 'Skyline_Commercial_Tower___Phase_1'
    """
    if not project_name_or_code:
        return "default_project_table"
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(project_name_or_code))
    return cleaned


def get_nosql_table_name_for_project(project_id):
    """
    Returns NoSQL table name matching the project name/code.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return "unknown_project_table"
    return sanitize_nosql_table_name(project.name)


def get_mongodb_collection(table_name):
    """
    Attempts to connect to MongoDB server if available.
    Returns (client, collection) tuple or (None, None).
    """
    if not HAS_PYMONGO:
        return None, None
    mongo_uri = os.environ.get('NOSQL_DB_URI', 'mongodb://localhost:27017/')
    try:
        client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=500)
        client.admin.command('ping')
        db = client['constructflow_nosql_db']
        return client, db[table_name]
    except Exception:
        return None, None


def get_embedded_nosql_dir():
    """
    Returns path to local embedded NoSQL database storage directory.
    """
    base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
    nosql_dir = os.path.join(base_dir, 'nosql_db')
    os.makedirs(nosql_dir, exist_ok=True)
    return nosql_dir


def save_document_to_embedded_nosql(table_name, doc):
    """
    Saves document into local embedded NoSQL JSON database file for the project table.
    """
    nosql_dir = get_embedded_nosql_dir()
    db_file = os.path.join(nosql_dir, f"{table_name}.json")

    documents = []
    if os.path.exists(db_file):
        try:
            with open(db_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
        except Exception:
            documents = []

    # Check if doc with same file_path already exists, update if found
    existing_idx = None
    for idx, d in enumerate(documents):
        if d.get('rel_file_path') == doc.get('rel_file_path') or d.get('doc_id') == doc.get('doc_id'):
            existing_idx = idx
            break

    if existing_idx is not None:
        documents[existing_idx] = doc
    else:
        documents.append(doc)

    with open(db_file, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2)

    return True


def get_documents_from_embedded_nosql(table_name):
    """
    Reads documents from local embedded NoSQL JSON database for the project table.
    """
    nosql_dir = get_embedded_nosql_dir()
    db_file = os.path.join(nosql_dir, f"{table_name}.json")
    if not os.path.exists(db_file):
        return []
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_file_to_nosql(project_id, relative_file_path, file_category, original_filename=None, notes=None, metadata=None):
    """
    Main API to save a file (invoice, photo, audio, 3D model, text log) into the project's NoSQL table.
    Encodes file bytes into base64 payload and builds structured NoSQL document.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {'success': False, 'error': 'Project not found'}

    table_name = sanitize_nosql_table_name(project.name)

    base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
    abs_file_path = os.path.join(base_dir, relative_file_path.replace('/', os.sep))

    file_bytes_base64 = ""
    file_size = 0
    if os.path.exists(abs_file_path):
        try:
            file_size = os.path.getsize(abs_file_path)
            with open(abs_file_path, 'rb') as f:
                file_bytes_base64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            file_bytes_base64 = ""

    filename = original_filename or os.path.basename(relative_file_path)
    now_iso = datetime.datetime.now().isoformat()
    doc_id = f"{table_name}_{hash(relative_file_path) & 0xffffffff}"

    nosql_doc = {
        'doc_id': doc_id,
        'project_id': project.id,
        'project_name': project.name,
        'project_code': project.code,
        'nosql_table_name': table_name,
        'filename': filename,
        'rel_file_path': relative_file_path,
        'file_category': file_category,  # e.g., 'invoice', 'photo', 'audio', 'text_log', '3d_blueprint_model'
        'file_size_bytes': file_size,
        'notes': notes or '',
        'created_at': now_iso,
        'metadata': metadata or {},
        'file_payload_base64': file_bytes_base64[:200] + "...[TRUNCATED_FOR_VIEW]" if len(file_bytes_base64) > 200 else file_bytes_base64,
        'full_base64_stored': bool(file_bytes_base64)
    }

    # Attempt MongoDB first
    client, mongo_coll = get_mongodb_collection(table_name)
    stored_in = "embedded_json"
    if mongo_coll is not None:
        try:
            mongo_doc = dict(nosql_doc)
            mongo_doc['file_payload_base64'] = file_bytes_base64
            mongo_coll.update_one({'doc_id': doc_id}, {'$set': mongo_doc}, upsert=True)
            stored_in = "mongodb"
        except Exception:
            stored_in = "embedded_json"
        finally:
            if client:
                client.close()

    # Always persist in embedded storage to guarantee reliability
    save_document_to_embedded_nosql(table_name, nosql_doc)

    nosql_doc['stored_in'] = stored_in
    return {
        'success': True,
        'table_name': table_name,
        'doc_id': doc_id,
        'filename': filename,
        'stored_in': stored_in,
        'document': nosql_doc
    }


def get_nosql_files_for_project(project_id):
    """
    Returns all file documents stored in the NoSQL table for the project.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return []

    table_name = sanitize_nosql_table_name(project.name)

    # Check MongoDB first
    client, mongo_coll = get_mongodb_collection(table_name)
    if mongo_coll is not None:
        try:
            docs = list(mongo_coll.find({}, {'_id': 0}))
            if docs:
                return docs
        except Exception:
            pass
        finally:
            if client:
                client.close()

    # Fallback to embedded storage
    return get_documents_from_embedded_nosql(table_name)



def sync_all_project_files_to_nosql(project_id):
    """
    Batch syncs all existing FieldInput records and Blueprint3D records into the project's NoSQL table.
    """
    project = Project.objects.filter(id=project_id).first()
    if not project:
        return {'success': False, 'error': 'Project not found', 'synced_count': 0}

    table_name = sanitize_nosql_table_name(project.name)
    synced_count = 0

    # 1. Sync FieldInputs (invoices, photos, audio, text logs)
    field_inputs = FieldInput.objects.filter(project_id=project_id)
    for fi in field_inputs:
        extractions = [e.to_dict() for e in fi.extractions.all()]
        meta = {
            'input_type': fi.input_type,
            'source_author': fi.source_author,
            'status': fi.status,
            'extractions_count': len(extractions),
            'extractions': extractions
        }
        res = save_file_to_nosql(
            project_id=project_id,
            relative_file_path=fi.file_path,
            file_category=fi.input_type,
            original_filename=fi.original_filename,
            notes=fi.notes,
            metadata=meta
        )
        if res.get('success'):
            synced_count += 1

    # 2. Sync 3D Blueprint Models
    blueprints = Blueprint3D.objects.filter(project_id=project_id)
    for bp in blueprints:
        meta = {
            'wall_count': bp.wall_count,
            'column_count': bp.column_count,
            'slab_area_sqm': bp.slab_area_sqm,
            'format': bp.format,
            'status': bp.status
        }
        res = save_file_to_nosql(
            project_id=project_id,
            relative_file_path=bp.model_file_path,
            file_category='3d_blueprint_model',
            original_filename=bp.source_filename,
            notes=f"Generated 3D Model: {bp.name}",
            metadata=meta
        )
        if res.get('success'):
            synced_count += 1

    return {
        'success': True,
        'project_id': project_id,
        'project_name': project.name,
        'table_name': table_name,
        'synced_count': synced_count,
        'files': get_nosql_files_for_project(project_id)
    }
