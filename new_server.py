from flask import Flask, render_template, url_for, request, session, redirect, send_from_directory
import os
import cv2
from werkzeug.utils import secure_filename
from flask_pymongo import PyMongo
from helpers import Helpers
from processor import Processor
import pytesseract
from PIL import Image
import io
import bcrypt
import datetime
import re
import zipfile

import glob

from google.cloud import vision
from google.cloud.vision import types

from utils import Service, encode_image

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
TEMP_FOLDER = os.path.join(APP_ROOT, 'temp_files')
FORM_IMAGES_FOLDER = os.path.join(APP_ROOT, 'form_image_files')

ALLOWED_EXTENSIONS = {'jpg', 'png', 'jpeg', 'zip'}

app.config['MONGO_DBNAME'] = 'deepblue'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/deepblue'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['FORM_IMAGES_FOLDER'] = FORM_IMAGES_FOLDER
app.secret_key = 'mysecret'


mongo = PyMongo(app)
predict_helper = Helpers()
processor = Processor()


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/aniruddh/PycharmProjects/main/misc/auth.json"
os.environ["VISION_API"] = "AIzaSyAKwLJ1A2Zr6YC1lyTJvJP1ez2eDL7rRiQ"

@app.route("/")
def hello():
    if 'username' in session:
        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        all_users = users.find()
        user_count = all_users.count()
        forms = mongo.db.forms
        all_forms = forms.find()
        form_count = all_forms.count()
        submissions = mongo.db.submissions
        all_subs = submissions.find()
        sub_count = all_subs.count()
        return render_template('index.html', user_type=user_type, user_count=user_count, form_count=form_count, sub_count=sub_count)
    else:
        return redirect('/userlogin')


@app.route('/submit', methods=['POST', 'GET'])
def submit():
    if 'username' in session:
        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        if user_type == 'admin':
            form = mongo.db.forms
            if request.method == 'POST':
                file = request.files['image_upload']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    fname = filename
                    full_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    fname_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    form_code = request.form.get('form_code')
                    preprocess = request.form.get('type')
                    #if str(preprocess) == 'no':
                    w, h, file_n = processor.get_details(form_code, full_path)
                    #else:
                    # w, h, file_n = processor.scan_form(form_code, full_path)
                    download_link = '/downloads/%s' % file_n
                    description = request.form.get('description')
                    form.insert(
                        {'code': str(form_code), 'static_url': str(download_link), 'description': description, 'width': str(w),
                         'height': str(h)})

                    redir = '/confirm/%s' % form_code
                    return redirect(redir)
            return render_template('new_form.html', user_type=user_type)
        else:
            return render_template('500.html')
    else:
        return redirect('/userlogin')


@app.route('/confirm/<form_code>', methods=['POST', 'GET'])
def confirm(form_code):
    if 'username' in session:
        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        form = mongo.db.forms
        current_form = form.find_one({'code': form_code})
        current_width = current_form['width']
        current_height = current_form['height']
        image_path = current_form['static_url']
        return render_template('new_form_confirm.html', static_url=image_path, form_width=current_width,
                               form_height=current_height, user_type=user_type)
    else:
        return redirect('/userlogin')


@app.route('/delete_form/<form_code>', methods=['POST', 'GET'])
def delete_form(form_code):
    if 'username' in session:
        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        if user_type == 'admin':
            forms = mongo.db.forms
            sections = mongo.db.sections
            submissions = mongo.db.submissions
            forms.delete_many({'code': form_code})
            sections.delete_many({'form': form_code})
            submissions.delete_many({'form_code':form_code})
            return redirect('/view_forms')


