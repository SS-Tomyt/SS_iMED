import streamlit as st
from firebase_admin import credentials, firestore, initialize_app
import datetime,time
import pytz
from PIL import Image
import numpy as np
import tensorflow.compat.v1 as tf


utc=pytz.UTC
timezone = pytz.timezone('Asia/Bangkok')


# Use the credentials for your Firebase project to initialize the Firebase app
@st.cache
def bind_socket():
    cred = credentials.Certificate('samsen-smart-pill-24a16-2bcc0c51c43d.json')
    initialize_app(cred)

bind_socket()

# Connect to your Firestore database
db = firestore.client()
p_username=""
if 'username' not in st.session_state: st.session_state.username=p_username
if 'username_' not in st.session_state: st.session_state.username_=st.session_state.username
if 'logedIn' not in st.session_state: st.session_state.logedIn=False
if 'stage' not in st.session_state: st.session_state.stage="Login"
if 'progess' not in st.session_state: st.session_state.progess=[]
if 'full' not in st.session_state: st.session_state.full=False
if 'numpill' not in st.session_state: st.session_state.numpill=0
if st.session_state.username_!="":st.session_state.username=st.session_state.username_
username=st.session_state.username
st.write(st.session_state)
def main_function(psc_info_ref):
    #get data and change to python dic
    psc_info = psc_info_ref.get()
    psc_info_data = psc_info.to_dict()
    
    #get the last day that  have to have a drug
    asingn_date=[psc_info_data['asingned_start'],psc_info_data['assigned_until']]

    #check the last day that  have to eat 
    have_to_eat=asingn_date[1] > datetime.datetime.now().replace(tzinfo=utc)
    st.title(f"สวัสดีคุณ{username}")
    if  have_to_eat:

        complete=psc_info_data['complete']
        total_day=asingn_date[1]-asingn_date[0]
        total=total_day.days*len(psc_info_data['meal'])
        st.session_state.progess=[complete,total]

        with st.expander("**คุณมียาที่ต้องกิน**", expanded=True):
            st.write(f"#### ส่งข้อมูลการกินยา")
            st.write(f"ช่วงวันที่: {asingn_date[0].date()} - {asingn_date[1].date()}")
            st.progress(round(complete/total*100))
            if st.button("ส่งข้อมูลการกินยา"):
                st.session_state.stage="add_data"
                st.experimental_rerun()      
    else:
        with st.expander("**คุณไม่มียาที่ต้องกิน**", expanded=True):
            if st.button("เพิ่มกำหนดการกินยา"):
                st.session_state.stage="add_psc"
                st.experimental_rerun()  
            

def run_inference_for_single_image(image, graph):
  with graph.as_default():
    with tf.Session() as sess:
      # Get handles to input and output tensors
      ops = tf.get_default_graph().get_operations()
      all_tensor_names = {output.name for op in ops for output in op.outputs}
      tensor_dict = {}
      for key in [
          'num_detections', 'detection_boxes', 'detection_scores',
          'detection_classes', 'detection_masks'
      ]:
        tensor_name = key + ':0'
        if tensor_name in all_tensor_names:
          tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
              tensor_name)
      if 'detection_masks' in tensor_dict:
        # The following processing is only for single image
        detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
        detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
        # Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
        real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
        detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
        detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
        detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
            detection_masks, detection_boxes, image.shape[0], image.shape[1])
        detection_masks_reframed = tf.cast(
            tf.greater(detection_masks_reframed, 0.5), tf.uint8)
        # Follow the convention by adding back the batch dimension
        tensor_dict['detection_masks'] = tf.expand_dims(
            detection_masks_reframed, 0)
      image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

      # Run inference
      output_dict = sess.run(tensor_dict,
                             feed_dict={image_tensor: np.expand_dims(image, 0)})

      # all outputs are float32 numpy arrays, so convert types as appropriate
      output_dict['num_detections'] = int(output_dict['num_detections'][0])
      output_dict['detection_classes'] = output_dict[
          'detection_classes'][0].astype(np.uint8)
      output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
      output_dict['detection_scores'] = output_dict['detection_scores'][0]
      if 'detection_masks' in output_dict:
        output_dict['detection_masks'] = output_dict['detection_masks'][0]
  return output_dict


# Create the login form
def login():
    with st.form("login"):
        st.title("Samsen Smart pill", anchor=None)
        st.subheader("กรุณาเข้าสู่ระบบ", anchor=None)
        p_username = st.text_input('ชื่อผู้ใช้:',key="username")
        password = st.text_input('รหัสผ่าน:', type='password')
        submitted = st.form_submit_button("ส่ง")
    st.session_state.username_=st.session_state.username
    # Check if the user has clicked the submit button and entered a username and password
    if submitted and p_username and password:
        # Check if the username and password are correct
        user_ref = db.collection('user').document(p_username)
        user = user_ref.get()
        if user.exists:
            user_data = user.to_dict()
            if user_data['password'] == password:
                # If the username and password are correct, show a success message
                st.success('เข้าสู่ระบบสำเร็จ!')
                st.session_state.logedIn=True
                st.session_state.stage="main"
                st.experimental_rerun()
            else:
                # If the password is incorrect, show an error message
                st.error('รหัสผ่านหรือชื่อผู้ใช้ผิดพลาด')
        else:
            # If the username does not exist, show an error message
            st.error('รหัสผ่านหรือชื่อผู้ใช้ผิดพลาด')

