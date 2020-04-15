import os
import shutil
from flask import (Blueprint, flash, g, redirect, render_template, request, url_for, current_app,send_from_directory)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
from werkzeug.urls import url_fix
from pkghound.auth import login_required
from pkghound.db import get_db

bp = Blueprint('package', __name__)


@bp.route('/')
def index():
    db = get_db()
    packages = db.execute(
        'SELECT p.id, link,title, tagline, topics,active, created, modified, user_id, username'
        ' FROM package p JOIN user u ON p.user_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    votes = db.execute("SELECT package_id, count(user_id)  FROM vote GROUP BY package_id ").fetchall()

    return render_template('packages/index.html', packages=packages,votes=dict(votes))

@bp.route('/package/<packageName>')
def showPackage(packageName):
    db = get_db()
    package = get_package_by_title(packageName)
    DIR = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package[2]))

    numImages = len([name for name in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, name))]) 
    votes = db.execute("SELECT package_id, count(user_id)  FROM vote GROUP BY package_id ").fetchall()
    return render_template('packages/package.html', package=package, numImages = numImages,votes=dict(votes))

@bp.route('/static/<packageName>/<filetype>',  defaults={'id' : 1})
@bp.route('/static/<packageName>/<filetype>/<int:id>')
def package_image(packageName,filetype,id):
    packageName = secure_filename(packageName)
    isGall =  filetype != "thumbnail" 
    current_app.logger.debug("Attempting to retrieve a" + " Gallary " if isGall else " Thumbnail " + " Image")
    current_app.logger.debug("Image Info: " + "\nPackage name: " + packageName + "\nFile Type: " + filetype + "\nID: " + str(id))
    current_app.logger.info("Directory: " + os.path.join(current_app.config['UPLOAD_FOLDER'], packageName,get_package_file(packageName, isGall, id)))
    return send_from_directory(os.path.join(current_app.config['PACKAGES_FOLDER'], packageName),get_package_file(packageName, isGall, id))


def get_package_file(package_name, isGall, id=1):
    current_app.logger.debug("Getting package file!")
    try:
        for file in os.listdir(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package_name))):
            current_app.logger.debug("Checking File: " + file)
            if not isGall :
                current_app.logger.debug("Thumbnail File selected")
                if (os.path.splitext(file)[0] == "thumbnail"):
                    current_app.logger.debug("Returns: "+  'thumbnail' +  os.path.splitext(file)[1] )
                    return 'thumbnail' +  os.path.splitext(file)[1] 
            else:
                gall_to_find = "gall_" + str(id)
                current_app.logger.debug("Gallary File selected")
                current_app.logger.debug("Returns: "+  gall_to_find + os.path.splitext(file)[1]  )
            
                if os.path.splitext(file)[0] == gall_to_find:
                    return secure_filename(gall_to_find + os.path.splitext(file)[1])
    except OSError:
        current_app.logger.error("An error has occured trying to access a file, file must not exist?")
    
    abort(404)
        




@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        link = request.form['link']
        title = request.form['title']
        tagline = request.form['tagline']
        topics = request.form['topics']
        description = request.form['description']
        active = request.form['active'] if 'active' in request.form else 1
        error = None

        if 'thumbnail' not in request.files:
            flash('Thumbnail is required!')
            return redirect(request.url)

        if not link:
            error = 'Link is required.'
        if not title:
            error = 'Title is required.'
        if not tagline:
            error = 'Tagline is required.'
        if not topics:
            error = 'Topics is required.'
        if not description:
            error = 'Description is required.'
        if error is not None:
            flash(error)
        else:
            # if the package exist, remove it.
            clean_up_package(title)
            # Handle thumbnail upload
            thumbnail = request.files['thumbnail']
            if thumbnail.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if thumbnail and allowed_file(thumbnail.filename):
                filename = secure_filename(
                    'thumbnail') + os.path.splitext(thumbnail.filename)[1]
                os.mkdir(os.path.join(
                    current_app.config['UPLOAD_FOLDER'], secure_filename(title)))
                thumbnail.save(os.path.join(
                    current_app.config['UPLOAD_FOLDER'], secure_filename(title), filename))

            # Handle gallary images
            max_gallary_images = 4
            for num in range(1, 5):
                gallary_item_name = 'gall_' + str(num)
                current_app.logger.debug(gallary_item_name + " is being uploaded" )
                if gallary_item_name not in request.files:
                    current_app.logger.debug(gallary_item_name + " is not in the request files..skipping..." )
                    continue
                gallary_item = request.files[gallary_item_name]
                if gallary_item.filename == '':
                    current_app.logger.warning("%s has attempted to upload an invalid gallary item...skipping..." % g.user['username'])
                    continue
                if gallary_item and allowed_file(gallary_item.filename):
                    current_app.logger.debug(gallary_item_name + " has been authenticated and is allowed...uploading..." )
                    filename = secure_filename(
                        gallary_item_name) + os.path.splitext(gallary_item.filename)[1]
                    gallary_item.save(os.path.join(
                        current_app.config['UPLOAD_FOLDER'], secure_filename(title), filename))
                current_app.logger.debug(gallary_item_name + ": Complete [" + str(num) + "]" )

            db = get_db()
            db.execute(
                'INSERT INTO package (link,title, tagline, topics,description,active, user_id)'
                ' VALUES (?, ?, ?,?,?, ?, ?)',
                (link, title, tagline, topics,description, active, g.user['id'])
            )
            db.commit()
            return redirect(url_for('package.index'))

    return render_template('packages/create.html')


