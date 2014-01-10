from . import settings, utils
from .settings import (
    GENERATED_MEDIA_DIR,
    GENERATED_MEDIA_NAMES_FILE,
    MEDIA_GENERATORS)
from .utils import load_backend
from django.utils.http import urlquote
import os
import shutil
import json


def generate_media():
    if os.path.exists(GENERATED_MEDIA_DIR):
        shutil.rmtree(GENERATED_MEDIA_DIR)

    # This will make media_url() generate production URLs
    was_dev_mode = settings.MEDIA_DEV_MODE
    settings.MEDIA_DEV_MODE = False

    utils.NAMES = {}

    # attempt to load the old generated names file
    old_names = {}
    try:
        fp = open(GENERATED_MEDIA_NAMES_FILE, 'r')
    except IOError:
        pass
    else:
        try:
            old_names.update(json.loads(fp.read()))
        except ValueError:
            pass

    for backend_name in MEDIA_GENERATORS:
        backend = load_backend(backend_name)()
        for key, url, content in backend.get_output():
            fpath = settings.MEDIA_FOLDER + key

            try:
                modified_date = os.path.getmtime(fpath)
                size = os.path.getsize(fpath)
            except OSError:
                exists = False
            else:
                exists = True

            # check if the file has already been hashed
            if exists and key in old_names:
                old_data = old_names[key]
                modified = old_data['last_modified'] == modified_date
                same_size = old_data['size'] == size
                if same_size and not modified:
                    # this file has probably not been modified!
                    print "%s is same" % key
                    utils.NAMES[key] = old_data
                    continue

            version = backend.generate_version(key, url, content)
            if version:
                base, ext = os.path.splitext(url)
                url = '%s-%s%s' % (base, version, ext)

            path = os.path.join(GENERATED_MEDIA_DIR, url)
            parent = os.path.dirname(path)
            if not os.path.exists(parent):
                os.makedirs(parent)

            fp = open(path, 'wb')
            if isinstance(content, unicode):
                content = content.encode('utf8')
            fp.write(content)
            fp.close()

            utils.NAMES[key] = {
                'hashed_name': urlquote(url),
                'last_modified': modified_date,
                'size': size
            }

    settings.MEDIA_DEV_MODE = was_dev_mode

    # Generate a module with media file name mappings
    fp = open(GENERATED_MEDIA_NAMES_FILE, 'w')
    fp.write(json.dumps(utils.NAMES, indent=2))
    fp.close()
