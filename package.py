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
    #get the database object and store it
    db = get_db()
    #Execute a SQL query and store it's results
    packages = db.execute(
        'SELECT p.id, link,title, tagline, topics,active, created, modified, user_id, username'
        ' FROM package p JOIN user u ON p.user_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    #Execute a SQL query and store it's results
    votes = db.execute("SELECT package_id, count(user_id)  FROM vote GROUP BY package_id ").fetchall()

    #return the index template, passing two arguments
    return render_template('packages/index.html', packages=packages,votes=dict(votes))

@bp.route('/package/<packageName>')
def showPackage(packageName):
    #get the database object and store it
    db = get_db()
    #get a singular package by it's title
    package = get_package_by_title(packageName)
    #store the package directory path
    DIR = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package[2]))
    #count how many images are in the path
    numImages = len([name for name in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, name))]) 
    #Execute a SQL query and store it's results
    votes = db.execute("SELECT package_id, count(user_id)  FROM vote GROUP BY package_id ").fetchall()
    #return the package template, passing two arguments
    return render_template('packages/package.html', package=package, numImages = numImages,votes=dict(votes))



@bp.route('/static/<packageName>/<filetype>',  defaults={'id' : 1})
@bp.route('/static/<packageName>/<filetype>/<int:id>')
def package_image(packageName,filetype,id):
    #store a secured package name
    packageName = secure_filename(packageName)
    #determine whether the file is a thumbnail or a gallery image
    isGall =  filetype != "thumbnail" 
    current_app.logger.debug("Attempting to retrieve a" + " Gallary " if isGall else " Thumbnail " + " Image")
    current_app.logger.debug("Image Info: " + "\nPackage name: " + packageName + "\nFile Type: " + filetype + "\nID: " + str(id))
    current_app.logger.info("Directory: " + os.path.join(current_app.config['UPLOAD_FOLDER'], packageName,get_package_file(packageName, isGall, id)))
    #return a site url file path 
    return send_from_directory(os.path.join(current_app.config['PACKAGES_FOLDER'], packageName),get_package_file(packageName, isGall, id))


def get_package_file(package_name, isGall, id=1):
    current_app.logger.debug("Getting package file!")
    #Catch any OSError's that occur
    try:
        #Cycle through the specified package directory
        for file in os.listdir(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package_name))):
            current_app.logger.debug("Checking File: " + file)
            #if the current file is not gallery image
            if not isGall :
                #
                current_app.logger.debug("Thumbnail File selected")
                #check whether the current file is called thumbnail
                if (os.path.splitext(file)[0] == "thumbnail"):
                    current_app.logger.debug("Returns: "+  'thumbnail' +  os.path.splitext(file)[1] )
                    #reuturn the thumbnail with it's proper extension
                    return 'thumbnail' +  os.path.splitext(file)[1] 
            else:
                #store gallery file name
                gall_to_find = "gall_" + str(id)
                current_app.logger.debug("Gallary File selected")
                current_app.logger.debug("Returns: "+  gall_to_find + os.path.splitext(file)[1]  )
                #if the file matches the correct extension
                if os.path.splitext(file)[0] == gall_to_find:
                    #return the gallery with it's proper extension
                    return secure_filename(gall_to_find + os.path.splitext(file)[1])
    except OSError:
        #catch any OSError's that occur
        current_app.logger.error("An error has occured trying to access a file, file must not exist?")

    #If none of the above occurs, the file does not exist return a 404 error page
    abort(404)
        




