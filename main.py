import io
import streamlit as st
import os
import base64
import tempfile
import numpy as np

try:
    from PIL import Image
    # Use a version-independent resampling filter
    if hasattr(Image, 'Resampling'):  # Pillow 9.0.0 and above
        RESAMPLING_FILTER = Image.Resampling.LANCZOS
    else:  # Pillow 8.x.x and below
        RESAMPLING_FILTER = Image.LANCZOS
except ImportError:
    st.error("Failed to import PIL. Please check your Pillow installation.")
    Image = None
    RESAMPLING_FILTER = None

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    st.error("Failed to import moviepy. Please check your moviepy installation.")
    VideoFileClip = None

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


def load_html_file(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning(f"File {file_name} not found. Skipping HTML content.")
        return ""
    except Exception as e:
        st.error(f"Error loading {file_name}: {str(e)}")


# Load and display the custom expander HTML
expander_html = load_html_file('expander.html')
if expander_html:
    st.html(expander_html)
else:
    st.write("Custom HTML content could not be loaded.")

uploaded_file = st.file_uploader("העלו קובץ וידאו", type=["mp4", "avi", "mov"])

# Display footer content
st.sidebar.markdown(footer_content, unsafe_allow_html=True)

## Display gif generation parameters once file has been uploaded ##
if uploaded_file is not None and Image is not None and VideoFileClip is not None:
    try:
        ## Save to temp file ##
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') 
        tfile.write(uploaded_file.read())
        tfile.close()
        
        ## Open file ##
        clip = VideoFileClip(tfile.name)
        st.session_state.clip_duration = clip.duration

        ## Input widgets ##
        with st.expander('פרמטרים לשינוי'):
            selected_resolution_scaling = st.slider('קנה מידה של רזולוציית וידאו', 0.0, 1.0, 0.5)
            selected_speedx = st.slider('מהירות ריצה', 0.1, 10.0, 2.0)
            selected_export_range = st.slider('טווח משך לייצוא', 0, int(st.session_state.clip_duration), (0, int(st.session_state.clip_duration)))
            st.session_state.clip_fps = st.slider('FPS', 10, 60, 20)

        ## Resizing of video ##
        # Instead of resizing here, we'll resize when processing frames
        
        st.session_state.clip_width = clip.w
        st.session_state.clip_height = clip.h
        st.session_state.clip_duration = clip.duration
        st.session_state.clip_total_frames = clip.duration * clip.fps

        ## Display output ##
        with st.container(border=1):
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric('רוחב', st.session_state.clip_width, 'pixels')
            col2.metric('גובה', st.session_state.clip_height, 'pixels')
            col3.metric('משך', st.session_state.clip_duration, 'seconds')
            col4.metric('FPS', st.session_state.clip_fps, '')
            col5.metric('סה"כ פריימים', round(st.session_state.clip_total_frames, 2), 'frames')

        # Extract video frame as a display image
        with st.expander('רצף תמונות'):
            selected_frame = st.slider('תצוגה מקדימה של מסגרת זמן(ש)', 0, int(st.session_state.clip_duration), int(np.median(st.session_state.clip_duration)))
            frame = clip.get_frame(selected_frame)
            st.image(frame)

        ## Export animated GIF ##    
        generate_gif = st.button('ליצירת תמונה מונפשת', use_container_width=True)
    
        if generate_gif:
            with st.spinner('מכין את התמונה...'):
                clip = clip.subclip(selected_export_range[0], selected_export_range[1]).speedx(selected_speedx)
            
                frames = []
                for frame in clip.iter_frames():
                    # Resize the frame
                    resized_frame = Image.fromarray(frame).resize(
                        (int(clip.w * selected_resolution_scaling), 
                         int(clip.h * selected_resolution_scaling)),
                        resample=RESAMPLING_FILTER
                    )
                    frames.append(resized_frame)

                # Save the GIF
                frames[0].save('export.gif', 
                               format='GIF', 
                               save_all=True, 
                               append_images=frames[1:], 
                               duration=int(1000/st.session_state.clip_fps), 
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



