import os
from core.models import FieldInput, Project

ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a', 'ogg'}
ALLOWED_TEXT_EXTENSIONS = {'txt', 'log', 'csv'}

def get_input_type_from_filename(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in ALLOWED_PHOTO_EXTENSIONS:
        return 'photo'
    elif ext in ALLOWED_PDF_EXTENSIONS:
        return 'invoice_pdf'
    elif ext in ALLOWED_AUDIO_EXTENSIONS:
        return 'audio_dictation'
    elif ext in ALLOWED_TEXT_EXTENSIONS:
        return 'text_log'
    return 'text_log'

def save_uploaded_file(file_obj, upload_folder, input_type=None):
    """
    Saves an uploaded file to appropriate subfolder and returns relative file path.
    """
    raw_name = getattr(file_obj, 'name', None) or getattr(file_obj, 'filename', '')
    if not file_obj or raw_name == '':
        raise ValueError("No file provided or filename is empty.")

    filename = os.path.basename(raw_name)
    if not input_type:
        input_type = get_input_type_from_filename(filename)

    subfolder = 'photos'
    if input_type == 'invoice_pdf':
        subfolder = 'invoices'
    elif input_type == 'audio_dictation':
        subfolder = 'audio'
    elif input_type == 'text_log':
        subfolder = 'text_logs'

    target_dir = os.path.join(upload_folder, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    dest_path = os.path.join(target_dir, filename)
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
        counter += 1

    if hasattr(file_obj, 'chunks'):
        with open(dest_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
    elif hasattr(file_obj, 'save'):
        file_obj.save(dest_path)
    else:
        with open(dest_path, 'wb+') as destination:
            destination.write(file_obj.read())

    rel_path = os.path.relpath(dest_path, start=os.path.dirname(upload_folder)).replace('\\', '/')
    return rel_path, os.path.basename(dest_path), input_type

from services.nosql_storage import save_file_to_nosql

def create_field_input(project_id, file_obj, upload_folder, notes=None, source_author='Site Inspector', forced_type=None):
    """
    Handles file saving and DB insertion of FieldInput record.
    """
    rel_path, secure_name, detected_type = save_uploaded_file(file_obj, upload_folder, input_type=forced_type)
    project = Project.objects.filter(id=project_id).first()

    field_input = FieldInput.objects.create(
        project=project,
        input_type=detected_type,
        file_path=rel_path,
        original_filename=secure_name,
        notes=notes,
        source_author=source_author,
        status='pending_review'
    )

    # Save into NoSQL project table
    try:
        save_file_to_nosql(
            project_id=project_id,
            relative_file_path=rel_path,
            file_category=detected_type,
            original_filename=secure_name,
            notes=notes,
            metadata={'source_author': source_author, 'status': 'pending_review'}
        )
    except Exception:
        pass

    return field_input

def create_text_log_input(project_id, text_content, upload_folder, notes=None, source_author='Site Inspector'):
    """
    Handles direct text log submission by saving to a text file.
    """
    subfolder = 'text_logs'
    target_dir = os.path.join(upload_folder, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"site_note_{FieldInput.objects.count() + 1}.txt"
    dest_path = os.path.join(target_dir, filename)
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(text_content)

    rel_path = os.path.relpath(dest_path, start=os.path.dirname(upload_folder)).replace('\\', '/')
    project = Project.objects.filter(id=project_id).first()

    field_input = FieldInput.objects.create(
        project=project,
        input_type='text_log',
        file_path=rel_path,
        original_filename=filename,
        notes=notes or text_content[:200],
        source_author=source_author,
        status='pending_review'
    )

    # Save into NoSQL project table
    try:
        save_file_to_nosql(
            project_id=project_id,
            relative_file_path=rel_path,
            file_category='text_log',
            original_filename=filename,
            notes=notes or text_content[:200],
            metadata={'source_author': source_author, 'status': 'pending_review'}
        )
    except Exception:
        pass

    return field_input