def get_package(id, check_user=True):
    packages = get_db().execute(
        'SELECT p.id, link,title, tagline, topics, description, active, created, modified, user_id, username'
        ' FROM package p JOIN user u ON p.user_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if packages is None:
        abort(404, "Package id {0} doesn't exist.".format(id))



    return packages

def get_package_by_title(title, check_user=True):
    packages = get_db().execute(
        'SELECT p.id, link,title, tagline, topics, description, active, created, modified, user_id, username'
        ' FROM package p JOIN user u ON p.user_id = u.id'
        ' WHERE p.title = ?',
        (title,)
    ).fetchone()

    if packages is None:
        abort(404, "Package id {0} doesn't exist.".format(id))


    return packages

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    package = get_package(id)

    if request.method == 'POST':
        link = request.form['link']
        title = request.form['title']
        tagline = request.form['tagline']
        topics = request.form['topics']
        active = request.form['active'] if 'active' in request.form else 1
        description = request.form['description']

        error = None

        if not link:
            error = 'Link is required.'
        if not title:
            error = 'Title is required.'
        if not tagline:
            error = 'Tagline is required.'
        if not topics:
            error = 'Topics is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE package SET link = ?, title = ?, tagline = ?, description = ?, topics= ?, active= ?'
                'WHERE id = ?',
                (link, title, tagline, description, topics, active, id)
            )
            db.commit()

            os.rename(os.path.join(current_app.config['UPLOAD_FOLDER'],secure_filename(package[2])), os.path.join(current_app.config['UPLOAD_FOLDER'],secure_filename(title)) )
            return redirect(url_for('package.index'))

    return render_template('packages/update.html', package=package)

@bp.route('/<int:id>/update/images', methods=('GET', 'POST'))
@login_required
def updateImages(id):
    package = get_package(id)
    DIR = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package[2]))

    numImages = len([name for name in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, name))]) 
   

    if request.method == 'POST':
        error = None
        if error is not None:
            flash(error)    
        else:
            if 'thumbnail' in request.files:
                current_app.logger.debug("Thumbnail")
                # Handle thumbnail upload
                thumbnail = request.files['thumbnail']
                if thumbnail.filename != '':
                    if thumbnail and allowed_file(thumbnail.filename):
                        filename = secure_filename('thumbnail') + os.path.splitext(thumbnail.filename)[1]
                        thumbnail.save(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package[2]), filename))

            
            # Handle gallary images
            max_gallary_images = 4
            for num in range(1, max_gallary_images+1):
                gallary_item_name = 'gall_' + str(num)

                if ('delete_gall_' + str(num)) in request.form:
                     clean_up_image(package[2], gallary_item_name)

                current_app.logger.debug(gallary_item_name + " is being uploaded" )
                if gallary_item_name not in request.files:
                    current_app.logger.debug(gallary_item_name + " is not in the request files..skipping..." )
                    continue
                gallary_item = request.files[gallary_item_name]
                if gallary_item.filename == '':
                    continue
                if gallary_item and allowed_file(gallary_item.filename):
                    current_app.logger.debug(gallary_item_name + " has been authenticated and is allowed...uploading..." )
                    filename = secure_filename(gallary_item_name) + os.path.splitext(gallary_item.filename)[1]

                    clean_up_image(package[2], gallary_item_name)

                    gallary_item.save(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package[2]), filename))
                current_app.logger.debug(gallary_item_name + ": Complete [" + str(num) + "]" )
            return redirect(url_for('package.updateImages', id=id))

    return render_template('packages/images.html',package=package,numImages=numImages)

@bp.route('/<int:id>/update/images/delete/<image>', methods=('POST',))
@login_required
def deleteImage(id,image):
    pack = get_package(id)
    imageToDelete = image
    clean_up_image(pack[2], image  )
    return redirect(request.url)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    pack = get_package(id)
    db = get_db()
    clean_up_package(secure_filename(pack[2]))
    db.execute('DELETE FROM package WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('package.index'))
    

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower(
           ) in current_app.config['ALLOWED_EXTENSIONS']


def clean_up_image(package_name, file_name):
    try:
        for file in os.listdir(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package_name))):
            current_app.logger.warning("Compaing %s with %s" % (os.path.splitext(file)[0] , os.path.splitext(file)[0] ))
            if os.path.splitext(file)[0] == os.path.splitext(file_name)[0]:
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package_name), secure_filename(file_name + os.path.splitext(file)[1])))
            
    except OSError as e:
        current_app.logger.error("Error: %s - %s." % (e.filename, e.strerror))

def clean_up_package(package_name):
    try:
        shutil.rmtree(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package_name)))
    except OSError as e:
        current_app.logger.error("Error: %s - %s." % (e.filename, e.strerror))

def get_packages():
    packages = {
        "Today": "",
        "Yesterday": "",
        "Yesterday": "",
        "PAST": "",
    }

    return packages

@bp.route('/vote/<int:user_id>/<int:id>')
def vote(user_id,  id):
    package = get_package(id)
    db = get_db()
    if g.user:
        isValid = db.execute('SELECT user_id, package_id FROM VOTE WHERE user_id = ? AND package_id = ?', (user_id, id)).fetchone()
        if(isValid is None):
            current_app.logger.debug(g.user['username'] + " has not voted on " + package['title'])
            db.execute('INSERT INTO vote (user_id, package_id) VALUES(?,?) ', (user_id, id))
            db.commit()
    return redirect(redirect_url())


def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)
    

