import requests
from youtube_transcript_api import YouTubeTranscriptApi
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import schedule
import time
import re
from youtube_transcript_api import YouTubeTranscriptApi

# 환경 변수에서 API 키 가져오기
API_KEY = os.getenv('YOUTUBE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not API_KEY:
    raise ValueError("환경 변수 'YOUTUBE_API_KEY'가 설정되지 않았습니다.")
if not OPENAI_API_KEY:
    raise ValueError("환경 변수 'OPENAI_API_KEY'가 설정되지 않았습니다.")

CHANNEL_IDS = [
    'UCczff_dQVVb9sSEULFUJ-sw',  # 미투리
    'UCC3yfxS5qC6PCwDzetUuEWg',  # 소수몽키
    # # 'UC_JJ_NhRqPKcIOj5Ko3W_3w',  # 오선의 미국 증시 라이브
    'UCxvdCnvGODDyuvnELnLkQWw',  # 이효석 아카데미
    # # 'UCoCvTlU0KpNYwnMIgs7MPrA',  # 보다
    # 'UCXq7NNALDnqafn3KFvIyJKA' # 오늘의 테슬라 뉴스
    # 'UCMupe3fvv1-Hi3SRxZzSsTw'  #주식 채널 에디
    # 'UC_SrKcdnpqPxneW4vkddo8w'  #IVECOIN 채널
]

def get_latest_video_id(channel_id):
    """채널 ID를 통해 최신 동영상 ID 가져오기"""
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?key={API_KEY}&channelId={channel_id}&order=date&part=id&maxResults=1"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        if 'items' in data and len(data['items']) > 0:
            video_data = data['items'][0]['id']
            if 'videoId' in video_data:
                return video_data['videoId']
        print("최신 동영상을 찾을 수 없습니다.")
    except requests.exceptions.RequestException as e:
        print(f"YouTube API 요청 중 오류 발생: {e}")
    return None


# def get_youtube_transcript(video_id, timestamp, channel_name):
#     """동영상 ID를 통해 자막 가져오기 및 저장"""
#     if not video_id:
#         print("유효한 동영상 ID가 없습니다.")
#         return None

#     try:
#         transcript = None
#         for lang in ['ko', 'en']:
#             try:
#                 transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
#                 break
#             except Exception as e:
#                 print(f"{lang} 자막을 가져오는 중 오류 발생: {e}")
#                 continue

#         if not transcript:
#             print("사용할 수 있는 자막이 없습니다.")
#             return None

#         transcript_text = "\n".join([f"{entry['start']:.2f}s: {entry['text']}" for entry in transcript])
#         print(transcript_text)

#         save_path = get_save_path(f"transcript_{channel_name}.txt")
#         with open(save_path, 'w', encoding='utf-8') as f:
#             f.write(transcript_text)
#         print(f"자막이 '{save_path}' 파일에 저장되었습니다.")

#         return transcript_text
#     except Exception as e:
#         print(f"자막을 가져오는 중 오류 발생: {e}")
#         return None

def get_youtube_transcript(video_id, timestamp, channel_name):
    """동영상 ID를 통해 자막 가져오기 및 저장 (시간 정보 제거 포함)"""
    if not video_id:
        print("유효한 동영상 ID가 없습니다.")
        return None

    try:
        transcript = None
        for lang in ['ko', 'en']:
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                break
            except Exception as e:
                print(f"{lang} 자막을 가져오는 중 오류 발생: {e}")
                continue

        if not transcript:
            print("사용할 수 있는 자막이 없습니다.")
            return None

        # 자막을 문자열로 변환 (시간 정보 포함)
        transcript_with_time = "\n".join([f"{entry['start']:.2f}s: {entry['text']}" for entry in transcript])

        # 시간 정보 제거 (정규 표현식 활용)
        time_pattern = re.compile(r'^\d+\.\d+s:\s*', re.MULTILINE)
        transcript_text = time_pattern.sub('', transcript_with_time)

        print(transcript_text)  # 출력 (확인용)

        # 파일 저장
        save_path = get_save_path(f"transcript_{channel_name}.txt")
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(transcript_text)
        print(f"자막이 '{save_path}' 파일에 저장되었습니다.")

        return transcript_text
    except Exception as e:
        print(f"자막을 가져오는 중 오류 발생: {e}")
        return None

def get_save_path(filename):
    """파일 저장 경로 결정"""
    home_dir = os.path.expanduser("~")
    icloud_dir = os.path.join(home_dir, "Library/Mobile Documents/com~apple~CloudDocs")
    if os.path.exists(icloud_dir):
        return os.path.join(icloud_dir, filename)
    return os.path.join(home_dir, "Documents", filename)

def split_text_into_chunks(text, max_chars=6000):
    """텍스트를 일정한 크기로 나누는 함수"""
    chunks = []
    while len(text) > max_chars:
        split_index = text[:max_chars].rfind(" ")
        if split_index == -1:
            split_index = max_chars
        chunks.append(text[:split_index].strip())
        text = text[split_index:].strip()
    chunks.append(text)
    return chunks


def make_openai_request(payload, max_retries=3):
    """OpenAI API 요청을 재시도하는 함수"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"⚠️ OpenAI API 요청 실패 (재시도 {attempt+1}/{max_retries}): {e}")
            time.sleep(2 ** attempt)
    print("OpenAI API 요청이 지속적으로 실패했습니다.")
    return None


# def refine_summary(summary):
#     """1차 요약된 summary를 '종목명: 주가 변동 사항, 주가 변동 이유' 형식으로 변환"""
#     url = "https://api.openai.com/v1/chat/completions"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {OPENAI_API_KEY}"
#     }

#     payload = {
#         "model": "gpt-4o",
#         "messages": [
#             {"role": "system", "content": "주어진 내용을 다음과 같이 정리해줘. 당신은 주식 분석 전문가입니다. 전체 내용에서 동일한 기업 또는 주식에 대한 내용은 모두 모아서 한 곳에서 정리해줘. 주가에 대한 언급이 있거나 숫자가 나오는 경우는 빼먹지 말고 담아줘. 주가 예측치가 있어도 빼먹으면 안되. 예, 테슬라 주가는 180$이고 5% 상승했습니다. 그 이유는... 이런 식으로 정리를 하면 되.  처음에 안녕하세요 같은 인사로 시작하지 말것. 번호를 붙여서 정리하지 말것. 전체 내용의 구성은 시작은 기업들 주가 변동에 대한 정리를 먼저 하고, 그 다음에 주요 지수나 그밖에 것들을 간략하게 정리하면 되. 그 밖에 것들은 모두 5줄 이내로 정리해줘. 위 모든 지침은 꼭 지켜야해"},
#             {"role": "user", "content": summary}
#         ],
#         "temperature": 0
#     }

#     try:
#         response = requests.post(url, headers=headers, json=payload)
#         response.raise_for_status()
#         result = response.json()
#         return result["choices"][0]["message"]["content"]

#     except requests.exceptions.RequestException as e:
#         print(f"OpenAI API 요청 중 오류 발생: {e}")
#         return None

# def summarize_and_analyze(transcripts, timestamp):
#     """각 채널의 요약을 통합 분석 (6000자 이하로 나누어 요청)"""
#     combined_text = "\n\n".join(transcripts)
#     text_chunks = split_text_into_chunks(combined_text, max_chars=16300)
#     analysis_results = []

#     for chunk in text_chunks:
#         result = make_openai_request({
#             "model": "gpt-4o",
#             "messages": [
#                 {"role": "system", "content": "주어진 내용을 다음과 같이 한글로 정리해줘. 당신은 주식 분석 전문가입니다. 전체 내용에서 같은 종목 주식에 대한 내용은 모두 모아서 한 곳에서 정리해줘. 주가에 대한 언급이 있거나 숫자가 나오는 경우는 빼먹지 말고 담아줘. 주가 예측치가 있어도 빼먹으면 안되. 예, 테슬라 주가는 180$이고 5% 상승했습니다. 그 이유는... 이런 식으로 정리를 하면 되. 처음에 안녕하세요 같은 인사로 시작하지 말것. 번호를 붙여서 정리하지 말것. 전체 내용의 구성은 시작은 기업들 주가 변동에 대한 정리를 먼저 하고, 그 다음에 주요 지수나 그밖에 것들을 간략하게 정리하면 되. 그 밖에 것들은 모두 5줄 이내로 정리해줘. 위 모든 지침은 꼭 지켜야해"},
#                 {"role": "user", "content": chunk}
#             ],
#             "temperature": 0
#         })
#         if result:
#             analysis_results.append(result)
    
#     sum_analysis = "\n\n".join(analysis_results)
#     #save_path = get_save_path(f"final_summary_{timestamp}.txt")
#     save_path = get_save_path(f"sumup.txt")
#     with open(save_path, 'w', encoding='utf-8') as f:
#         f.write(sum_analysis)
#     print(f"분석 결과가 '{save_path}' 파일에 저장되었습니다.")
#     #final_summary= refine_summary(sum_analysis)
#     #save_path2 = get_save_path(f"summary.txt")
#     #with open(save_path2, 'w', encoding='utf-8') as f:
#     #    f.write(final_summary)
#     #print(f"최종 결과가 '{save_path2}' 파일에 저장되었습니다.")

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_transcripts = []

    for channel_id in CHANNEL_IDS:
        print(f"채널 {channel_id} 최신 동영상 검색 중...")
        latest_video_id = get_latest_video_id(channel_id)
        if latest_video_id:
            print(f"최신 동영상 ID: {latest_video_id}")
            transcript_text = get_youtube_transcript(latest_video_id, timestamp, channel_id)
            if transcript_text:
                all_transcripts.append(transcript_text)
    
    # if all_transcripts:
    #     print("전체 요약 및 분석 시작...")
    #     summarize_and_analyze(all_transcripts, timestamp)
    # else:
    #     print("유효한 자막 데이터가 없습니다.")

if __name__ == '__main__':
    #main()
    schedule.every().day.at("07:00").do(main)   
    
    while True:
        schedule.run_pending()
        time.sleep(60)

