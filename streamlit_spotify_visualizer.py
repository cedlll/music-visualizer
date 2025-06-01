import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import json
from datetime import datetime
import base64

# Set page config
st.set_page_config(
    page_title="🎵 Spotify Music Visualizer",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1DB954, #1ed760);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .track-info {
        background: linear-gradient(135deg, #1DB954, #191414);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
    }
    
    .metric-container {
        background: rgba(29, 185, 84, 0.1);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #1DB954;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #1DB954, #1ed760);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div {
        background-color: #191414;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

class SpotifyVisualizer:
    def __init__(self):
        self.sp = None
        self.current_track = None
        self.audio_features = None
        self.audio_analysis = None
        
    def authenticate(self, client_id, client_secret, redirect_uri):
        """Authenticate with Spotify API"""
        try:
            scope = "user-read-playback-state user-read-currently-playing playlist-read-private user-library-read"
            
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=scope,
                cache_path=None,
                show_dialog=True
            )
            
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            return True
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            return False
    
    def get_user_playlists(self):
        """Get user's playlists"""
        if not self.sp:
            return []
        
        try:
            playlists = self.sp.current_user_playlists()
            return [(playlist['name'], playlist['id']) for playlist in playlists['items']]
        except Exception as e:
            st.error(f"Failed to fetch playlists: {str(e)}")
            return []
    
    def get_playlist_tracks(self, playlist_id):
        """Get tracks from a playlist"""
        if not self.sp:
            return []
        
        try:
            results = self.sp.playlist_tracks(playlist_id)
            tracks = []
            for item in results['items']:
                track = item['track']
                if track and track['preview_url']:  # Only include tracks with preview
                    tracks.append({
                        'name': track['name'],
                        'artist': ', '.join([artist['name'] for artist in track['artists']]),
                        'id': track['id'],
                        'preview_url': track['preview_url'],
                        'popularity': track['popularity'],
                        'duration_ms': track['duration_ms']
                    })
            return tracks
        except Exception as e:
            st.error(f"Failed to fetch playlist tracks: {str(e)}")
            return []
    
    def get_track_features(self, track_id):
        """Get audio features for a track"""
        if not self.sp:
            return None
        
        try:
            features = self.sp.audio_features(track_id)[0]
            analysis = self.sp.audio_analysis(track_id)
            return features, analysis
        except Exception as e:
            st.error(f"Failed to fetch track features: {str(e)}")
            return None, None
    
    def get_currently_playing(self):
        """Get currently playing track"""
        if not self.sp:
            return None
        
        try:
            current = self.sp.current_user_playing_track()
            if current and current['is_playing']:
                track = current['item']
                return {
                    'name': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'id': track['id'],
                    'progress_ms': current['progress_ms'],
                    'duration_ms': track['duration_ms']
                }
        except Exception as e:
            st.error(f"Failed to fetch currently playing: {str(e)}")
        return None

def create_audio_visualizations(features, analysis, track_info):
    """Create various audio visualizations"""
    
    # Create subplot layout
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Audio Features Radar', 'Frequency Analysis', 'Beat Timeline', 'Tempo & Energy'),
        specs=[[{"type": "scatterpolar"}, {"type": "bar"}],
               [{"type": "scatter"}, {"type": "indicator"}]]
    )
    
    # 1. Audio Features Radar Chart
    if features:
        audio_attrs = ['danceability', 'energy', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence']
        values = [features.get(attr, 0) for attr in audio_attrs]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=audio_attrs,
            fill='toself',
            fillcolor='rgba(29, 185, 84, 0.3)',
            line=dict(color='#1DB954', width=3),
            name='Audio Features'
        ), row=1, col=1)
    
    # 2. Frequency Analysis (simulated from segments)
    if analysis and 'segments' in analysis:
        segments = analysis['segments'][:50]  # First 50 segments
        frequencies = []
        for segment in segments:
            if 'pitches' in segment:
                frequencies.extend(segment['pitches'])
        
        if frequencies:
            freq_bins = np.histogram(frequencies, bins=12)[0]
            pitch_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            
            fig.add_trace(go.Bar(
                x=pitch_names,
                y=freq_bins,
                marker_color=px.colors.sequential.Viridis,
                name='Pitch Distribution'
            ), row=1, col=2)
    
    # 3. Beat Timeline
    if analysis and 'beats' in analysis:
        beats = analysis['beats'][:100]  # First 100 beats
        beat_times = [beat['start'] for beat in beats]
        beat_confidence = [beat['confidence'] for beat in beats]
        
        fig.add_trace(go.Scatter(
            x=beat_times,
            y=beat_confidence,
            mode='markers+lines',
            marker=dict(
                size=8,
                color=beat_confidence,
                colorscale='Viridis',
                showscale=True
            ),
            line=dict(color='#1DB954', width=2),
            name='Beat Confidence'
        ), row=2, col=1)
    
    # 4. Tempo & Energy Gauge
    if features:
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=features.get('tempo', 0),
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Tempo (BPM)"},
            delta={'reference': 120},
            gauge={
                'axis': {'range': [None, 200]},
                'bar': {'color': "#1DB954"},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 120], 'color': "gray"},
                    {'range': [120, 200], 'color': "darkgray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': features.get('energy', 0) * 200
                }
            }
        ), row=2, col=2)
    
    # Update layout
    fig.update_layout(
        title=f"Audio Visualization: {track_info['name']} by {track_info['artist']}",
        height=800,
        showlegend=True,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_waveform_visualization(analysis):
    """Create a waveform-like visualization from audio analysis"""
    if not analysis or 'segments' not in analysis:
        return None
    
    segments = analysis['segments']
    
    # Extract segment data
    times = [seg['start'] for seg in segments]
    loudness = [seg['loudness_max'] for seg in segments]
    
    # Normalize loudness to positive values
    min_loudness = min(loudness)
    normalized_loudness = [(l - min_loudness) for l in loudness]
    
    fig = go.Figure()
    
    # Create waveform
    fig.add_trace(go.Scatter(
        x=times,
        y=normalized_loudness,
        mode='lines',
        fill='tonexty',
        fillcolor='rgba(29, 185, 84, 0.3)',
        line=dict(color='#1DB954', width=2),
        name='Audio Waveform'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    fig.update_layout(
        title="Audio Waveform Visualization",
        xaxis_title="Time (seconds)",
        yaxis_title="Amplitude",
        template="plotly_dark",
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def create_3d_visualization(features, analysis):
    """Create 3D visualization of audio features"""
    if not analysis or 'segments' not in analysis:
        return None
    
    segments = analysis['segments'][:100]  # Limit for performance
    
    x = [seg['start'] for seg in segments]
    y = [seg['loudness_max'] for seg in segments]
    z = [sum(seg.get('pitches', [0])) for seg in segments]
    
    colors = [seg.get('confidence', 0) for seg in segments]
    
    fig = go.Figure(data=[go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode='markers',
        marker=dict(
            size=5,
            color=colors,
            colorscale='Viridis',
            opacity=0.8,
            colorbar=dict(title="Confidence")
        )
    )])
    
    fig.update_layout(
        title="3D Audio Feature Space",
        scene=dict(
            xaxis_title="Time (s)",
            yaxis_title="Loudness",
            zaxis_title="Pitch Sum",
            bgcolor='rgba(0,0,0,0)'
        ),
        template="plotly_dark",
        height=600,
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

def main():
    # Initialize session state
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = SpotifyVisualizer()
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # Header
    st.markdown('<h1 class="main-header">🎵 Spotify Music Visualizer</h1>', unsafe_allow_html=True)
    
    # Sidebar for authentication and controls
    with st.sidebar:
        st.header("🔐 Spotify Authentication")
        
        if not st.session_state.authenticated:
            st.info("Connect your Spotify account to start visualizing!")
            
            client_id = st.text_input("Spotify Client ID", type="password", 
                                    help="Get this from your Spotify Developer Dashboard")
            client_secret = st.text_input("Spotify Client Secret", type="password",
                                        help="Keep this secret and secure")
            redirect_uri = st.text_input("Redirect URI", value="http://localhost:8888/callback",
                                       help="Must match your Spotify app settings")
            
            if st.button("🎵 Connect to Spotify"):
                if client_id and client_secret and redirect_uri:
                    if st.session_state.visualizer.authenticate(client_id, client_secret, redirect_uri):
                        st.session_state.authenticated = True
                        st.success("Successfully connected to Spotify!")
                        st.rerun()
                else:
                    st.error("Please fill in all authentication fields")
        
        else:
            st.success("✅ Connected to Spotify")
            
            if st.button("🔓 Disconnect"):
                st.session_state.authenticated = False
                st.session_state.visualizer = SpotifyVisualizer()
                st.rerun()
            
            st.markdown("---")
            
            # Playlist selection
            st.header("🎵 Select Music")
            
            playlists = st.session_state.visualizer.get_user_playlists()
            if playlists:
                playlist_names = [name for name, _ in playlists]
                selected_playlist = st.selectbox("Choose Playlist", playlist_names)
                
                if selected_playlist:
                    playlist_id = next(pid for name, pid in playlists if name == selected_playlist)
                    tracks = st.session_state.visualizer.get_playlist_tracks(playlist_id)
                    
                    if tracks:
                        track_names = [f"{track['name']} - {track['artist']}" for track in tracks]
                        selected_track_name = st.selectbox("Choose Track", track_names)
                        
                        if selected_track_name:
                            selected_track = next(track for track in tracks 
                                                if f"{track['name']} - {track['artist']}" == selected_track_name)
                            
                            if st.button("🎯 Analyze Track"):
                                with st.spinner("Analyzing track..."):
                                    features, analysis = st.session_state.visualizer.get_track_features(selected_track['id'])
                                    if features:
                                        st.session_state.current_track = selected_track
                                        st.session_state.current_features = features
                                        st.session_state.current_analysis = analysis
                                        st.success("Track analyzed successfully!")
            
            st.markdown("---")
            
            # Currently playing
            st.header("🎵 Now Playing")
            if st.button("🔄 Get Currently Playing"):
                current = st.session_state.visualizer.get_currently_playing()
                if current:
                    st.session_state.current_playing = current
                    with st.spinner("Analyzing currently playing track..."):
                        features, analysis = st.session_state.visualizer.get_track_features(current['id'])
                        if features:
                            st.session_state.current_track = current
                            st.session_state.current_features = features
                            st.session_state.current_analysis = analysis
                else:
                    st.info("No track currently playing")
    
    # Main content area
    if st.session_state.authenticated:
        if hasattr(st.session_state, 'current_track') and st.session_state.current_track:
            track = st.session_state.current_track
            features = st.session_state.current_features
            analysis = st.session_state.current_analysis
            
            # Track info display
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"""
                <div class="track-info">
                    <h2>🎵 {track['name']}</h2>
                    <h3>👨‍🎤 {track['artist']}</h3>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if features:
                    st.metric("Energy", f"{features['energy']:.2f}", 
                            delta=f"{features['energy'] - 0.5:.2f}")
                    st.metric("Danceability", f"{features['danceability']:.2f}",
                            delta=f"{features['danceability'] - 0.5:.2f}")
            
            with col3:
                if features:
                    st.metric("Valence", f"{features['valence']:.2f}",
                            delta=f"{features['valence'] - 0.5:.2f}")
                    st.metric("Tempo", f"{features['tempo']:.0f} BPM")
            
            # Audio preview
            if 'preview_url' in track and track['preview_url']:
                st.audio(track['preview_url'], format='audio/mp3')
            
            # Visualization tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📊 Multi-View", "🌊 Waveform", "🌐 3D Analysis", "📈 Detailed Features"])
            
            with tab1:
                if features and analysis:
                    fig = create_audio_visualizations(features, analysis, track)
                    st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                if analysis:
                    waveform_fig = create_waveform_visualization(analysis)
                    if waveform_fig:
                        st.plotly_chart(waveform_fig, use_container_width=True)
                    else:
                        st.info("Waveform data not available for this track")
            
            with tab3:
                if analysis:
                    fig_3d = create_3d_visualization(features, analysis)
                    if fig_3d:
                        st.plotly_chart(fig_3d, use_container_width=True)
                    else:
                        st.info("3D visualization data not available")
            
            with tab4:
                if features:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Audio Features")
                        feature_data = {
                            'Feature': ['Danceability', 'Energy', 'Speechiness', 'Acousticness', 
                                      'Instrumentalness', 'Liveness', 'Valence'],
                            'Value': [features['danceability'], features['energy'], features['speechiness'],
                                    features['acousticness'], features['instrumentalness'], 
                                    features['liveness'], features['valence']]
                        }
                        df = pd.DataFrame(feature_data)
                        
                        fig_bar = px.bar(df, x='Feature', y='Value', 
                                       color='Value', color_continuous_scale='viridis',
                                       title="Audio Feature Values")
                        fig_bar.update_layout(template="plotly_dark", 
                                            paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_bar, use_container_width=True)
                    
                    with col2:
                        st.subheader("Technical Details")
                        st.write(f"**Key:** {features['key']}")
                        st.write(f"**Mode:** {'Major' if features['mode'] == 1 else 'Minor'}")
                        st.write(f"**Time Signature:** {features['time_signature']}/4")
                        st.write(f"**Tempo:** {features['tempo']:.1f} BPM")
                        st.write(f"**Duration:** {features['duration_ms'] / 1000:.1f} seconds")
                        st.write(f"**Loudness:** {features['loudness']:.1f} dB")
                        
                        if analysis:
                            st.subheader("Analysis Summary")
                            st.write(f"**Sections:** {len(analysis.get('sections', []))}")
                            st.write(f"**Segments:** {len(analysis.get('segments', []))}")
                            st.write(f"**Beats:** {len(analysis.get('beats', []))}")
        
        else:
            st.info("👆 Please select a track from the sidebar to start visualizing!")
            
            # Show example visualizations
            st.markdown("## 🎵 What you can visualize:")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("""
                **📊 Audio Features**
                - Danceability
                - Energy levels  
                - Valence (mood)
                - Acousticness
                """)
            
            with col2:
                st.markdown("""
                **🌊 Waveform Analysis**
                - Amplitude over time
                - Beat detection
                - Segment analysis
                - Tempo visualization
                """)
            
            with col3:
                st.markdown("""
                **🌐 3D Visualizations** 
                - Multi-dimensional audio space
                - Pitch and timbre analysis
                - Confidence mapping
                - Interactive exploration
                """)
    
    else:
        st.info("🔐 Please authenticate with Spotify in the sidebar to begin!")
        
        # Setup instructions
        st.markdown("""
        ## 🚀 Getting Started
        
        1. **Create a Spotify App:**
           - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
           - Create a new app
           - Note your Client ID and Client Secret
           
        2. **Configure Redirect URI:**
           - In your Spotify app settings, add: `http://localhost:8888/callback`
           - For Streamlit Cloud deployment, use your app's URL + `/callback`
           
        3. **Enter Credentials:**
           - Paste your Client ID and Client Secret in the sidebar
           - Click "Connect to Spotify"
           
        4. **Start Visualizing:**
           - Select a playlist and track
           - Explore different visualization modes
           - Analyze your music's audio features!
        """)

if __name__ == "__main__":
    main()