@app.route('/submission', methods=['POST', 'GET'])
def submission():
    if 'username' in session:
        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        form = mongo.db.forms
        submissions = mongo.db.submissions
        sections = mongo.db.sections
        forms = form.find()
        form_code = []
        if forms.count() > 0:
            for f in forms:
                code = f['code']
                form_code.append(code)

        formlist = range(0, forms.count(), 1)

        if request.method == 'POST':
            file = request.files['image_upload']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                fname = filename
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                fname_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                f_code = request.form.get('form_code')
                f_sections = []

                find_form = form.find_one({'code' : f_code})
                f_width = int(find_form['width'])
                f_height = int(find_form['height'])
                find_f_sections = sections.find({'form': f_code})
                if find_f_sections.count() > 0:
                    for section in find_f_sections:
                        section_name = section['section_name']
                        f_sections.append(section_name)


                section_values = []

                #_, _, new_file = processor.get_details(f_code, full_path)
                new_file = full_path
                img = cv2.imread(new_file)
                img = cv2.resize(img, (f_width, f_height))
                #cv2.imshow("im", img)
                #cv2.waitKey(0)
                # predict words
                for section in f_sections:
                    find_section = sections.find_one({'section_name': section, 'form': f_code})
                    x1 = int(find_section['x1'])
                    x2 = int(find_section['x2'])
                    y1 = int(find_section['y1'])
                    y2 = int(find_section['y2'])
                    section_type = str(find_section['type'])
                    crop_img = img[y1:y2, x1:x2]
                    #cv2.imshow("im", crop_img)
                    #cv2.waitKey(0)

                    final_filename = '%s/section_scanned_%s.jpg' % (TEMP_FOLDER, section)
                    cv2.imwrite(final_filename, crop_img)
                    #detect_text(final_filename)

                    if section_type == 'text':
                        section_value = predict_helper.predict(crop_img, section_type)
                        detected_text = detect_text(final_filename)
                        if detected_text == 'failed':
                            detected_text = section_value
                        detected_text = detected_text.upper()
                        section_values.append(detected_text)
                    if section_type == 'Number':
                        section_value = predict_helper.predict(crop_img, section_type)
                        detected_text = detect_text(final_filename)
                        if detected_text == 'failed':
                            detected_text = section_value
                        section_values.append(detected_text)
                    elif section_type == 'image':
                        filename
                        section_filename = '%s/section_scanned_%s.jpg' % (FORM_IMAGES_FOLDER, section)
                        cv2.imwrite(section_filename, crop_img)
                        link = '/form_images/section_scanned_%s.jpg' % section
                        section_values.append(link)

                date = str(datetime.date.today())
                timestamp = str(datetime.datetime.now().strftime('%H:%M:%S'))
                stamp = '%s-%s' % (date, timestamp)
                sub_name = '%s_%s' % (timestamp, f_code)
                submissions.insert({'fields': f_sections, 'values': section_values, 'form_code' : f_code, 'name': sub_name, 'time' : stamp})
                return redirect('/submission')

        return render_template('submission_platform.html', form_code=form_code, formlist=formlist, user_type=user_type)
    else:
        return redirect('/userlogin')

@app.route('/submission_batch', methods=['POST', 'GET'])
def submission_batch():
    if 'username' in session:
        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        form = mongo.db.forms
        submissions = mongo.db.submissions
        submissions_batch = mongo.db.submissions_batch
        sections = mongo.db.sections
        forms = form.find()
        form_code = []
        if forms.count() > 0:
            for f in forms:
                code = f['code']
                form_code.append(code)

        formlist = range(0, forms.count(), 1)

        if request.method == 'POST':
            file = request.files['image_upload']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                fname = filename
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                fname_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                f_code = request.form.get('form_code')
                f_sections = []

                find_form = form.find_one({'code' : f_code})
                f_width = int(find_form['width'])
                f_height = int(find_form['height'])
                find_f_sections = sections.find({'form': f_code})
                if find_f_sections.count() > 0:
                    for section in find_f_sections:
                        section_name = section['section_name']
                        f_sections.append(section_name)


               
                #_, _, new_file = processor.get_details(f_code, full_path)
                
                zip_ref = zipfile.ZipFile(full_path, 'r')
                zip_ref.extractall(os.path.join(APP_ROOT, 'unzips', filename))
                zip_ref.close()

                unzip_location = os.path.join(APP_ROOT, 'unzips', filename)

                types = ('*.jpg')
                jpg_files = glob.glob( os.path.join(unzip_location, '*.jpg'))
                jpg_files.sort()

                for jpg_file in jpg_files:
                    section_values = []
                    print("Current working with {}".format(jpg_file))
                    new_file = jpg_file
                    img = cv2.imread(new_file)
                    img = cv2.resize(img, (f_width, f_height))
                    #cv2.imshow("im", img)
                    #cv2.waitKey(0)
                    # predict words
                    for section in f_sections:
                        print("Working with section {}".format(section))
                        find_section = sections.find_one({'section_name': section, 'form': f_code})
                        x1 = int(find_section['x1'])
                        x2 = int(find_section['x2'])
                        y1 = int(find_section['y1'])
                        y2 = int(find_section['y2'])
                        section_type = str(find_section['type'])
                        crop_img = img[y1:y2, x1:x2]
                        #cv2.imshow("im", crop_img)
                        #cv2.waitKey(0)

                        final_filename = '%s/section_scanned_%s.jpg' % (TEMP_FOLDER, section)
                        cv2.imwrite(final_filename, crop_img)
                        #detect_text(final_filename)

                        if section_type == 'text':
                            section_value = predict_helper.predict(crop_img, section_type)
                            detected_text = detect_text(final_filename)
                            if detected_text == 'failed':
                                detected_text = section_value
                            detected_text = detected_text.upper()
                            print("Data : {}".format(detected_text))
                            section_values.append(detected_text)
                        if section_type == 'Number':
                            section_value = predict_helper.predict(crop_img, section_type)
                            detected_text = detect_text(final_filename)
                            if detected_text == 'failed':
                                detected_text = section_value
                            section_values.append(detected_text)
                        elif section_type == 'image':
                            filename
                            section_filename = '%s/section_scanned_%s.jpg' % (FORM_IMAGES_FOLDER, section)
                            cv2.imwrite(section_filename, crop_img)
                            link = '/form_images/section_scanned_%s.jpg' % section
                            section_values.append(link)

                    date = str(datetime.date.today())
                    timestamp = str(datetime.datetime.now().strftime('%H:%M:%S'))
                    stamp = '%s-%s' % (date, timestamp)
                    sub_name = '%s_%s' % (timestamp, f_code)
                    submissions_batch.insert({'fields': f_sections, 'values': section_values, 'form_code' : f_code, 'name': sub_name, 'time' : stamp, 'file_name' : jpg_file})
                return redirect('/submission')

        return render_template('submission_platform_batch.html', form_code=form_code, formlist=formlist, user_type=user_type)
    else:
        return redirect('/userlogin')