@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    #Check if the request method is a post
    if request.method == 'POST':
        #Retrieve the posted information via reques.form
        link = request.form['link']
        title = request.form['title']
        tagline = request.form['tagline']
        topics = request.form['topics']
        description = request.form['description']
        active = request.form['active'] if 'active' in request.form else 1
        error = None

        #if the user did not upload a thumbnail file flash an error message and redirect back to the create page
        if 'thumbnail' not in request.files:
            flash('Thumbnail is required!')
            return redirect(request.url)
        #Check if all fields are filled
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
            #If the thumbnail is empty  flash an error message and redirect back to the create page
            if thumbnail.filename == '':
                flash('No selected file')
                return redirect(request.url)
            #if the thumbnail is proper and it is a allowed file store it in our specified upload folder
            if thumbnail and allowed_file(thumbnail.filename):
                filename = secure_filename(
                    'thumbnail') + os.path.splitext(thumbnail.filename)[1]
                os.mkdir(os.path.join(
                    current_app.config['UPLOAD_FOLDER'], secure_filename(title)))
                thumbnail.save(os.path.join(
                    current_app.config['UPLOAD_FOLDER'], secure_filename(title), filename))

            # Handle gallary images
            max_gallary_images = 4
            #cycle through checking if each gallery image is uploaded
            for num in range(1, max_gallary_images+1):
                gallary_item_name = 'gall_' + str(num)
                current_app.logger.debug(gallary_item_name + " is being uploaded" )
                if gallary_item_name not in request.files:
                    current_app.logger.debug(gallary_item_name + " is not in the request files..skipping..." )
                    continue
                #Store the gallery image in a file object
                gallary_item = request.files[gallary_item_name]
                if gallary_item.filename == '':
                    current_app.logger.warning("%s has attempted to upload an invalid gallary item...skipping..." % g.user['username'])
                    continue
                #If the gallery image is proper and is a allowed file, store it in our specified upload folder
                if gallary_item and allowed_file(gallary_item.filename):
                    current_app.logger.debug(gallary_item_name + " has been authenticated and is allowed...uploading..." )
                    filename = secure_filename(
                        gallary_item_name) + os.path.splitext(gallary_item.filename)[1]
                    gallary_item.save(os.path.join(
                        current_app.config['UPLOAD_FOLDER'], secure_filename(title), filename))
                current_app.logger.debug(gallary_item_name + ": Complete [" + str(num) + "]" )
            #Store our database object 
            db = get_db()
            #Execute and SQL query
            db.execute(
                'INSERT INTO package (link,title, tagline, topics,description,active, user_id)'
                ' VALUES (?, ?, ?,?,?, ?, ?)',
                (link, title, tagline, topics,description, active, g.user['id'])
            )
            #Commit our changes
            db.commit()
            #Redirect to our index page
            return redirect(url_for('package.index'))
    #if the user has not submitted anything, render our create page
    return render_template('packages/create.html')


def get_package(id, check_user=True):
    #Execute a SQL query, that finds a package by its id  only fetch one 
    packages = get_db().execute(
        'SELECT p.id, link,title, tagline, topics, description, active, created, modified, user_id, username'
        ' FROM package p JOIN user u ON p.user_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()
    #If the SQL query did not retrieve a package return a 404 because the package does not exist.
    if packages is None:
        abort(404, "Package id {0} doesn't exist.".format(id))


    #Return the package SQL object
    return packages

def get_package_by_title(title, check_user=True):
    #Execute a SQL query, that finds a package by its name and only fetch one
    packages = get_db().execute(
        'SELECT p.id, link,title, tagline, topics, description, active, created, modified, user_id, username'
        ' FROM package p JOIN user u ON p.user_id = u.id'
        ' WHERE p.title = ?',
        (title,)
    ).fetchone()
    #If the SQL query did not retrieve a package return a 404 because the package does not exist.
    if packages is None:
        abort(404, "Package id {0} doesn't exist.".format(id))

    #Return the package SQL object
    return packages

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    #Store our package to be updated
    package = get_package(id)

    #if the user has submitted
    if request.method == 'POST':
        #Store the form information
        link = request.form['link']
        title = request.form['title']
        tagline = request.form['tagline']
        topics = request.form['topics']
        active = request.form['active'] if 'active' in request.form else 1
        description = request.form['description']

        error = None

        #Check if all fields have been retrieved
        if not link:
            error = 'Link is required.'
        if not title:
            error = 'Title is required.'
        if not tagline:
            error = 'Tagline is required.'
        if not topics:
            error = 'Topics is required.'
        #Check if their is an error
        if error is not None:
            flash(error)
        else:
            #Store database object
            db = get_db()
            #Execute SQL Query
            db.execute(
                'UPDATE package SET link = ?, title = ?, tagline = ?, description = ?, topics= ?, active= ?'
                'WHERE id = ?',
                (link, title, tagline, description, topics, active, id)
            )
            #Commit changes
            db.commit()
            #Make sure to change the old package folder, incase the user changed the package name.
            os.rename(os.path.join(current_app.config['UPLOAD_FOLDER'],secure_filename(package[2])), os.path.join(current_app.config['UPLOAD_FOLDER'],secure_filename(title)) )
            #Redirect to index page
            return redirect(url_for('package.index'))
    #return the updatepage, passing one argument 
    return render_template('packages/update.html', package=package)

@bp.route('/<int:id>/update/images', methods=('GET', 'POST'))
@login_required
def updateImages(id):
    #Store our package to be updated
    package = get_package(id)
    #Store the package directory
    DIR = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package[2]))
    #Get how many images are in the package
    numImages = len([name for name in os.listdir(DIR) if os.path.isfile(os.path.join(DIR, name))]) 
   
    #If the user has submitted
    if request.method == 'POST':
        error = None
        #If there are errors
        if error is not None:
            flash(error)    
        else:
            #If the user decided to change the thumbnail file
            if 'thumbnail' in request.files:
                current_app.logger.debug("Thumbnail")
                # Handle thumbnail upload
                thumbnail = request.files['thumbnail']
                #If the thumbnail file is valid 
                if thumbnail.filename != '':
                    if thumbnail and allowed_file(thumbnail.filename):
                        #store the file name, and save the file to the specified package folder
                        filename = secure_filename('thumbnail') + os.path.splitext(thumbnail.filename)[1]
                        thumbnail.save(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package[2]), filename))

            
            # Handle gallary images
            max_gallary_images = 4
            #Cycle through the number of gallery images
            for num in range(1, max_gallary_images+1):
                #store the gallery image name
                gallary_item_name = 'gall_' + str(num)
                #if the user has checked the specified to delete gallary image
                if ('delete_gall_' + str(num)) in request.form:
                    #Delete the gallary image
                     clean_up_image(package[2], gallary_item_name)

                current_app.logger.debug(gallary_item_name + " is being uploaded" )
                
                if gallary_item_name not in request.files:
                    current_app.logger.debug(gallary_item_name + " is not in the request files..skipping..." )
                    continue
                #Store the gallary image file 
                gallary_item = request.files[gallary_item_name]
                if gallary_item.filename == '':
                    continue
                #If the gallery image is valid
                if gallary_item and allowed_file(gallary_item.filename):
                    current_app.logger.debug(gallary_item_name + " has been authenticated and is allowed...uploading..." )
                    #Store the file name, delete the old file and upload the new file to the specified packagage folder
                    filename = secure_filename(gallary_item_name) + os.path.splitext(gallary_item.filename)[1]

                    clean_up_image(package[2], gallary_item_name)

                    gallary_item.save(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package[2]), filename))
                current_app.logger.debug(gallary_item_name + ": Complete [" + str(num) + "]" )
            #redirect to the update images page, passing one argument
            return redirect(url_for('package.updateImages', id=id))
    #if the user has not submitted render the images page
    return render_template('packages/images.html',package=package,numImages=numImages)

