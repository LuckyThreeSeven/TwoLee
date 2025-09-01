import cv2
import time

stream_url = "http://localhost:8080/video_feed"
cap = cv2.VideoCapture(stream_url)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
if not cap.isOpened():
    print("Stream not opened!")
    exit()

# 영상 저장 관련 변수
fps = 20.0                      # 프레임 속도 (보통 20~30)
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 또는 'XVID' → .avi

start_time = time.time()
segment_duration = 10  # 10초마다 저장
segment_index = 0

out = None

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame.")
        break

    current_time = time.time()

    # 첫 시작이거나, 10초 경과 시 새 파일 생성
    if out is None or (current_time - start_time) >= segment_duration:
        if out is not None:
            out.release()

        filename = f"video_segment_{segment_index}.mp4"
        print(f"[INFO] Start recording: {filename}")
        out = cv2.VideoWriter(filename, fourcc, fps, (frame_width, frame_height))
        start_time = current_time
        segment_index += 1

    out.write(frame)
    cv2.imshow("Server View", frame)

    if cv2.waitKey(1) == ord('q'):
        break

# 정리
if out:
    out.release()
cap.release()
cv2.destroyAllWindows()