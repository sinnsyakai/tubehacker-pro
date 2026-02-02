import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import re
import time
import json
import os
import tempfile
from typing import Optional, List
import streamlit.components.v1 as components

MAX_VIDEOS = 5

st.set_page_config(
    page_title="TubeHacker Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ダイアログ関数の定義
@st.dialog("🔑 初期設定")
def show_settings_dialog():
    st.markdown("### Gemini APIキーを入力してください")
    st.markdown("[APIキーの取得はこちら](https://aistudio.google.com/app/apikey)")
    
    api_key_input = st.text_input(
        "Gemini API Key", 
        value=st.session_state.get('api_key', ''),
        type="password",
        placeholder="AI..."
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存", type="primary", use_container_width=True):
            if api_key_input:
                st.session_state.api_key = api_key_input
                st.query_params['api_key'] = api_key_input
                st.session_state.show_settings = False
                st.rerun()
            else:
                st.error("APIキーを入力してください")
    with col2:
        if st.button("キャンセル", use_container_width=True):
            st.session_state.show_settings = False
            st.rerun()

# クールなデザインのCSS
st.markdown("""
<style>
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --accent: #f43f5e;
        --bg-dark: #0f172a;
        --bg-card: #1e293b;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
    }
    
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }
    
    .sub-header {
        font-size: 1rem;
        color: var(--text-secondary);
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* タブをより目立つデザインに */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 8px 12px;
        border-radius: 16px;
        border: 2px solid #475569;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 700;
        font-size: 15px;
        color: #94a3b8;
        border: 2px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(99, 102, 241, 0.2);
        color: #c7d2fe;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: 2px solid #a5b4fc !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }
    
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }
    
    .stExpander {
        border: 1px solid #334155;
        border-radius: 12px;
        margin-bottom: 1rem;
        background: var(--bg-card);
    }
    
    [data-testid="collapsedControl"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%) !important;
        border-radius: 8px !important;
    }
    
    .stExpander [data-testid="stMarkdownContainer"] {
        color: #f8fafc !important;
    }
    
    .stExpander [data-testid="stMarkdownContainer"] p,
    .stExpander [data-testid="stMarkdownContainer"] li,
    .stExpander [data-testid="stMarkdownContainer"] h2,
    .stExpander [data-testid="stMarkdownContainer"] h3 {
        color: #f8fafc !important;
    }
    
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #475569;
    }
    
    h1, h2, h3 {
        letter-spacing: -0.3px;
    }
    
    /* 次へボタンのスタイル */
    .scroll-top-btn {
        display: inline-block;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        padding: 12px 24px;
        border-radius: 12px;
        text-decoration: none;
        font-weight: 700;
        margin-top: 16px;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# セッション状態
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = []
if 'common_patterns' not in st.session_state:
    st.session_state.common_patterns = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""
if 'generated_ideas' not in st.session_state:
    st.session_state.generated_ideas = None
if 'generated_script' not in st.session_state:
    st.session_state.generated_script = None
if 'fetched_videos' not in st.session_state:
    st.session_state.fetched_videos = []
if 'script_metadata' not in st.session_state:
    st.session_state.script_metadata = {}
if 'stop_generation' not in st.session_state:
    st.session_state.stop_generation = False
if 'parsed_ideas' not in st.session_state:
    st.session_state.parsed_ideas = {}
if 'char_count_stats' not in st.session_state:
    st.session_state.char_count_stats = {'avg': 0, 'max': 0, 'min': 0}
if 'show_settings' not in st.session_state:
    st.session_state.show_settings = False


def extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_videos_from_channel(channel_url: str, max_videos: int = MAX_VIDEOS) -> List[dict]:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        
        # URLを正規化（/videosを追加）
        base_url = channel_url.rstrip('/')
        if not base_url.endswith('/videos'):
            videos_url = base_url + '/videos'
        else:
            videos_url = base_url
        
        response = requests.get(videos_url, headers=headers, timeout=20)
        
        # ytInitialDataを抽出
        match = re.search(r'var ytInitialData = ({.*?});', response.text)
        if not match:
            match = re.search(r'ytInitialData\s*=\s*({.*?});', response.text)
        if not match:
            # 別のパターンも試す
            match = re.search(r'window\["ytInitialData"\]\s*=\s*({.*?});', response.text)
        if not match:
            return []
        
        data = json.loads(match.group(1))
        videos = []
        
        def find_videos(obj, depth=0):
            if depth > 20 or len(videos) >= max_videos:
                return
            if isinstance(obj, dict):
                # videoRenderer パターン（メイン）
                if 'videoRenderer' in obj:
                    renderer = obj['videoRenderer']
                    video_id = renderer.get('videoId', '')
                    title_obj = renderer.get('title', {})
                    if isinstance(title_obj, dict):
                        runs = title_obj.get('runs', [])
                        title = runs[0].get('text', '') if runs else title_obj.get('simpleText', '')
                    else:
                        title = str(title_obj)
                    if video_id and title and not any(v['video_id'] == video_id for v in videos):
                        videos.append({'video_id': video_id, 'title': title, 'url': f'https://www.youtube.com/watch?v={video_id}'})
                
                # gridVideoRenderer パターン（グリッド表示）
                elif 'gridVideoRenderer' in obj:
                    renderer = obj['gridVideoRenderer']
                    video_id = renderer.get('videoId', '')
                    title_obj = renderer.get('title', {})
                    if isinstance(title_obj, dict):
                        runs = title_obj.get('runs', [])
                        title = runs[0].get('text', '') if runs else title_obj.get('simpleText', '')
                    else:
                        title = str(title_obj)
                    if video_id and title and not any(v['video_id'] == video_id for v in videos):
                        videos.append({'video_id': video_id, 'title': title, 'url': f'https://www.youtube.com/watch?v={video_id}'})
                
                # richItemRenderer パターン（新しいUIスタイル）
                elif 'richItemRenderer' in obj:
                    content = obj['richItemRenderer'].get('content', {})
                    if 'videoRenderer' in content:
                        renderer = content['videoRenderer']
                        video_id = renderer.get('videoId', '')
                        title_obj = renderer.get('title', {})
                        if isinstance(title_obj, dict):
                            runs = title_obj.get('runs', [])
                            title = runs[0].get('text', '') if runs else title_obj.get('simpleText', '')
                        else:
                            title = str(title_obj)
                        if video_id and title and not any(v['video_id'] == video_id for v in videos):
                            videos.append({'video_id': video_id, 'title': title, 'url': f'https://www.youtube.com/watch?v={video_id}'})
                
                # 直接videoIdとtitleがある場合
                elif 'videoId' in obj:
                    video_id = obj['videoId']
                    title_obj = obj.get('title', {})
                    if isinstance(title_obj, dict):
                        runs = title_obj.get('runs', [])
                        title = runs[0].get('text', '') if runs else title_obj.get('simpleText', '')
                    elif isinstance(title_obj, str):
                        title = title_obj
                    else:
                        title = ''
                    if video_id and title and len(video_id) == 11 and not any(v['video_id'] == video_id for v in videos):
                        videos.append({'video_id': video_id, 'title': title, 'url': f'https://www.youtube.com/watch?v={video_id}'})
                
                for value in obj.values():
                    find_videos(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    find_videos(item, depth + 1)
        
        find_videos(data)
        return videos[:max_videos]
    except Exception as e:
        print(f"チャンネル動画取得エラー: {e}")
        return []


def search_youtube_videos(query: str, max_videos: int = MAX_VIDEOS) -> List[dict]:
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'ja-JP,ja;q=0.9'}
        search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        response = requests.get(search_url, headers=headers, timeout=15)
        
        match = re.search(r'var ytInitialData = ({.*?});', response.text)
        if not match:
            match = re.search(r'ytInitialData\s*=\s*({.*?});', response.text)
        if not match:
            return []
        
        data = json.loads(match.group(1))
        videos = []
        
        def find_videos(obj, depth=0):
            if depth > 15 or len(videos) >= max_videos:
                return
            if isinstance(obj, dict):
                if 'videoRenderer' in obj:
                    renderer = obj['videoRenderer']
                    video_id = renderer.get('videoId', '')
                    title_obj = renderer.get('title', {})
                    title = title_obj.get('runs', [{}])[0].get('text', '') if isinstance(title_obj, dict) else ''
                    if video_id and title and not any(v['video_id'] == video_id for v in videos):
                        videos.append({'video_id': video_id, 'title': title, 'url': f'https://www.youtube.com/watch?v={video_id}'})
                for value in obj.values():
                    find_videos(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    find_videos(item, depth + 1)
        
        find_videos(data)
        return videos[:max_videos]
    except Exception:
        return []


def get_video_info(video_id: str, is_shorts: bool = False) -> dict:
    try:
        # ショートの場合は両方のURLを試す
        if is_shorts:
            url = f"https://www.youtube.com/shorts/{video_id}"
        else:
            url = f"https://www.youtube.com/watch?v={video_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        # タイトル取得（複数の方法を試す）
        title = None
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 方法1: og:title
        title_tag = soup.find('meta', property='og:title')
        if title_tag and title_tag.get('content'):
            title = title_tag['content']
        
        # 方法2: title タグ
        if not title:
            title_element = soup.find('title')
            if title_element:
                title = title_element.text.replace(' - YouTube', '').strip()
        
        # 方法3: JSON-LD から
        if not title:
            import json
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('name'):
                        title = data['name']
                        break
                except:
                    pass
        
        # 方法4: ytInitialPlayerResponse から
        if not title:
            import re
            match = re.search(r'"title":"([^"]+)"', response.text)
            if match:
                title = match.group(1).encode().decode('unicode_escape')
        
        if not title:
            title = "タイトル取得失敗"
        
        # サムネイル取得
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        thumb_response = requests.get(thumbnail_url, timeout=10)
        if thumb_response.status_code != 200:
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            thumb_response = requests.get(thumbnail_url, timeout=10)
        
        thumbnail_image = None
        if thumb_response.status_code == 200:
            thumbnail_image = Image.open(BytesIO(thumb_response.content))
        
        return {
            'title': title, 
            'thumbnail_url': thumbnail_url, 
            'thumbnail_image': thumbnail_image, 
            'video_id': video_id, 
            'url': url,
            'is_shorts': is_shorts
        }
    except Exception as e:
        return {
            'title': "取得エラー", 
            'thumbnail_url': None, 
            'thumbnail_image': None, 
            'video_id': video_id, 
            'url': f"https://www.youtube.com/watch?v={video_id}", 
            'error': str(e),
            'is_shorts': is_shorts
        }


def get_transcript(video_id: str) -> Optional[str]:
    try:
        ytt_api = YouTubeTranscriptApi()
        
        # 方法1: 日本語・英語の字幕を直接試す
        for lang in ['ja', 'en', 'ja-JP', 'en-US']:
            try:
                transcript_data = ytt_api.fetch(video_id, languages=[lang])
                full_text = ' '.join([entry.text for entry in transcript_data])
                if full_text.strip():
                    return full_text
            except Exception:
                pass
        
        # 方法2: 利用可能な字幕一覧から取得
        try:
            transcript_list = ytt_api.list(video_id)
            
            # まず手動字幕を優先
            for transcript in transcript_list:
                if not transcript.is_generated:
                    try:
                        transcript_data = transcript.fetch()
                        full_text = ' '.join([entry.text for entry in transcript_data])
                        if full_text.strip():
                            return full_text
                    except Exception:
                        pass
            
            # 次に自動生成字幕を試す
            for transcript in transcript_list:
                if transcript.is_generated:
                    try:
                        transcript_data = transcript.fetch()
                        full_text = ' '.join([entry.text for entry in transcript_data])
                        if full_text.strip():
                            return full_text
                    except Exception:
                        pass
                        
        except Exception:
            pass
        
        return None
    except Exception:
        return None


def transcribe_shorts_audio(model, video_id: str) -> Optional[str]:
    """ショート動画の音声をダウンロードしてGeminiで文字起こし"""
    try:
        import yt_dlp
        
        # 一時ファイルを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, 'audio.mp3')
            
            # yt-dlpで音声をダウンロード
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'outtmpl': audio_path.replace('.mp3', '.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'extract_audio': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
            }
            
            url = f"https://www.youtube.com/shorts/{video_id}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # ダウンロードされたファイルを探す
            audio_file = None
            for f in os.listdir(temp_dir):
                if f.endswith(('.mp3', '.m4a', '.webm', '.ogg')):
                    audio_file = os.path.join(temp_dir, f)
                    break
            
            if not audio_file or not os.path.exists(audio_file):
                return None
            
            # Geminiで音声を文字起こし
            audio_data = genai.upload_file(audio_file)
            
            prompt = """この音声を日本語で文字起こししてください。
話されている内容をそのまま書き起こしてください。
前置きや説明は不要です。音声の内容のみ出力してください。"""
            
            response = model.generate_content([prompt, audio_data])
            
            # 一時ファイルを削除（ディレクトリごと自動削除される）
            genai.delete_file(audio_data)
            
            return response.text.strip()
            
    except Exception as e:
        print(f"音声文字起こしエラー: {e}")
        return None

def analyze_video_with_gemini(model, video_info: dict, transcript: str) -> dict:
    transcript_text = transcript if transcript and len(transcript.strip()) > 50 else None
    char_count = len(transcript) if transcript else 0
    
    # ショート動画かどうかを判定（URLにshortsが含まれるか、字幕が短い）
    is_shorts = 'shorts' in video_info.get('url', '') or (char_count > 0 and char_count < 500)
    
    if is_shorts:
        # ショート動画用プロンプト
        prompt = f"""YouTubeショート動画を分析してください。前置きは不要。直接内容のみ出力。

【タイトル】{video_info['title']}
【字幕テキスト】{transcript_text[:3000] if transcript_text else "なし（字幕なし）"}

以下の形式で出力：

## 文字起こし（{char_count}文字）
{f"字幕テキストをそのまま整形して出力してください。誤字脱字のみ修正し、要約や省略はしない。適切な箇所で改行を入れて読みやすく整形。" if transcript_text else "字幕テキストがないため、文字起こしはできません。"}

## タイトル分析
- キーワード: 
- 文字数: {len(video_info['title'])}文字
- 煽り要素: 
- クリック誘発テクニック: 

## サムネイル/最初のフレーム分析
※添付画像を分析
- インパクト: 
- テキスト: 
- 配置: 
- 色使い: 

## CTA分析
- CTA/誘導の有無: 
- 誘導先: 

## 構成分析（縦型ショート特有）
- 冒頭のつかみ（フック）: 
- 展開速度: 
- 視聴維持の工夫: 
- バズ要素: 
- ターゲット層: 
"""
    else:
        # 通常動画用プロンプト
        prompt = f"""YouTube動画を分析してください。前置きや挨拶は一切不要。直接内容のみ出力。

【タイトル】{video_info['title']}
【字幕テキスト】{transcript_text[:12000] if transcript_text else "なし"}

以下の形式で出力：

## 文字起こし（{char_count}文字）
字幕テキストの誤字脱字のみ修正。要約や省略はしない。内容はそのまま維持。
適切な箇所で見出しをつけて読みやすく整形。

## タイトル分析
- キーワード: SEOとして有効な複合キーワードのみ（単語の羅列ではなく、検索されそうなフレーズ）
- 文字数: {len(video_info['title'])}文字
- 煽り要素: 
- クリック誘発テクニック: 

## サムネイル分析
※添付画像を分析
- 文字の配置: 
- フォント: 
- 色使い: 
- 背景: 
- 人物: 
- 視線誘導: 
- サムネイル内の文字数: 〇文字

## CTA分析
冒頭・途中・終盤すべてのCTAを検出：
- 冒頭CTA: タイミング、訴求内容、セリフ
- 途中CTA: タイミング、訴求内容、セリフ（複数あれば全て）
- 終盤CTA: タイミング、訴求内容、セリフ

## 構成分析
- 冒頭フック: 
- 視聴維持の工夫: 
- 訴求内容: 
- ターゲット層: 
"""
    
    try:
        if video_info.get('thumbnail_image'):
            response = model.generate_content([prompt, video_info['thumbnail_image']])
        else:
            response = model.generate_content(prompt)
        
        return {
            'success': True,
            'analysis': response.text,
            'video_info': video_info,
            'has_transcript': transcript_text is not None,
            'transcript': transcript,
            'char_count': char_count,
            'is_shorts': is_shorts
        }
    except Exception as e:
        return {'success': False, 'error': str(e), 'video_info': video_info, 'has_transcript': False, 'transcript': None, 'char_count': 0, 'is_shorts': is_shorts if 'is_shorts' in dir() else False}


def extract_common_patterns(model, all_results: list) -> tuple:
    char_counts = [r.get('char_count', 0) for r in all_results if r.get('char_count', 0) > 0]
    avg_chars = sum(char_counts) // len(char_counts) if char_counts else 0
    max_chars = max(char_counts) if char_counts else 0
    min_chars = min(char_counts) if char_counts else 0
    
    # タイトル文字数を収集
    title_lengths = [len(r['video_info']['title']) for r in all_results if r.get('success')]
    avg_title_len = sum(title_lengths) // len(title_lengths) if title_lengths else 0
    max_title_len = max(title_lengths) if title_lengths else 0
    min_title_len = min(title_lengths) if title_lengths else 0
    
    combined = ""
    for i, result in enumerate(all_results, 1):
        if result.get('success'):
            title = result['video_info']['title']
            combined += f"\n\n---【動画{i}: {title}（タイトル{len(title)}文字, 文字起こし{result.get('char_count', 0)}文字）】---\n"
            combined += result['analysis']
    
    is_single = len(all_results) == 1
    
    prompt = f"""YouTube動画の分析結果から{'構成パターン' if is_single else '共通の黄金パターン'}を抽出。
前置きや挨拶は一切不要。直接内容のみ出力。

{combined[:20000]}

以下の形式で出力：

## タイトルの{'特徴' if is_single else '黄金パターン'}
- キーワード傾向
- 構成パターン
- 効果的な要素
- タイトル文字数の傾向: 平均{avg_title_len}文字（{min_title_len}〜{max_title_len}文字）

## サムネイルの{'特徴' if is_single else '黄金パターン'}
- 色使い
- 文字の配置
- 視線誘導
- サムネイル文字数の傾向: 〇〜〇文字

## 台本構成の{'詳細分析' if is_single else '黄金パターン'}

### 文字起こしの文字数
- 平均: {avg_chars}文字
- 最大: {max_chars}文字
- 最小: {min_chars}文字
- **台本生成時の目標文字数: {avg_chars}文字前後**

### 全体構成
1. フック
2. CTA①
3. 導入
4. 本題1
5. 本題2
6. CTA②
7. 本題3
8. 注意点
9. まとめ
10. CTA③

### CTA配置パターン
- 冒頭CTA: 
- 途中CTA: 
- 終盤CTA: 

### 各パートのテクニック

## チェックリスト
"""
    
    try:
        response = model.generate_content(prompt)
        char_stats = {'avg': avg_chars, 'max': max_chars, 'min': min_chars}
        return response.text, char_stats
    except Exception as e:
        return f"エラー: {str(e)}", {'avg': 0, 'max': 0, 'min': 0}



def generate_content_ideas(model, common_patterns: str, theme: str, video_titles: list) -> str:
    theme_text = theme if theme else f"分析した動画（{', '.join(video_titles[:3])}）の内容に基づいてAIが最適なテーマを提案"
    
    prompt = f"""YouTubeコンテンツの企画案を生成。前置きや挨拶は一切不要。直接内容のみ出力。

【黄金パターン】
{common_patterns[:12000]}

【テーマ】
{theme_text}

以下の形式で3つの企画案を出力：

## 企画案1
### タイトル案
1. [具体的なタイトル]
2. [具体的なタイトル]
3. [具体的なタイトル]

### サムネイル構成案
- メインテキスト: [具体的な文言]
- サブテキスト: 
- 背景: 
- 配置: 

### 台本構成案

---

## 企画案2
（同様）

---

## 企画案3
（同様）
"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"エラー: {str(e)}"


def parse_ideas(ideas_text: str) -> dict:
    """企画案からタイトルとサムネワードを抽出"""
    parsed = {}
    
    for plan_num in [1, 2, 3]:
        parsed[plan_num] = {'titles': [], 'thumbnail_word': ''}
        
        # タイトル抽出
        pattern = rf'企画案{plan_num}.*?タイトル案.*?1\.\s*(.+?)(?:\n|$).*?2\.\s*(.+?)(?:\n|$).*?3\.\s*(.+?)(?:\n|$)'
        match = re.search(pattern, ideas_text, re.DOTALL)
        if match:
            parsed[plan_num]['titles'] = [match.group(1).strip(), match.group(2).strip(), match.group(3).strip()]
        
        # サムネイルワード抽出
        thumb_pattern = rf'企画案{plan_num}.*?メインテキスト[：:]\s*(.+?)(?:\n|$)'
        thumb_match = re.search(thumb_pattern, ideas_text, re.DOTALL)
        if thumb_match:
            parsed[plan_num]['thumbnail_word'] = thumb_match.group(1).strip().strip('[]「」')
    
    return parsed


def generate_full_script(model, common_patterns: str, theme: str, title: str, thumbnail_word: str, target_chars: int = 0) -> tuple:
    # 文字数の配分を計算（より詳細に）
    if target_chars > 0:
        char_instruction = f"""
★★★ 最重要 ★★★
この台本の総文字数は【必ず{target_chars}文字以上】にしてください。
短い台本は絶対にNGです。各セクションを十分に詳しく書いてください。

目標文字数の内訳:
- フック（冒頭のつかみ）: {target_chars // 8}文字以上
- CTA①: {target_chars // 20}文字以上
- 導入: {target_chars // 8}文字以上
- 本題1: {target_chars // 5}文字以上（具体例3つ以上必須）
- 本題2: {target_chars // 5}文字以上（具体例3つ以上必須）
- CTA②: {target_chars // 20}文字以上
- 本題3: {target_chars // 5}文字以上（具体例3つ以上必須）
- 注意点: {target_chars // 10}文字以上
- まとめ: {target_chars // 10}文字以上
- CTA③・エンディング: {target_chars // 15}文字以上

合計で必ず{target_chars}文字以上になるように、各セクションを詳しく書いてください。
"""
    else:
        char_instruction = """
この台本は5000文字以上で詳しく書いてください。
各セクションには具体例を3つ以上含めてください。
"""
    
    prompt = f"""YouTube動画の台本を生成してください。

{char_instruction}

【参考パターン】
{common_patterns[:5000]}

【テーマ】{theme}
【タイトル】{title}
{'【サムネイルワード】' + thumbnail_word if thumbnail_word else ''}

★ 出力ルール:
- 「ナレーション」「セリフ」などのラベル不要。直接話し言葉で開始
- 演出メモや（カッコ書きの指示）は出力しない
- 見出しはH2（##）とH3（###）のみ
- 区切り線（---）は不要
- 視聴者に語りかける口調で親しみやすく
- 各セクションは複数の段落で構成し、具体例やエピソードを豊富に入れる
- 短い文章はNG。各セクションをしっかりと詳しく書く

## フック
（視聴者の好奇心を刺激する冒頭。問題提起や意外な事実を複数の文で詳しく説明）

## CTA①
（チャンネル登録を自然に呼びかけ。なぜ登録すべきか理由も添えて）

## 導入
（今日の動画で得られるメリットを具体的に3つ以上説明）

## 本題1
（メインコンテンツ1。具体例を3つ以上挙げながら詳しく解説。視聴者の疑問を先回りして答える）

## 本題2
（メインコンテンツ2。具体例を3つ以上挙げながら詳しく解説。ステップバイステップで説明）

## CTA②
（途中のエンゲージメント。コメントやいいねを促す。質問を投げかける）

## 本題3
（メインコンテンツ3。具体例を3つ以上挙げながら詳しく解説。実践的なアドバイス）

## 注意点
（よくある失敗や間違いを3つ以上挙げて、それぞれの対処法も説明）

## まとめ
（今日のポイントを箇条書きではなく文章で振り返り。実践を促す）

## CTA③

## エンディング
（次の動画への期待を持たせる締めくくり）

★ 再確認: 必ず{target_chars if target_chars > 0 else 5000}文字以上で出力してください。短い台本はNGです。
"""
    
    try:
        response = model.generate_content(prompt)
        script_text = response.text
        char_count = len(script_text)
        return script_text, char_count
    except Exception as e:
        return f"エラー: {str(e)}", 0


def create_copy_button(text: str, button_id: str):
    escaped = text.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${').replace('\n', '\\n')
    components.html(f"""
        <button onclick="navigator.clipboard.writeText(`{escaped}`.replace(/\\\\n/g, '\\n')).then(() => {{
            document.getElementById('status-{button_id}').style.display = 'inline';
            setTimeout(() => document.getElementById('status-{button_id}').style.display = 'none', 2000);
        }})" style="
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: white; border: none; padding: 10px 20px; border-radius: 8px;
            cursor: pointer; font-size: 13px; font-weight: 600; margin: 8px 0;
        ">コピー</button>
        <span id="status-{button_id}" style="margin-left: 8px; color: #22c55e; display: none; font-size: 13px;">✓ コピー完了</span>
    """, height=50)


# メインUI
st.markdown('<h1 class="main-header">TubeHacker Pro</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">YouTube動画を分析し、黄金パターンを抽出するAIツール</p>', unsafe_allow_html=True)

# URLからAPIキーを読み込み
query_params = st.query_params
if 'api_key' in query_params and not st.session_state.api_key:
    st.session_state.api_key = query_params['api_key']

# APIキー未設定時のみ警告を表示（モーダルはボタンクリックで表示）
if not st.session_state.api_key:
    st.warning("⚠️ APIキーが未設定です。右上の『⚙️ 設定』ボタンから設定してください。")

# モデル初期化
model = None
if st.session_state.api_key:
    try:
        genai.configure(api_key=st.session_state.api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        st.error(f"API接続エラー: {e}")

# ヘッダーに設定ボタンを配置
col_header1, col_header2, col_header3 = st.columns([6, 2, 2])
with col_header2:
    if st.session_state.api_key:
        st.success("✓ API設定済み", icon="✅")
with col_header3:
    if st.button("⚙️ 設定", use_container_width=True):
        show_settings_dialog()


# タブ
tab1, tab2, tab3, tab4 = st.tabs(["分析", "共通項抽出", "企画生成", "台本生成"])

# タブ1
with tab1:
    st.header("動画分析")
    
    # 入力方法の選択
    input_method = st.radio("入力方法", ["動画URL", "チャンネルURL"], horizontal=True)
    
    video_ids_to_analyze = []
    
    if input_method == "動画URL":
        st.markdown("**YouTube動画のURLを入力（1行に1URL）**")
        urls_input = st.text_area(
            "URL", 
            placeholder="https://youtube.com/watch?v=xxxx\nhttps://youtube.com/watch?v=yyyy",
            height=100,
            label_visibility="collapsed",
            key="url_input"
        )
        
        # session_stateに保存
        st.session_state.current_urls = urls_input
        
        if urls_input.strip():
            # 改行、カンマで分割
            urls = re.split(r'[\n,]+', urls_input.strip())
            for url in urls[:MAX_VIDEOS]:
                url = url.strip()
                if url:
                    vid = extract_video_id(url)
                    if vid:
                        video_ids_to_analyze.append({'video_id': vid, 'url': url})
            if video_ids_to_analyze:
                st.success(f"✓ {len(video_ids_to_analyze)}件の動画を検出（最大{MAX_VIDEOS}件）")
    
    elif input_method == "チャンネルURL":
        st.markdown("**YouTubeチャンネルのURLを入力**")
        channel_url = st.text_input(
            "チャンネルURL", 
            placeholder="https://youtube.com/@channel",
            label_visibility="collapsed"
        )
        
        if channel_url.strip():
            # チャンネルURLが変わったら自動で動画を取得
            if channel_url != st.session_state.get('last_channel_url', ''):
                st.session_state.last_channel_url = channel_url
                with st.spinner("チャンネルから動画を取得中..."):
                    videos = get_videos_from_channel(channel_url)
                    st.session_state.fetched_videos = videos if videos else []
            
            if st.session_state.fetched_videos:
                st.success(f"✓ {len(st.session_state.fetched_videos)}件の動画を検出")
                for v in st.session_state.fetched_videos:
                    st.caption(f"・{v['title'][:50]}...")
                    video_ids_to_analyze.append({'video_id': v['video_id'], 'url': v['url']})
            elif channel_url:
                st.warning("動画が見つかりませんでした。URLを確認してください。")
    
    st.divider()
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        analyze_btn = st.button("🔍 分析開始", type="primary", use_container_width=True)
    with col2:
        stop_btn = st.button("⏹ 停止")
        if stop_btn:
            st.session_state.stop_generation = True
    with col3:
        if st.button("🗑 クリア"):
            st.session_state.analysis_results = []
            st.session_state.fetched_videos = []
            st.session_state.last_channel_url = ''
            st.rerun()
    
    # 分析実行
    if analyze_btn:
        if not video_ids_to_analyze:
            st.error("URLを入力してください")
        elif not model:
            st.error("APIキーを設定してください（右上の⚙️設定ボタン）")
        else:
            st.session_state.stop_generation = False
            progress = st.progress(0)
            status = st.empty()
            results = []
            
            for i, vdata in enumerate(video_ids_to_analyze):
                if st.session_state.stop_generation:
                    st.warning("停止しました")
                    break
                    
                try:
                    status.text(f"分析中 ({i+1}/{len(video_ids_to_analyze)}): 動画情報取得...")
                    # URLからショートかどうか判定
                    is_shorts = 'shorts' in vdata.get('url', '')
                    video_info = get_video_info(vdata['video_id'], is_shorts=is_shorts)
                    
                    status.text(f"分析中 ({i+1}/{len(video_ids_to_analyze)}): 字幕取得...")
                    transcript = get_transcript(vdata['video_id'])
                    
                    # ショート動画で字幕がない場合、音声から文字起こしを試みる
                    if is_shorts and not transcript and model:
                        status.text(f"分析中 ({i+1}/{len(video_ids_to_analyze)}): 音声から文字起こし中...")
                        transcript = transcribe_shorts_audio(model, vdata['video_id'])
                    
                    status.text(f"分析中 ({i+1}/{len(video_ids_to_analyze)}): AI分析中...")
                    result = analyze_video_with_gemini(model, video_info, transcript)
                    results.append(result)
                    
                except Exception as e:
                    st.error(f"動画 {vdata['video_id']} の分析でエラー: {str(e)}")
                    results.append({
                        'success': False, 
                        'error': str(e), 
                        'video_info': {'video_id': vdata['video_id'], 'title': 'エラー'}
                    })
                
                progress.progress((i + 1) / len(video_ids_to_analyze))
            
            st.session_state.analysis_results = results
            status.empty()
            success_count = len([r for r in results if r.get('success')])
            if success_count > 0:
                st.success(f"✓ 完了（{success_count}件成功）")
            else:
                st.error("分析に失敗しました。URLを確認してください。")
                # 失敗した原因を詳細表示
                for r in results:
                    if not r.get('success') and r.get('error'):
                        st.warning(f"エラー詳細: {r.get('error')}")


    
    if st.session_state.analysis_results:
        st.divider()
        
        # 目立つ見出し
        st.markdown("""
        <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 20px; border-radius: 16px; margin-bottom: 20px;">
            <h2 style="color: white; margin: 0; text-align: center;">🎬 分析結果</h2>
            <p style="color: rgba(255,255,255,0.9); text-align: center; margin: 10px 0 0 0;">以下の動画を分析しました。内容を確認してください。</p>
        </div>
        """, unsafe_allow_html=True)
        
        success_results = [r for r in st.session_state.analysis_results if r.get('success')]
        st.success(f"✓ {len(success_results)}件の動画を分析済み")
        
        for i, result in enumerate(success_results, 1):
            title = result['video_info'].get('title', '不明')
            chars = result.get('char_count', 0)
            
            # カード形式で表示（常に開いた状態）
            st.markdown(f"---")
            st.markdown(f"### {i}. {title}")
            st.caption(f"📝 {chars}文字")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                if result['video_info'].get('thumbnail_url'):
                    st.image(result['video_info']['thumbnail_url'], use_container_width=True)
                st.caption(f"[動画を見る]({result['video_info'].get('url', '#')})")
            with col2:
                create_copy_button(result['analysis'], f"analysis_{i}")
                
                # 分析結果の要約を表示（最初の500文字）
                analysis_text = result['analysis']
                if len(analysis_text) > 500:
                    st.markdown(analysis_text[:500] + "...")
                    with st.expander("📖 全文を表示"):
                        st.markdown(analysis_text)
                else:
                    st.markdown(analysis_text)
        
        st.markdown("---")
        
        # 次へのナビゲーション
        st.info("👆 上の『共通項抽出』タブをクリックして次のステップへ進んでください")

# タブ2
with tab2:
    st.header("共通項抽出")
    
    if not st.session_state.analysis_results:
        st.warning("先に動画を分析してください")
    else:
        results = [r for r in st.session_state.analysis_results if r.get('success')]
        st.info(f"{len(results)}件の分析結果からパターンを抽出")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            extract_btn = st.button("パターン抽出", type="primary")
        with col2:
            if st.button("停止", key="stop_extract"):
                st.session_state.stop_generation = True
        
        if extract_btn and model:
            with st.spinner("抽出中..."):
                patterns, char_stats = extract_common_patterns(model, results)
                st.session_state.common_patterns = patterns
                st.session_state.char_count_stats = char_stats
            st.success("✓ 完了")
            st.info(f"📊 台本の目標文字数: {char_stats.get('avg', 0)}文字（分析動画の平均）")
        
        if st.session_state.common_patterns:
            st.divider()
            st.markdown("### 📊 抽出された共通パターン")
            create_copy_button(st.session_state.common_patterns, "patterns")
            st.markdown(st.session_state.common_patterns)
            
            # 結果の下にナビゲーションボタン
            if st.button("👆 上の『企画生成』タブをクリックして次へ", type="primary", use_container_width=True, key="nav_to_ideas"):
                st.info("上の『企画生成』タブをクリックしてください")

# タブ3
with tab3:
    st.header("企画生成")
    
    # 生成モードの選択
    gen_mode = st.radio("生成モード", ["分析結果から生成", "直接テーマ入力"], horizontal=True)
    
    if gen_mode == "分析結果から生成":
        if not st.session_state.common_patterns:
            st.warning("先に動画を分析して共通項を抽出してください")
        else:
            theme = st.text_input("テーマ（任意）", placeholder="空欄の場合、分析動画に基づきAIが提案", key="theme_from_analysis")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                gen_ideas_btn = st.button("企画案を生成", type="primary", key="gen_from_analysis")
            with col2:
                if st.button("停止", key="stop_ideas"):
                    st.session_state.stop_generation = True
            
            if gen_ideas_btn and model:
                video_titles = [r['video_info']['title'] for r in st.session_state.analysis_results if r.get('success')]
                with st.spinner("生成中..."):
                    ideas = generate_content_ideas(model, st.session_state.common_patterns, theme, video_titles)
                    st.session_state.generated_ideas = ideas
                    st.session_state.parsed_ideas = parse_ideas(ideas)
                    st.session_state.current_theme = theme if theme else "AI提案テーマ"
                st.success("完了")
    
    else:  # 直接テーマ入力モード
        st.info("💡 分析なしで直接企画・台本を生成します")
        
        direct_theme = st.text_input("テーマ（必須）", placeholder="例: ChatGPTの活用法", key="direct_theme")
        direct_reference = st.text_area("参考情報（任意）", placeholder="YouTubeの傾向、ターゲット層、スタイルなど", height=80, key="direct_ref")
        
        # 目標文字数の入力
        direct_chars = st.number_input("目標文字数", min_value=1000, max_value=20000, value=5000, step=500, key="direct_chars")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            direct_gen_btn = st.button("🎯 企画案を直接生成", type="primary", key="gen_direct")
        with col2:
            if st.button("停止", key="stop_direct"):
                st.session_state.stop_generation = True
        
        if direct_gen_btn and model:
            if not direct_theme.strip():
                st.error("テーマを入力してください")
            else:
                # 直接生成用のパターンを作成
                direct_pattern = f"""
テーマ: {direct_theme}
参考情報: {direct_reference if direct_reference else 'なし'}
"""
                with st.spinner("生成中..."):
                    ideas = generate_content_ideas(model, direct_pattern, direct_theme, [])
                    st.session_state.generated_ideas = ideas
                    st.session_state.parsed_ideas = parse_ideas(ideas)
                    st.session_state.current_theme = direct_theme
                    st.session_state.char_count_stats = {'avg': direct_chars, 'max': direct_chars, 'min': direct_chars}
                st.success("完了")
    
    # 生成された企画の表示（両方のモードで共通）
    if st.session_state.generated_ideas:
        st.divider()
        st.markdown("### 💡 生成された企画案")
        create_copy_button(st.session_state.generated_ideas, "ideas")
        st.markdown(st.session_state.generated_ideas)
        
        st.divider()
        st.subheader("台本を作成")
        
        col1, col2 = st.columns(2)
        with col1:
            plan_num = st.radio("企画案", [1, 2, 3], format_func=lambda x: f"企画案{x}")
        with col2:
            title_num = st.radio("タイトル案", [1, 2, 3], format_func=lambda x: f"タイトル案{x}")
        
        # 自動でタイトルとサムネワードを取得
        parsed = st.session_state.parsed_ideas
        auto_title = ""
        auto_thumb = ""
        if plan_num in parsed:
            titles = parsed[plan_num].get('titles', [])
            if len(titles) >= title_num:
                auto_title = titles[title_num - 1]
            auto_thumb = parsed[plan_num].get('thumbnail_word', '')
        
        st.info(f"タイトル: {auto_title}")
        st.info(f"サムネワード: {auto_thumb}")
        
        custom_title = st.text_input("タイトル変更（任意）", placeholder="変更する場合のみ入力")
        custom_thumb = st.text_input("サムネワード変更（任意）", placeholder="変更する場合のみ入力")
        
        # 目標文字数を表示
        target_chars = st.session_state.char_count_stats.get('avg', 0)
        if target_chars > 0:
            st.markdown(f"""
            ---
            📊 **台本の目標文字数: {target_chars}文字前後**
            """)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            gen_script_btn = st.button("📝 台本を生成", type="primary", use_container_width=True)
        with col2:
            if st.button("停止", key="stop_script"):
                st.session_state.stop_generation = True
        
        if gen_script_btn and model:
            final_title = custom_title if custom_title else auto_title
            final_thumb = custom_thumb if custom_thumb else auto_thumb
            target_chars = st.session_state.char_count_stats.get('avg', 0)
            
            # common_patternsがなくても生成できるように
            patterns = st.session_state.common_patterns if st.session_state.common_patterns else f"テーマ: {st.session_state.current_theme}"
            
            with st.spinner("台本生成中..."):
                script, char_count = generate_full_script(
                    model,
                    patterns,
                    st.session_state.get('current_theme', ''),
                    final_title,
                    final_thumb,
                    target_chars
                )
                st.session_state.generated_script = script
                st.session_state.script_metadata = {
                    'title': final_title,
                    'thumbnail_word': final_thumb,
                    'char_count': char_count,
                    'target_chars': target_chars
                }
            
            st.success("台本が生成されました！上の『台本生成』タブをクリックして確認してください")


# タブ4
with tab4:
    st.header("台本生成結果")
    
    if not st.session_state.generated_script:
        st.warning("先に企画生成タブで台本を生成してください")
    else:
        meta = st.session_state.script_metadata
        
        # タイトルとサムネワードを本文の上に
        header_text = f"""タイトル: {meta.get('title', '')}
サムネイルワード: {meta.get('thumbnail_word', '')}
文字数: {meta.get('char_count', 0)}文字

"""
        full_text = header_text + st.session_state.generated_script
        
        st.markdown(f"**タイトル**: {meta.get('title', '')}")
        st.markdown(f"**サムネイルワード**: {meta.get('thumbnail_word', '')}")
        
        # 文字数と目標との比較
        char_count = meta.get('char_count', 0)
        target_chars = meta.get('target_chars', 0)
        
        if target_chars > 0:
            diff = char_count - target_chars
            diff_percent = (char_count / target_chars * 100) if target_chars > 0 else 0
            if abs(diff_percent - 100) <= 20:  # ±20%以内ならOK
                st.success(f"📊 **文字数**: {char_count}文字（目標{target_chars}文字の{diff_percent:.0f}%）✓")
            elif diff > 0:
                st.warning(f"📊 **文字数**: {char_count}文字（目標{target_chars}文字より{diff}文字多い）")
            else:
                st.warning(f"📊 **文字数**: {char_count}文字（目標{target_chars}文字より{-diff}文字少ない）")
        else:
            st.markdown(f"**文字数**: {char_count}文字")
        
        st.divider()
        
        create_copy_button(full_text, "script")
        
        # タイトルをH2見出しで表示
        st.markdown(f"## {meta.get('title', '')}")
        st.markdown(st.session_state.generated_script)

# フッター
st.divider()
st.caption(f"TubeHacker Pro v4.0 | 最大{MAX_VIDEOS}動画")
