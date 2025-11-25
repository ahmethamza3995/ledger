import hashlib
import re
import unicodedata
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.utils import timezone

ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def normalize_subcategory_name(name: str) -> str:
    s = (name or '').casefold()
    s = ''.join(ch for ch in s if not unicodedata.category(ch).startswith('P'))
    s = re.sub(r'\s+', '', s, flags=re.UNICODE)
    return s

def get_file_bytes(django_file) -> bytes:
    """
    FieldFile / UploadedFile / ContentFile fark etmeksizin güvenli biçimde byte döndürür.
    Dosya kapalıysa açar; okuma sonunda mümkünse imleci başa alır.
    """
    data = b''
    try:
        # Bazı UploadedFile tiplerinde .open gerekmeyebilir; dene:
        data = django_file.read()
    except Exception:
        # Kapalı olabilir; açıp tekrar dene
        try:
            django_file.open('rb')
            data = django_file.read()
        finally:
            try:
                django_file.close()
            except Exception:
                pass
    else:
        # İmleci sıfıra almayı dene (her zaman mümkün olmayabilir)
        try:
            django_file.seek(0)
        except Exception:
            pass
    if not data:
        raise ValueError("Invalid or empty file.")
    return data

def compute_content_hash(django_file) -> str:
    #dosyayı güvenli şekilde byte'a çevirip hashler
    data = get_file_bytes(django_file)
    return hashlib.sha256(data).hexdigest()

def hashed_receipt_path(django_file, dt=None) -> str:
    dt = dt or timezone.now()
    # Uzantıyı mevcut addan al; yoksa .bin
    ext = Path(getattr(django_file, 'name', '') or '').suffix.lower() or '.bin'
    file_hash = compute_content_hash(django_file)
    return f"receipts/{dt:%Y/%m}/{file_hash}{ext}"

def validate_image_file(django_file):
    size = getattr(django_file, 'size', None)
    if size and size > MAX_FILE_SIZE:
        raise ValueError("File too large (max 10MB).")
    data = get_file_bytes(django_file)  # kapalı/pozisyonu yanlış olsa da güvenli okur
    try:
        img = Image.open(BytesIO(data))
        img.verify()  # bozuk dosyayı yakalar
        fmt = Image.open(BytesIO(data)).format
    except Exception:
        raise ValueError("Invalid image file.")
    if fmt not in ALLOWED_IMAGE_FORMATS:
        raise ValueError("Only jpg/png/webp images are allowed.")

def make_thumbnail(django_file, width=320) -> ContentFile:
    data = get_file_bytes(django_file)
    img = Image.open(BytesIO(data))
    img = ImageOps.exif_transpose(img)
    img.thumbnail((width, width * 1000))
    out = BytesIO()
    img.save(out, format='WEBP', quality=85)
    return ContentFile(out.getvalue())