def detect_text(path):

    client = vision.ImageAnnotatorClient()

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)

    response = client.text_detection(image=image)
    texts = response.text_annotations
    #print(texts)
    #print(texts[0].description)
    try :
        string = str(texts[0].description).rstrip()
        return string
    except Exception:
        print("Extraction")
        string = 'failed'
        return string

"""
def main(photo_file):

    access_token = os.environ.get('VISION_API')
    service = Service('vision', 'v1', access_token=access_token)

    with open(photo_file, 'rb') as image:
        base64_image = encode_image(image)
        body = {
            'requests': [{
                'image': {
                    'content': base64_image,
                },
                'features': [{
                    'type': 'TEXT_DETECTION',
                    'maxResults': 1,
                }]

            }]
        }
        response = service.execute(body=body)
        text = response['responses'][0]['textAnnotations'][0]['description']
        print('Found text: {}'.format(text))
    return text
"""


@app.route('/view_forms', methods=['POST', 'GET'])
def view_form():
    if 'username' in session:

        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']

        forms = mongo.db.forms
        count = forms.count()
        formlist = range(0, count, 1)

        form_codes = []
        form_descriptions = []

        find_form_code = forms.find({}, {'code': True, 'description': True, '_id': False})
        new_count = find_form_code.count()
        if new_count > 0:
            for title in find_form_code:
                code = title['code']
                description = title['description']
                form_codes.append(code)
                form_descriptions.append(description)

        return render_template('forms.html', formlist=formlist, form_codes=form_codes,
                               form_descriptions=form_descriptions, user_type=user_type)
    else:
        return redirect('/userlogin')


@app.route('/form_components/<form_code>', methods=['POST', 'GET'])
def form_components(form_code):
    if 'username' in session:
        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        forms = mongo.db.forms
        sections = mongo.db.sections
        form = forms.find_one({'code': str(form_code)})
        form_width = form['width']
        form_height = form['height']
        static_img_url = form['static_url']
        action_url = '/add_section/%s' % form_code

        sections_form = sections.find({'form': form_code})
        count = sections_form.count()
        sectionlist = range(0, count, 1)

        sections_arr = []

        if count > 0:
            find_section_name = sections.find({'form': form_code}, {'section_name': True, '_id': False})
            for title in find_section_name:
                code = title['section_name']
                sections_arr.append(code)

        return render_template('edit_sections.html', static_img_url=static_img_url, sectionlist=sectionlist,
                               sections_arr=sections_arr, form_code=form_code, action_url=action_url, form_height=form_height, form_width=form_width, user_type=user_type)
    else:
        return redirect('/userlogin')