@bp.route('/<int:id>/update/images/delete/<image>', methods=('POST',))
@login_required
def deleteImage(id,image):
    #Store the package that has the image
    pack = get_package(id)
    #Store the image to be delete
    imageToDelete = image
    #Delete the image
    clean_up_image(pack[2], image  )
    #Return to the previous requested page
    return redirect(request.url)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    #Get the package to be deleted
    pack = get_package(id)
    #Store the database object
    db = get_db()
    #Delete the package files
    clean_up_package(secure_filename(pack[2]))
    #Execute SQL query
    db.execute('DELETE FROM package WHERE id = ?', (id,))
    #Commit changes
    db.commit()
    #Return to the main page
    return redirect(url_for('package.index'))
    

def allowed_file(filename):
    #Check if the allowed file is in our specified config tuple
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower(
           ) in current_app.config['ALLOWED_EXTENSIONS']


def clean_up_image(package_name, file_name):
    #Catch any OSError's that occur
    try:
        #Cycle through the specified package folder
        for file in os.listdir(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package_name))):
            current_app.logger.warning("Compaing %s with %s" % (os.path.splitext(file)[0] , os.path.splitext(file)[0] ))
            #Check if the current file is the same file to be deleted
            if os.path.splitext(file)[0] == os.path.splitext(file_name)[0]:
                #delete the image
                os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package_name), secure_filename(file_name + os.path.splitext(file)[1])))
    #Catch any OSError's that occur        
    except OSError as e:
        current_app.logger.error("Error: %s - %s." % (e.filename, e.strerror))

def clean_up_package(package_name):
    #Catch any OSError's that occur
    try:
        #Delete the package folder
        shutil.rmtree(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(package_name)))
    #Catch any OSError's that occur
    except OSError as e:
        current_app.logger.error("Error: %s - %s." % (e.filename, e.strerror))



@bp.route('/vote/<int:user_id>/<int:id>')
def vote(user_id,  id):
    #Get package to be voted on
    package = get_package(id)
    #Store db object
    db = get_db()
    #Check if the user is logged in
    if g.user:
        #Executes a SQL query
        isValid = db.execute('SELECT user_id, package_id FROM VOTE WHERE user_id = ? AND package_id = ?', (user_id, id)).fetchone()
        #If the user has not voted
        if(isValid is None):
            current_app.logger.debug(g.user['username'] + " has not voted on " + package['title'])
            #Execute a SQL query
            db.execute('INSERT INTO vote (user_id, package_id) VALUES(?,?) ', (user_id, id))
            #Commit changes
            db.commit()
        else:
            current_app.logger.debug(g.user['username'] + " has not voted on " + package['title'])
            #Execute an SQL query
            db.execute('DELETE FROM vote WHERE user_id = ? AND package_id = ? ', (user_id, id))
            #Commit changes
            db.commit()
    #Redirect to previous page
    return redirect(redirect_url())


def redirect_url(default='index'):
    #Return previous redirect url
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)
    

