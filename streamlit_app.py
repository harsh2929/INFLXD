import streamlit as st
import requests
import json
import os
from datetime import datetime
import time
import hashlib

# Page config
st.set_page_config(
    page_title="INFLXD Transcription Service",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
    }
    .upload-section {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .status-badge {
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
    }
    .success { background-color: #d4edda; color: #155724; }
    .processing { background-color: #fff3cd; color: #856404; }
    .failed { background-color: #f8d7da; color: #721c24; }
    .history-item {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 4px solid #007bff;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'api_token' not in st.session_state:
    st.session_state.api_token = None
if 'job_history' not in st.session_state:
    st.session_state.job_history = []
if 'global_history' not in st.session_state:
    st.session_state.global_history = {}  # Persists across logins
if 'current_user_hash' not in st.session_state:
    st.session_state.current_user_hash = None
if 'download_job_id' not in st.session_state:
    st.session_state.download_job_id = None
if 'check_job_id' not in st.session_state:
    st.session_state.check_job_id = None

# API Base URL
API_BASE_URL = "https://transcribe-staging.api.inflexion.ai/enterprise"

# Helper functions
def get_user_hash(token):
    """Create a hash of the API token for user identification"""
    return hashlib.md5(token.encode()).hexdigest()[:16]

def get_mime_type(filename):
    """Get MIME type based on file extension"""
    ext = filename.split('.')[-1].lower()
    mime_types = {
        'mp3': 'audio/mpeg',
        'mp4': 'audio/mp4'
    }
    return mime_types.get(ext, 'audio/mpeg')

def make_api_request(method, endpoint, headers=None, data=None, files=None):
    """Make API request with error handling"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=data, files=files)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return response
    except Exception as e:
        st.error(f"API Request Error: {str(e)}")
        return None

def format_status(status):
    """Format status with colored badge"""
    status_colors = {
        "completed": "success",
        "processing": "processing",
        "failed": "failed"
    }
    css_class = status_colors.get(status.lower(), "processing")
    return f'<span class="status-badge {css_class}">{status.upper()}</span>'

def save_job_to_history(job_data):
    """Save job to both session and persistent history"""
    job_entry = {
        "id": job_data["id"],
        "title": job_data["title"],
        "company": job_data["company"],
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": job_data["status"]
    }
    
    # Save to session history
    st.session_state.job_history.insert(0, job_entry)
    st.session_state.job_history = st.session_state.job_history[:20]
    
    # Save to persistent history
    if st.session_state.current_user_hash:
        if st.session_state.current_user_hash not in st.session_state.global_history:
            st.session_state.global_history[st.session_state.current_user_hash] = []
        
        st.session_state.global_history[st.session_state.current_user_hash].insert(0, job_entry)
        # Keep last 100 jobs per user
        st.session_state.global_history[st.session_state.current_user_hash] = \
            st.session_state.global_history[st.session_state.current_user_hash][:100]

def load_user_history():
    """Load history for current user"""
    if st.session_state.current_user_hash and \
       st.session_state.current_user_hash in st.session_state.global_history:
        st.session_state.job_history = \
            st.session_state.global_history[st.session_state.current_user_hash].copy()

# Main App
st.title("🎙️ INFLXD Transcription Service")
st.markdown("**Professional Audio Transcription Platform**")

# Sidebar for API Key
with st.sidebar:
    st.header("🔐 Authentication")
    
    if st.session_state.api_token is None:
        api_key_input = st.text_input(
            "Enter your API Token",
            type="password",
            placeholder="Bearer token..."
        )
        
        if st.button("Authenticate", type="primary", use_container_width=True):
            if api_key_input:
                st.session_state.api_token = api_key_input
                st.session_state.current_user_hash = get_user_hash(api_key_input)
                load_user_history()
                st.success("✓ Authenticated successfully!")
                st.rerun()
            else:
                st.error("Please enter a valid API token")
    else:
        st.success("✓ Authenticated")
        st.caption("Token: " + st.session_state.api_token[:20] + "...")
        
        if st.button("Logout", use_container_width=True):
            st.session_state.api_token = None
            st.session_state.current_user_hash = None
            st.session_state.job_history = []
            st.rerun()
    
    # Recent Jobs History
    if st.session_state.job_history:
        st.divider()
        st.header("📝 Recent Jobs")
        st.caption("Click on a job to see details and copy ID")
        
        for i, job in enumerate(st.session_state.job_history[:5]):
            with st.expander(f"🔸 {job['title'][:25]}..." if len(job['title']) > 25 else f"🔸 {job['title']}", expanded=False):
                st.markdown(f"**Company:** {job['company']}")
                st.markdown(f"**Status:** {job['status']}")
                st.markdown(f"**Submitted:** {job['submitted_at']}")
                st.divider()
                st.markdown("**📋 Job ID** *(click below to select and copy)*")
                st.code(job['id'], language=None)

# Check if authenticated
if st.session_state.api_token is None:
    st.warning("⚠️ Please authenticate with your API token in the sidebar to continue.")
    st.stop()

# Main content area with tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 Upload Audio", "📊 Check Status", "📥 Download Transcript", "📜 📚 API Documentation", "Under development..."])

# Tab 1: Upload Audio
with tab1:
    st.header("Upload Audio for Transcription")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # File upload
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=['mp3', 'mp4'],
            help="Select the audio file you want to transcribe (MP3 or MP4)"
        )
        
        # Basic parameters
        title = st.text_input(
            "Title *",
            placeholder="e.g., Q4 2024 Earnings Call",
            help="Title for the transcription job"
        )
        
        company = st.text_input(
            "Company *",
            placeholder="e.g., Acme Corporation",
            help="Company name associated with this transcription"
        )
        
        entities = st.text_input(
            "Entities/Keywords (optional)",
            placeholder="e.g., John Doe, Jane Smith, revenue, growth",
            help="Comma-separated list of names and keywords to highlight"
        )
    
    with col2:
        # Advanced options
        st.subheader("Advanced Options")
        
        speakers = st.text_area(
            "Speakers (JSON format, optional)",
            placeholder='[{"name": "John Doe", "role": "CEO"}, {"name": "Jane Smith", "role": "CFO"}]',
            height=100,
            help="Define speakers in JSON format"
        )
        
        call_type = st.selectbox(
            "Call Type",
            ["", "earnings call", "round table", "panel call", "product launch event", "other"],
            help="Type of audio stream"
        )
        
        time_period = st.text_input(
            "Time Period",
            placeholder="e.g., Q1 2025, March 2025",
            help="Timeframe of the call"
        )
        
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            clean_audio = st.checkbox("Generate Clean Audio", value=True)
            clean_transcript = st.checkbox("Generate Clean Transcript", value=True)
        
        with col_opt2:
            speaker_diarization = st.checkbox("Speaker Diarization", value=True)
            fact_checking = st.checkbox("Fact Checking", value=False)
    
    # Upload button
    if st.button("🚀 Submit Transcription Job", type="primary", use_container_width=True):
        # Validation
        if not uploaded_file:
            st.error("Please select an audio file")
        elif not title:
            st.error("Please enter a title")
        elif not company:
            st.error("Please enter a company name")
        else:
            with st.spinner("Uploading audio file and creating transcription job..."):
                # Prepare request
                headers = {
                    "Authorization": f"Bearer {st.session_state.api_token}",
                    "Accept": "application/json"
                }
                
                data = {
                    "title": title,
                    "company": company,
                    "entities": entities,
                    "clean_audio": str(clean_audio).lower(),
                    "clean_transcript": str(clean_transcript).lower(),
                    "speaker_diarization": str(speaker_diarization).lower(),
                    "fact_checking": str(fact_checking).lower()
                }
                
                # Add optional fields
                if call_type:
                    data["call_type"] = call_type
                if time_period:
                    data["time_period"] = time_period
                if speakers:
                    try:
                        speakers_json = json.loads(speakers)
                        data["speakers"] = json.dumps(speakers_json)
                    except:
                        st.warning("Invalid speakers JSON format, skipping...")
                
                # Get appropriate MIME type
                mime_type = get_mime_type(uploaded_file.name)
                
                files = {
                    "audio": (uploaded_file.name, uploaded_file.getvalue(), mime_type)
                }
                
                # Make request
                response = make_api_request("POST", "/workflow", headers=headers, data=data, files=files)
                
                if response and response.status_code in (200, 201):
                    job_data = response.json()
                    save_job_to_history(job_data)
                    
                    st.success("✅ Transcription job submitted successfully!")
                    
                    # Display job details
                    with st.expander("Job Details", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.text(f"Job ID: {job_data['id']}")
                            st.text(f"Status: {job_data['status']}")
                            st.text(f"Title: {job_data['title']}")
                        with col2:
                            st.text(f"Company: {job_data['company']}")
                            st.text(f"Upload Type: {job_data.get('upload_type', 'AI')}")
                            if job_data.get('public_url'):
                                st.text("Audio URL: Available")
                    
                    # Copy job ID button
                    st.code(job_data['id'], language=None)
                    st.caption("Job ID copied to clipboard! Use this to check status.")
                
                elif response:
                    st.error(f"Error {response.status_code}: {response.text}")
                else:
                    st.error("Failed to connect to the API")

# Tab 2: Check Status
with tab2:
    st.header("Check Transcription Status")
    
    # Use job ID from history if available
    default_job_id = st.session_state.check_job_id if st.session_state.check_job_id else ""
    
    job_id = st.text_input(
        "Enter Job ID",
        placeholder="e.g., 508926fa-9729-4dd7-9b1e-9aeecb5c9642",
        help="Enter the job ID from your transcription submission",
        value=default_job_id
    )
    
    # Clear the session state job ID after use
    if st.session_state.check_job_id:
        st.session_state.check_job_id = None
    
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("Auto-refresh", value=False)
    
    if st.button("🔍 Check Status", type="primary", use_container_width=True) or auto_refresh:
        if job_id:
            with st.spinner("Checking job status..."):
                headers = {
                    "Authorization": f"Bearer {st.session_state.api_token}"
                }
                
                response = make_api_request("GET", f"/workflow/{job_id}", headers=headers)
                
                if response and response.status_code == 200:
                    status_data = response.json()
                    
                    # Update status in both session and persistent history
                    for job in st.session_state.job_history:
                        if job['id'] == job_id:
                            job['status'] = status_data['status']
                            break
                    
                    # Update persistent history
                    if st.session_state.current_user_hash and \
                       st.session_state.current_user_hash in st.session_state.global_history:
                        for job in st.session_state.global_history[st.session_state.current_user_hash]:
                            if job['id'] == job_id:
                                job['status'] = status_data['status']
                                break
                    
                    # Display status
                    st.markdown(f"### Status: {format_status(status_data['status'])}", unsafe_allow_html=True)
                    
                    # Progress indicator
                    if status_data['status'] == 'processing':
                        st.progress(0.5, text="Transcription in progress...")
                    elif status_data['status'] == 'completed':
                        st.progress(1.0, text="Transcription completed!")
                    
                    # Job details
                    with st.expander("Full Job Details", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.text(f"Job ID: {status_data['id']}")
                            st.text(f"Title: {status_data['title']}")
                            st.text(f"Company: {status_data['company']}")
                            st.text(f"Status: {status_data['status']}")
                        
                        with col2:
                            st.text(f"Upload Type: {status_data.get('upload_type', 'N/A')}")
                            st.text(f"Entities: {status_data.get('entities', 'N/A')}")
                            if status_data.get('public_url'):
                                st.markdown(f"[📎 Audio File]({status_data['public_url']})")
                    
                    # Auto-refresh logic
                    if auto_refresh and status_data['status'] == 'processing':
                        time.sleep(5)
                        st.rerun()
                
                elif response:
                    st.error(f"Error {response.status_code}: {response.text}")
                else:
                    st.error("Failed to connect to the API")
        else:
            st.warning("Please enter a job ID")

# Tab 3: Download Transcript
with tab3:
    st.header("Download Completed Transcript")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Use job ID from history if available
        default_download_id = st.session_state.download_job_id if st.session_state.download_job_id else ""
        
        download_job_id = st.text_input(
            "Enter Job ID",
            placeholder="e.g., 508926fa-9729-4dd7-9b1e-9aeecb5c9642",
            key="download_job_id_field",
            value=default_download_id
        )
        
        # Clear the session state job ID after use
        if st.session_state.download_job_id:
            st.session_state.download_job_id = None
        
        format_type = st.selectbox(
            "Select Output Format",
            ["json", "pdf", "docx", "txt", "html", "srt", "vtt"],
            help="Choose the format for your transcript"
        )
    
    with col2:
        st.subheader("Export Options")
        remove_timestamps = st.checkbox("Remove Timestamps", value=False)
        remove_word_timestamps = st.checkbox("Remove Word-level Timestamps", value=True)
        remove_speaker_labels = st.checkbox("Remove Speaker Labels", value=False)
        remove_insights = st.checkbox("Remove Insights", value=False)
        remove_keywords = st.checkbox("Remove Keywords", value=False)
    
    if st.button("📥 Download Transcript", type="primary", use_container_width=True):
        if download_job_id:
            with st.spinner(f"Downloading transcript in {format_type.upper()} format..."):
                headers = {
                    "Authorization": f"Bearer {st.session_state.api_token}"
                }
                
                # Build query parameters
                params = []
                if remove_timestamps:
                    params.append("remove_timestamps=1")
                if remove_word_timestamps:
                    params.append("remove_word_level_timestamps=1")
                if remove_speaker_labels:
                    params.append("remove_speaker_labels=1")
                if remove_insights:
                    params.append("remove_insights=1")
                if remove_keywords:
                    params.append("remove_keywords=1")
                
                query_string = "?" + "&".join(params) if params else ""
                endpoint = f"/transcript/export/{download_job_id}/{format_type}{query_string}"
                
                response = make_api_request("GET", endpoint, headers=headers)
                
                if response and response.status_code == 200:
                    # Prepare download
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"transcript_{download_job_id[:8]}_{timestamp}.{format_type}"
                    
                    # Handle different content types
                    if format_type == "json":
                        content = response.text
                        mime_type = "application/json"
                        
                        # Display JSON preview
                        with st.expander("Preview JSON Transcript", expanded=True):
                            try:
                                json_data = json.loads(content)
                                st.json(json_data)
                            except:
                                st.text(content[:1000] + "...")
                    
                    elif format_type in ["pdf", "docx"]:
                        content = response.content
                        mime_type = "application/octet-stream"
                    
                    else:  # txt, html, srt, vtt
                        content = response.text
                        mime_type = "text/plain"
                        
                        # Display text preview
                        with st.expander(f"Preview {format_type.upper()} Transcript", expanded=True):
                            st.text(content[:1000] + "...")
                    
                    # Download button
                    st.download_button(
                        label=f"💾 Save {format_type.upper()} File",
                        data=content,
                        file_name=filename,
                        mime=mime_type,
                        use_container_width=True
                    )
                    
                    st.success(f"✅ Transcript ready for download as {filename}")
                
                elif response:
                    if response.status_code == 404:
                        st.error("Transcript not found. Make sure the job is completed.")
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                else:
                    st.error("Failed to connect to the API")
        else:
            st.warning("Please enter a job ID")

# API Documentation
with tab4:
    st.header("API Documentation Summary")
    
    st.markdown("""
    ### 🔗 Base URL
    ```
    https://transcribe-staging.api.inflexion.ai/enterprise
    ```
    
    ### 🎯 Available Endpoints
    
    #### 1. Upload Audio File
    - **Endpoint:** `POST /workflow`
    - **Required:** title, audio file (MP3 or MP4), company
    - **Optional:** entities, speakers, call_type, time_period, various processing options
    
    #### 2. Check Status
    - **Endpoint:** `GET /workflow/{workflow_id}`
    - **Returns:** Job status (processing, completed, failed)
    
    #### 3. Export Transcript
    - **Endpoint:** `GET /transcript/export/{workflow_id}/{format}`
    - **Formats:** json, pdf, docx, txt, html, srt, vtt
    - **Options:** Remove timestamps, speaker labels, insights, etc.
    
    ### 📝 Status Values
    - `processing`: Transcription in progress
    - `completed`: Transcription ready for download
    - `failed`: Transcription failed
    
    ### 💡 Tips
    - Save your Job IDs for tracking and downloading
    - Processing typically takes a few minutes depending on audio length
    - Use JSON format for programmatic access to transcript data
    - PDF and DOCX formats are best for human-readable reports
    """)

# Footer
st.divider()
st.caption("INFLXD Transcription Service v1.0 | Powered by Inflexion AI")