@app.route('/records', methods=['GET', 'POST'])
def records():
    if 'username' in session:
        users = mongo.db.users
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        submissions = mongo.db.submissions
        subs = submissions.find()
        sub_count = subs.count()

        sub_names = []
        sub_times = []
        sub_codes = []
        sub_links = []
        submissionlist = range(0, sub_count, 1)
        if sub_count > 0:
            find_submission = submissions.find({}, {'name': True, 'form_code': True, 'time': True, '_id': False})
            for title in find_submission:
                code = title['form_code']
                name = title['name']
                time = title['time']
                view_link = '/view_record/%s' % name
                sub_names.append(name)
                sub_times.append(time)
                sub_codes.append(code)
                sub_links.append(view_link)

        return render_template('view_records.html', submissionlist=submissionlist, sub_names=sub_names, sub_codes=sub_codes, sub_times=sub_times, sub_links=sub_links, user_type=user_type)
    else:
        return redirect('/userlogin')


@app.route('/view_record/<name>', methods=['GET', 'POST'])
def record_details(name):
    if 'username' in session:
        users = mongo.db.users
        sections = mongo.db.sections
        find_user = users.find_one({'name': session['username']})
        user_type = find_user['user_type']
        submissions = mongo.db.submissions
        find_submisson = submissions.find_one({'name': name})
        submission_fields = list(find_submisson['fields'])
        submission_values = list(find_submisson['values'])
        submission_types = []
        record_form = find_submisson['form_code']
        for field in submission_fields:
            find_field = sections.find_one({'form':record_form, 'section_name' : field})
            field_type = find_field['type']
            submission_types.append(field_type)

        fieldlist = range(0, len(submission_fields), 1)
        valuelist = range(0, len(submission_values), 1)

        return render_template('view_record_detail.html', fieldlist=fieldlist, valuelist=valuelist, submission_values=submission_values, submission_fields=submission_fields, user_type=user_type, submission_types=submission_types)
    else:
        return redirect('/userlogin')


@app.route('/add_section/<form_code>', methods=['POST', 'GET'])
def add_section(form_code):
    if 'username' in session:

        sections = mongo.db.sections
        if request.method == 'POST':
            y1 = request.form['y1']
            y2 = request.form['y2']
            x1 = request.form['x1']
            x2 = request.form['x2']
            form_type = request.form['type']
            section_name = request.form['section_name']
            sections.insert({'section_name': str(section_name), 'x1': x1, 'x2': x2, 'y1': y1, 'y2': y2, 'form': form_code,
                             'type': form_type})
            red = '/form_components/%s' % form_code
            return redirect(red)
    else:
        return redirect('/userlogin')


# Login and registration
@app.route('/register', methods=['POST', 'GET'])
def register():
    if 'username' in session:
        return redirect('/')
    if request.method == 'POST':
        users = mongo.db.users
        user_fname = request.form.get('name')
        # user_fname = request.form['name']
        user_email = request.form.get('email')
        existing_user = users.find_one({'name': request.form.get('username')})
        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form.get('password').encode('utf-8'), bcrypt.gensalt())
            users.insert(
                {'fullname': user_fname, 'email': user_email, 'name': request.form.get('username'),
                 'user_type': 'worker', 'password': hashpass})
            session['username'] = request.form.get('username')
            return redirect('/')

        return 'A user with that Email id/username already exists'

    return render_template('signup.html')


@app.route('/userlogin', methods=['POST', 'GET'])
def userlogin():
    if 'username' in session:
        return redirect('/')

    return render_template('signin.html')


@app.route('/login', methods=['POST'])
def login():
    users = mongo.db.users
    login_user = users.find_one({'name': request.form['username']})

    if login_user:
        if bcrypt.hashpw(request.form.get('password').encode('utf-8'), login_user['password']) == login_user[
            'password']:
            session['username'] = request.form['username']
            return redirect('/')

    return 'Invalid username/password combination'


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')


@app.route('/downloads/<filename>')
def downloads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/form_images/<filename>')
def downloads_forms(filename):
    return send_from_directory(app.config['FORM_IMAGES_FOLDER'], filename)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


if __name__ == "__main__":
    app.run(host='0.0.0.0')
