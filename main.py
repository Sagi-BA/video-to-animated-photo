import io
import streamlit as st
import os
import base64
import tempfile
from PIL import Image
import numpy as np
from moviepy.editor import VideoFileClip
from utils.counter import initialize_user_count, increment_user_count, get_user_count
from utils.TelegramSender import send_telegram_gif_sync
from utils.init import initialize

st.set_page_config(layout="wide", initial_sidebar_state="collapsed", page_title="הפיכת סרטון לתמונה מונפשת", page_icon="🎥")

title, image_path, footer_content = initialize()

## Session state ##
if 'clip_width' not in st.session_state:
    st.session_state.clip_width = 0
if 'clip_height' not in st.session_state:
    st.session_state.clip_height = 0
if 'clip_duration' not in st.session_state:
    st.session_state.clip_duration = 0
if 'clip_fps' not in st.session_state:
    st.session_state.clip_fps = 0
if 'clip_total_frames' not in st.session_state:
    st.session_state.clip_total_frames = 0  
if 'telegram_message_sent' not in st.session_state:
    st.session_state.telegram_message_sent = False  
if 'counted' not in st.session_state:
    st.session_state.counted = True 
    increment_user_count()

initialize_user_count()

st.title(title)

@st.cache_data
def load_html_file(file_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        return f.read()

# Load and display the custom expander HTML
expander_html = load_html_file('expander.html')
st.html(expander_html)

uploaded_file = st.file_uploader("העלו קובץ וידאו", type=["mp4", "avi", "mov"])

# Display footer content
st.sidebar.markdown(footer_content, unsafe_allow_html=True)

## Display gif generation parameters once file has been uploaded ##
if uploaded_file is not None:
    try:
        ## Save to temp file ##
        tfile = tempfile.NamedTemporaryFile(delete=False) 
        tfile.write(uploaded_file.read())
        
        ## Open file ##
        clip = VideoFileClip(tfile.name)
        st.session_state.clip_duration = clip.duration

        ## Input widgets ##
        with st.expander('פרמטרים לשינוי'):
            selected_resolution_scaling = st.slider('Scaling of video resolution', 0.0, 1.0, 0.5 )
            selected_speedx = st.slider('Playback speed', 0.1, 10.0, 5.0)
            selected_export_range = st.slider('Duration range to export', 0, int(st.session_state.clip_duration), (0, int(st.session_state.clip_duration) ))
            st.session_state.clip_fps = st.slider('FPS', 10, 60, 20)

        ## Resizing of video ##
        clip = clip.resize(selected_resolution_scaling)
            
        st.session_state.clip_width = clip.w
        st.session_state.clip_height = clip.h
        st.session_state.clip_duration = clip.duration
        st.session_state.clip_total_frames = clip.duration * clip.fps
        # st.session_state.clip_fps = st.sidebar.slider('FPS', 10, 60, 20)

        ## Display output ##
        #   st.subheader('Metrics')
        with st.container(border=1):
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric('רוחב', st.session_state.clip_width, 'pixels')
            col2.metric('גובה', st.session_state.clip_height, 'pixels')
            col3.metric('משך', st.session_state.clip_duration, 'seconds')
            col4.metric('FPS', st.session_state.clip_fps, '')
            col5.metric('סה"כ פריימים', round(st.session_state.clip_total_frames, 2), 'frames')

        # Extract video frame as a display image
        # st.subheader('רצף תמונות')

        with st.expander('רצף תמונות'):
            selected_frame = st.slider('תצוגה מקדימה של מסגרת זמן(ש)', 0, int(st.session_state.clip_duration), int(np.median(st.session_state.clip_duration)) )
            clip.save_frame('frame.gif', t=selected_frame)
            frame_image = Image.open('frame.gif')
            st.image(frame_image)

        ## Print image parameters ##
        # st.subheader('פרמטרים של התמונה')
        # with st.expander('הצגת הפרמטרים של תמונה'):
        #     st.write(f'File name: `{uploaded_file.name}`')
        #     st.write('Image size:', frame_image.size)
        #     st.write('Video resolution scaling', selected_resolution_scaling)
        #     st.write('Speed playback:', selected_speedx)
        #     st.write('Export duration:', selected_export_range)
        #     st.write('Frames per second (FPS):', st.session_state.clip_fps)
        
        ## Export animated GIF ##    
        generate_gif = st.button('ליצירת תמונה מונפשת',use_container_width=True)
    
        if generate_gif:
            with st.spinner('מכין את התמונה...'):
                clip = clip.subclip(selected_export_range[0], selected_export_range[1]).speedx(selected_speedx)
            
                frames = []
                for frame in clip.iter_frames():
                    frames.append(np.array(frame))
                
                image_list = []

                for frame in frames:
                    # Convert numpy array to PIL Image
                    im = Image.fromarray(frame)
                    # Resize the image using LANCZOS resampling (replacement for ANTIALIAS)
                    im = im.resize((int(im.width * selected_resolution_scaling), 
                                    int(im.height * selected_resolution_scaling)), 
                                   Image.LANCZOS)
                    image_list.append(im)

                # Save the GIF
                image_list[0].save('export.gif', 
                                   format='GIF', 
                                   save_all=True, 
                                   append_images=image_list[1:], 
                                   duration=1000/st.session_state.clip_fps, 
                                   loop=0)
                
                ## Download ##
                
                #video_file = open('export.gif', 'rb')
                #video_bytes = video_file.read()
                #st.video(video_bytes)
                
                file_ = open('export.gif', 'rb')
                contents = file_.read()
                data_url = base64.b64encode(contents).decode("utf-8")
                file_.close()
                fsize = round(os.path.getsize('export.gif')/(1024*1024), 1)
                fname = uploaded_file.name.split('.')[0]
                file_name=f'{fname}_scaling-{selected_resolution_scaling}_fps-{st.session_state.clip_fps}_speed-{selected_speedx}_duration-{selected_export_range[0]}-{selected_export_range[1]}.gif'
                
                # Send animated GIF to Telegram
                send_telegram_gif_sync(data_url, "הפיכת סרטון לתמונה מונפשת")
                st.session_state.telegram_message_sent = True

                with st.container(border=1):
                    st.html(
                        f'<img src="data:image/gif;base64,{data_url}" alt="cat gif">'
                    )
                    
                    st.info(f'גודל הקובץ: {fsize} MB', icon='💾')

                    st.write(f"""
                        <a href="data:image/png;base64,{data_url}" download="{file_name}" class="centered-link">
                            הורדת תמונה
                        </a>
                    """, unsafe_allow_html=True)
                
                st.snow()
                st.success("🎉 ההמרה הושלמה! איך זה נראה?")
                st.toast('ההמרה הושלמה! איך זה נראה', icon='🎉')
                
    except Exception as e:
        st.error(f"Error processing video: {str(e)}")
        st.warning("Please try uploading a different video file.")                
## Default page ##
else:
    st.warning('☝️ תעלו קובץ')

# Display user count after the chatbot
user_count = get_user_count(formatted=True)
st.markdown(f"<div class='user-count' style='color: #4B0082;'>סה\"כ משתמשים: {user_count}</div>", unsafe_allow_html=True)