def add_prescription(psc_info_ref):
    with st.form("addPres"):
        st.title("Samsen Smart pill", anchor=None)
        st.subheader("กรุณากรอกข้อมูลยา", anchor=None)
        # medic_name = st.text_input('ชื่อยา(ปริมาณ):')
        units_per_dose = st.number_input('จำนวนเม็ดต่อครั้ง:')
        times_per_day = st.multiselect('เวลาที่กิน',['เช้า', 'กลางวัน', 'เย็น', 'ก่อนนอน'])
        meal = st.selectbox('กินก่อนหรือหลังอาหาร?',('ก่อนอาหาร', 'หลังอาหาร'))
        asingn_start = st.date_input("เริ่มกิน",datetime.datetime.now())
        asingn_untill = st.date_input("กินจนถึง",datetime.datetime.now()+datetime.timedelta(days=1))
        submitted = st.form_submit_button("ยืนยัน")
    asingn_untill = asingn_untill + datetime.timedelta(days=1)
    asingn_start = datetime.datetime(asingn_start.year, asingn_start.month, asingn_start.day)
    asingn_untill = datetime.datetime(asingn_untill.year, asingn_untill.month, asingn_untill.day)

    if submitted:
        psc_info_ref.set({
            'unitPer1': units_per_dose,
            'mealPreDay': times_per_day,
            'meal': meal,
            'asingned_start': asingn_start,
            'assigned_until': asingn_untill,
            'complete':0
        })
        st.session_state.stage="main"
        st.experimental_rerun()
#           'medic_name': medic_name,

def add_data(user_ref):
    #get data from firestore
    psc_info_ref = user_ref.collection("prescription").document('information')
    psc_info = psc_info_ref.get()
    psc_info_data = psc_info.to_dict()
    #get current hour
    current_time = datetime.datetime.now()
    hour = current_time.hour
    #set defult number of pill
    numOfPill=0
    #check time to set defult meal
    if hour>4 and hour<12:mealIndex=0
    elif hour>=12 and hour<17:mealIndex=1
    elif hour>=17 and hour<21:mealIndex=2
    else:mealIndex=3
    #from
    with st.form("addPres"):
        meal = st.selectbox(
        'เวลาที่กิน',
        ['เช้า', 'กลางวัน', 'เย็น', 'ก่อนนอน'],index=mealIndex)
        timeMeal = st.selectbox('กินก่อนหรือหลังอาหาร?',('ก่อนอาหาร', 'หลังอาหาร'))


        img_file_buffer = st.camera_input("ถ่ายรูปยาที่จะกิน")
        if img_file_buffer is not None:
            image = Image.open(img_file_buffer)
            (im_width, im_height) = image.size
            image_np = np.array(image.getdata()).reshape((im_height, im_width, 3)).astype(np.uint8)
            output_dict = run_inference_for_single_image(image_np, detection_graph)
            numOfPill=output_dict['num_detections']
            st.write(numOfPill)
        submitted = st.form_submit_button("ยืนยัน") 
    st.session_state.numpill=numOfPill

    #Check it is complete
    if numOfPill== psc_info_data["unitPer1"] and meal in psc_info_data["mealPreDay"]:
        full=True
        psc_info_ref.update({'complete':psc_info_data["complete"]+1})
    else:full=False
    st.session_state.full=full

    date=datetime.datetime.now().date()
    date_str = date.strftime('%d-%m-%Y')
    if submitted and numOfPill:
        user_ref.collection(date_str).document(meal).set({
            'timestamp': datetime.datetime.now(),
            'numOfPill': numOfPill,
            'timePreDay': timeMeal,
            'meal': meal,
            'full':full
        })
        st.session_state.stage="done"
        st.experimental_rerun()

def done(psc_info_ref):
    psc_info = psc_info_ref.get()
    psc_info_data = psc_info.to_dict()
    unitPer1=psc_info_data["unitPer1"]
    st.title("ส่งสำเร็จ")
    if st.session_state.full:
        st.write("มื้อนี้กินยาครบตามจำนวน")
        complete=st.session_state.progess[0]
        total=st.session_state.progess[1]
        p1=round(complete/total*100)
        p2=round((complete+1)/total*100)
        p_bar = st.progress(p1)

        for percent_complete in range(p1,p2):
            time.sleep(0.01)
            p_bar.progress(percent_complete + 1)
            
    else:
        st.write("มื้อนี้กินไม่ยาครบ")
        st.write(f"ต้องกิน:{unitPer1} พบ:{st.session_state.numpill}")

    if st.button("กลับหน้าหลัก"):
        st.session_state.stage="main" 
        st.experimental_rerun()
    if st.button("ส่งใหม่"):
        st.session_state.stage="add_data" 
        st.experimental_rerun()

detection_graph = tf.Graph()
with detection_graph.as_default():
  od_graph_def = tf.GraphDef()
  # Open the file in binary mode
  with open("frozen_inference_graph.pb", "rb") as fid:
    # Read the contents of the file
    serialized_graph = fid.read()
    od_graph_def.ParseFromString(serialized_graph)
    tf.import_graph_def(od_graph_def, name='')


if not st.session_state.logedIn:
    login()
else:
    #set the path to data
    user_ref = db.collection('user').document(username)
    psc_ref = user_ref.collection("prescription")
    psc_info_ref = user_ref.collection("prescription").document('information')
    if st.session_state.stage == "main":
        main_function(psc_info_ref)
    elif st.session_state.stage == "add_data":
        add_data(user_ref)
    elif st.session_state.stage == "add_psc":
        add_prescription(psc_info_ref)
    elif st.session_state.stage == "done":
        done(psc_info_ref)
    else: login()