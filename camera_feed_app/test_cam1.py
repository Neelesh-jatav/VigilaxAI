"""Test Camera 1 accessibility"""
import cv2

print('Testing Camera 1...')
cap = cv2.VideoCapture(1)
opened = cap.isOpened()
print(f'Camera 1 opened: {opened}')

if opened:
    ret, frame = cap.read()
    print(f'Can read frame: {ret}')
    if ret and frame is not None:
        print(f'Frame shape: {frame.shape}')
else:
    print('Camera 1 cannot be opened - might be in use or not available')

cap.release()
print('Test complete')
